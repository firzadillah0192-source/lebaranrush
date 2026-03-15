import json
import copy
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Room, GameState
from players.models import Player
from engine.transitions import transition_to
from engine.state_manager import get_current_state


class RoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Force room code to uppercase for case-insensitive matching/groups
        self.room_code = self.scope['url_route']['kwargs']['room_code'].upper()
        self.room_group_name = f'room_{self.room_code}'
        # Identity tracking for reward masking
        self.is_host = False
        self.player_id = None

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # Send current state upon connection
        state = await self.get_room_state_data()
        if state:
            await self.send(text_data=json.dumps({
                "action": "game_state_sync",
                "state": state['current_state'],
                "data": self.mask_rewards(state['state_data'], state['current_state']),
                "timer": state['timer'],
                "started_at": state.get('started_at'),
                "server_time": state['server_time'],
                "players": state['players']
            }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')

        # --- IDENTIFY HANDSHAKE ---
        if action == 'identify':
            self.is_host = data.get('is_host', False)
            self.player_id = data.get('player_id')
            return

        if action == 'player_join':
            player_id = data.get('player_id')
            player_name = data.get('player_name')
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'room_message',
                    'action': 'player_join',
                    'player_id': player_id,
                    'player_name': player_name,
                }
            )

        elif action == 'chat_message':
            # Use cached name if available
            pid = self.player_id
            pname = await self.get_player_name(pid) if pid else "Guest"
            message = data.get('message')
            if message:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'room_message',
                        'action': 'chat_message',
                        'player_id': str(pid) if pid else None,
                        'player_name': pname,
                        'message': message,
                    }
                )

        elif action == 'save_spin_config':
            spin_config = data.get('spin_config')
            await self.update_spin_config(spin_config)
            # Notify everyone about config update
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "room_message",
                    "action": "game_state_update",
                    "state": "SPINWHEEL_READY",
                    "data": {"spin_config": spin_config}
                }
            )

        elif action == 'state_transition_request':
            new_state = data.get('new_state')
            state_data = data.get('state_data', {})
            timer = data.get('timer')
            force = data.get('force', False)

            success, message = await database_sync_to_async(transition_to)(
                self.room_code, new_state, state_data, timer, force
            )

            if success:
                # The state_manager.update_game_state already broadcasts 'game_state_update'
                # with full data. We don't need a redundant broadcast here.
                pass

            if not success:
                await self.send(text_data=json.dumps({
                    "action": "error",
                    "message": message
                }))
            elif new_state == 'GACHA_PICK_SUBMIT':
                # After a successful pick, broadcast discrete events
                pick_event = await self.get_last_pick_event()
                if pick_event:
                    # 1. Broadcast BOX_PICKED to everyone (no reward info)
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            "type": "room_message",
                            "action": "box_picked",
                            "box_id": pick_event['box_id'],
                            "player_id": pick_event['player_id'],
                            "player_name": pick_event['player_name'],
                        }
                    )

                    # 2. Send personal reward event ONLY to the picker (this socket)
                    if pick_event.get('reward'):
                        event_type = pick_event.get('event_type', 'prize_won')
                        await self.send(text_data=json.dumps({
                            "action": event_type,
                            "box_id": pick_event['box_id'],
                            "reward": pick_event['reward'],
                            "player_id": pick_event['player_id'],
                            "player_name": pick_event['player_name'],
                        }))

                    # 3. Broadcast point update so all UIs refresh counts
                    player_id = state_data.get('player_id')
                    if player_id:
                        await self.broadcast_player_update(player_id)

                # 4. Auto-advance to GACHA_RESULT if all active players picked
                all_picked = await self.check_all_picked_flag()
                if all_picked:
                    import asyncio
                    await asyncio.sleep(1.5)
                    success, _ = await database_sync_to_async(transition_to)(
                        self.room_code, 'GACHA_RESULT', {}, None, True
                    )
                    # Use common auto-advance logic if successful
                    if success:
                        await self.auto_advance_from_result()

            elif new_state == 'GACHA_RESULT' and success:
                # If host manually transitions, trigger auto-advance from result
                await self.auto_advance_from_result()

            elif new_state == 'GACHA_POWERUP_RESOLVED' and success:
                # If host manually resolves or auto-resolves powerups
                await self.auto_resolve_and_advance()

        elif action == 'exchange_points_request':
            player_id = data.get('player_id')
            await self.exchange_points(player_id)

        elif action == 'gacha_interaction_submit':
            player_id = data.get('player_id')
            interaction_type = data.get('interaction_type')
            interaction_value = data.get('interaction_value')
            await self.handle_gacha_interaction(player_id, interaction_type, interaction_value)

        elif action == 'powerup_action':
            player_id = data.get('player_id')
            ability_type = data.get('ability_type')
            action_data = data.get('action_data', {})
            await self.handle_powerup_action(player_id, ability_type, action_data)

        elif action == 'start_game':
            game = data.get('game')
            if game == 'undercover':
                from games.undercover.game_logic import start_undercover_game
                target_round = data.get('round', 1)
                result = await database_sync_to_async(start_undercover_game)(self.room_code)
                if result.get('success'):
                    from engine.transitions import UNDERCOVER_REVEAL_TIMER
                    await database_sync_to_async(transition_to)(
                        self.room_code, 'UNDERCOVER_WORD', {
                            'assignments': result['assignments'],
                            'round': target_round
                        }, UNDERCOVER_REVEAL_TIMER, True
                    )
                    pass # state_manager already broadcasted with full data
                else:
                    await self.send(text_data=json.dumps({
                        "action": "error",
                        "message": result.get('error', 'Failed to start game.')
                    }))

        elif action == 'spin_wheel':
            # Player-triggered spin
            player_id = data.get('player_id')
            print(f"[WS] Action spin_wheel for player {player_id}")
            try:
                success, msg = await database_sync_to_async(transition_to)(
                    self.room_code, 'SPINWHEEL_SPIN', {'player_id': player_id}, None, True
                )
                print(f"[WS] Transition result: success={success}, msg={msg}")
                if success:
                    # Broadcast start event
                    gs = await self.get_room_state_data() # refresh to get reward index
                    reward = gs['state_data'].get('reward', {})
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'room_message',
                            'action': 'spin_start',
                            'player_name': reward.get('player_name', 'Player'),
                            'reward': reward # Includes chosen_index for animation
                        }
                    )
                    pass # state_manager already broadcasted with full data
                else:
                    print(f"[WS] Spin failed: {msg}")
                    await self.send(text_data=json.dumps({
                        "action": "toast",
                        "msg": f"Spin failed: {msg}",
                        "icon": "❌"
                    }))
            except Exception as e:
                print(f"[WS] Error in spin_wheel: {str(e)}")
                import traceback
                traceback.print_exc()

        elif action == 'force_resolve_powerups':
            await self.auto_resolve_and_advance()

        elif action == 'undercover_vote':
            voter_id = str(self.player_id)
            target_id = str(data.get('target_id'))
            await self.handle_undercover_vote(voter_id, target_id)

        elif action == 'undercover_submit_clue':
            player_id = str(self.player_id)
            clue = data.get('clue', '')
            await self.handle_undercover_clue(player_id, clue)

        elif action == 'admin_fetch_words':
            await self.handle_admin_fetch_words()

        elif action == 'admin_add_word':
            await self.handle_admin_add_word(data)

        elif action == 'admin_delete_word':
            await self.handle_admin_delete_word(data)

        elif action == 'sync_all':
            if self.is_host:
                state = await self.get_room_state_data()
                if state:
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            "type": "game_state_update",
                            "state": state['current_state'],
                            "data": state['state_data'],
                            "timer": state['timer'],
                            "started_at": state.get('started_at'),
                            "players": state['players']
                        }
                    )

        elif action == 'sync_request':
            state = await self.get_room_state_data()
            if state:
                await self.send(text_data=json.dumps({
                    "action": "game_state_sync",
                    "state": state['current_state'],
                    "data": self.mask_rewards(state['state_data'], state['current_state']),
                    "timer": state['timer'],
                    "server_time": state['server_time'],
                    "players": state['players']
                }))

    # --- REWARD MASKING ---
    def mask_rewards(self, state_data, current_state):
        """
        Strip sensitive info from state_data for non-host players.
        The picker always sees their own reward.
        """
        if not state_data:
            return state_data

        # Host always sees everything
        if self.is_host:
            return state_data

        masked = copy.deepcopy(state_data)

        # 1. Mask words for non-pickers in Gacha
        if current_state in ('GACHA_PICK', 'GACHA_SHUFFLE', 'GACHA_INTERACT', 'GACHA_POWERUP') and 'boxes' in masked:
            for box in masked.get('boxes', []):
                if str(box.get('player_id', '')) == str(self.player_id):
                    continue
                else:
                    box['reward'] = None
            masked.pop('_last_pick_event', None)
            masked.pop('_all_picked', None)
            masked.pop('_has_powerups', None)

        # 2. Mask words for Undercover
        if current_state == 'UNDERCOVER_WORD' and 'assignments' in masked:
            assignments = masked.get('assignments', {})
            # Only keep the player's own assignment
            if self.player_id:
                player_id_str = str(self.player_id)
                my_assignment = assignments.get(player_id_str)
                masked['assignments'] = {player_id_str: my_assignment} if my_assignment else {}
            else:
                masked['assignments'] = {}
        
        # 3. Mask voting progress if needed (optional, currently public)

        return masked

    # --- GROUP HANDLERS ---
    async def room_message(self, event):
        await self.send(text_data=json.dumps(event))

    async def game_state_update(self, event):
        """Handler for state updates from engine broadcast."""
        # Prioritize data from the event for speed and consistency
        state = event.get('state')
        data = event.get('data')
        timer = event.get('timer')
        started_at = event.get('started_at', 0)
        
        # Fallback to DB only if event is incomplete
        if state is None or data is None:
            state_obj = await self.get_room_state_data()
            if not state_obj: return
            state = state_obj['current_state']
            data = state_obj['state_data']
            timer = state_obj['timer']
            started_at = state_obj.get('started_at', 0)

        # Always fetch fresh players list for status sync
        players_data = await self.get_players_list()
        
        await self.send(text_data=json.dumps({
            "action": "game_state_update",
            "state": state,
            "data": self.mask_rewards(data, state),
            "timer": timer,
            "started_at": started_at,
            "players": players_data
        }))

        # Auto-advance logic (Only host handles this to avoid race conditions)
        if self.is_host:
            import asyncio
            if state == 'GACHA_RESULT':
                asyncio.create_task(self.auto_advance_from_result())
            elif state == 'GACHA_POWERUP':
                asyncio.create_task(self.auto_advance_from_powerup())
            elif state == 'SPINWHEEL_SPIN':
                asyncio.create_task(self.auto_advance_spin(4.0))
            elif state == 'SPINWHEEL_RESULT':
                asyncio.create_task(self.auto_reset_spin_ready(6.0))
            elif state.startswith('UNDERCOVER_') and timer > 0:
                current_turn = data.get('current_turn_index') if state == 'UNDERCOVER_DISCUSSION' else None
                asyncio.create_task(self.auto_advance_undercover(state, timer, current_turn))

    # --- HELPERS ---
    async def broadcast_player_update(self, player_id):
        try:
            player = await database_sync_to_async(lambda: Player.objects.get(id=player_id))()
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "room_message",
                    "action": "point_update",
                    "player_id": str(player.id),
                    "points": player.points,
                    "spin_count": player.spin_count,
                    "shield_count": player.shield_count,
                    "swap_count": player.swap_count
                }
            )
        except Exception:
            pass

    @database_sync_to_async
    def check_all_picked_flag(self):
        """Check the _all_picked flag set by the transition engine."""
        try:
            room = Room.objects.get(code=self.room_code)
            state = room.game_state
            return (state.state_data or {}).get('_all_picked', False)
        except Exception:
            return False

    @database_sync_to_async
    def check_has_powerups_flag(self):
        """Check if GACHA_RESULT has powerup abilities."""
        try:
            room = Room.objects.get(code=self.room_code)
            state = room.game_state
            return (state.state_data or {}).get('_has_powerups', False)
        except Exception:
            return False

    @database_sync_to_async
    def check_has_next_round_flag(self):
        """Check if there is a next round configured."""
        try:
            room = Room.objects.get(code=self.room_code)
            state = room.game_state
            gs_data = state.state_data or {}
            round_configs = gs_data.get('round_configs', [])
            current_round = gs_data.get('current_round', 1)
            return current_round < len(round_configs)
        except Exception:
            return False

    @database_sync_to_async
    def get_active_player_count(self):
        """Count non-eliminated players in the room."""
        try:
            return Player.objects.filter(room__code=self.room_code, status='active').count()
        except Exception:
            return 0

    @database_sync_to_async
    def get_last_pick_event(self):
        """Read the last pick event stored by the transition engine."""
        try:
            room = Room.objects.get(code=self.room_code)
            state = room.game_state
            event = (state.state_data or {}).get('_last_pick_event')
            return event
        except Exception:
            return None

    @database_sync_to_async
    def get_room_state_data(self):
        try:
            from django.utils import timezone
            room = Room.objects.get(code=self.room_code)
            state, _ = GameState.objects.get_or_create(room=room)

            players_data = []
            for p in room.players.all():
                players_data.append({
                    "id": str(p.id),
                    "name": p.name,
                    "status": p.status,
                    "points": p.points,
                    "spin_count": p.spin_count,
                    "shield_count": p.shield_count,
                    "swap_count": p.swap_count
                })

            sync_data = {
                "current_state": state.current_state,
                "state_data": state.state_data or {},
                "timer": state.timer_duration or 0,
                "started_at": state.state_started_at.isoformat(),
                "server_time": int(timezone.now().timestamp() * 1000),
                "players": players_data
            }
            return sync_data
        except Exception:
            return None

    async def exchange_points(self, player_id):
        try:
            player = await database_sync_to_async(lambda: Player.objects.get(id=player_id))()
            room = await database_sync_to_async(lambda: Room.objects.get(code=self.room_code))()
            if player.points >= room.spin_cost_points:
                player.points -= room.spin_cost_points
                player.spin_count += 1
                await database_sync_to_async(player.save)()

                # Add to queue if spin session is active
                @database_sync_to_async
                def add_to_queue():
                    try:
                        state = room.game_state
                        gs_data = state.state_data or {}
                        spin_config = gs_data.get('spin_config', {})
                        if spin_config.get('is_active'):
                            queue = gs_data.get('spin_queue', [])
                            if not any(qp['id'] == str(player.id) for qp in queue):
                                queue.append({'id': str(player.id), 'name': player.name})
                                gs_data['spin_queue'] = queue
                                state.state_data = gs_data
                                state.save()
                                return True
                        return False
                    except Exception: return False
                
                queued = await add_to_queue()

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "room_message",
                        "action": "point_update",
                        "player_id": player_id,
                        "points": player.points,
                        "spin_count": player.spin_count,
                        "shield_count": player.shield_count,
                        "swap_count": player.swap_count
                    }
                )

                if queued:
                    # Sync game state to show updated queue
                    await self.game_state_update({
                        'type': 'game_state_update',
                        'data': {'room_code': self.room_code}
                    })

        except Exception as e:
            print(f"Error exchanging points: {e}")

    async def handle_gacha_interaction(self, player_id, interaction_type, interaction_value):
        try:
            room = await database_sync_to_async(lambda: Room.objects.get(code=self.room_code))()
            state = await database_sync_to_async(lambda: room.game_state)()
            player = await database_sync_to_async(lambda: Player.objects.get(id=player_id))()

            if not state.state_data:
                state.state_data = {}
            if 'interactions' not in state.state_data:
                state.state_data['interactions'] = {}

            state.state_data['interactions'][str(player_id)] = {
                'type': interaction_type,
                'value': interaction_value
            }

            # Handle shield interaction: apply immediately
            if interaction_type == 'use_shield':
                boxes = state.state_data.get('boxes', [])
                box = next((b for b in boxes if str(b.get('player_id')) == str(player_id) and b.get('pending_interaction') == 'shield'), None)
                if box:
                    if interaction_value:  # Player chose to USE shield
                        player.shield_count = max(0, player.shield_count - 1)
                        box['reward'] = {'type': 'special', 'item': 'shield', 'label': 'Shield Used - Safe!'}
                        box['revealed'] = True
                    else:  # Player chose NOT to use shield (accept zonk)
                        player.status = 'eliminated'
                        box['revealed'] = True
                    box.pop('pending_interaction', None)
                    await database_sync_to_async(player.save)()
                    state.state_data['boxes'] = boxes

            # Execute IMMEDIATE if manual swap
            elif interaction_type == 'swap_points':
                if player.swap_count > 0:
                    target_id = interaction_value
                    try:
                        rival = await database_sync_to_async(lambda: Player.objects.get(id=target_id))()
                        player.points, rival.points = rival.points, player.points
                        player.swap_count -= 1
                        await database_sync_to_async(player.save)()
                        await database_sync_to_async(rival.save)()

                        await self.channel_layer.group_send(
                            self.room_group_name,
                            {
                                "type": "room_message",
                                "action": "toast_broadcast",
                                "msg": f"{player.name} swapped points with {rival.name}!",
                                "icon": "🔄"
                            }
                        )
                    except Player.DoesNotExist:
                        pass
                # Mark box as revealed
                boxes = state.state_data.get('boxes', [])
                box = next((b for b in boxes if str(b.get('player_id')) == str(player_id) and b.get('pending_interaction') == 'swap'), None)
                if box:
                    box['revealed'] = True
                    box.pop('pending_interaction', None)
                    state.state_data['boxes'] = boxes

            await database_sync_to_async(state.save)()

            # Broadcast point update
            await self.broadcast_player_update(player_id)
            if interaction_type == 'swap_points' and 'rival' in locals():
                await self.broadcast_player_update(rival.id)

            # Auto-advance: if in GACHA_INTERACT, try to go to GACHA_RESULT now
            if state.current_state == 'GACHA_INTERACT':
                import asyncio
                await asyncio.sleep(1.0)
                await database_sync_to_async(transition_to)(
                    self.room_code, 'GACHA_RESULT', {}, None, True
                )

        except Exception as e:
            import traceback
            traceback.print_exc()

    async def handle_undercover_vote(self, voter_id, target_id):
        try:
            room = await database_sync_to_async(lambda: Room.objects.get(code=self.room_code))()
            state = await database_sync_to_async(lambda: room.game_state)()

            if state.current_state != 'UNDERCOVER_VOTE':
                return

            if not state.state_data:
                state.state_data = {}
            if 'votes' not in state.state_data:
                state.state_data['votes'] = {}

            state.state_data['votes'][str(voter_id)] = str(target_id)
            await database_sync_to_async(state.save)()

            # Sync players to show status
            players_data = await self.get_players_list()
            
            # Broadcast update to host (who shows vote counts/status)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "room_message",
                    "action": "vote_update",
                    "voter_id": voter_id,
                    "target_id": target_id,
                    "votes": state.state_data['votes'],
                    "players": players_data
                }
            )

            # Auto-advance if all active players voted
            @database_sync_to_async
            def check_all_voted():
                active_players = room.players.filter(status='active').exclude(id=voter_id) # Voter is active too
                # wait, voter_id IS one of the active players.
                active_count = room.players.filter(status='active').count()
                voted_count = len(state.state_data['votes'])
                return voted_count >= active_count

            if await check_all_voted():
                import asyncio
                await asyncio.sleep(1.0)
                await database_sync_to_async(transition_to)(
                    self.room_code, 'UNDERCOVER_RESULT', {}, None, True
                )
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "game_state_update"
                    }
                )

        except Exception as e:
            print(f"Error in handle_undercover_vote: {e}")

    async def handle_undercover_clue(self, player_id, clue_text):
        try:
            room = await database_sync_to_async(lambda: Room.objects.get(code=self.room_code))()
            state = await database_sync_to_async(lambda: room.game_state)()

            if state.current_state != 'UNDERCOVER_DISCUSSION':
                return

            gs_data = state.state_data or {}
            turn_order = gs_data.get('turn_order', [])
            current_idx = gs_data.get('current_turn_index', 0)

            if current_idx >= len(turn_order):
                return

            # Verify it's this player's turn
            if str(turn_order[current_idx]) != str(player_id):
                return

            # Append clue
            clues = gs_data.get('clues', [])
            player_name = await self.get_player_name(player_id)
            clues.append({
                'player_id': str(player_id),
                'player_name': player_name,
                'clue': clue_text[:50] # Limit to 50 chars as requested
            })
            gs_data['clues'] = clues

            # Save state
            state.state_data = gs_data
            await database_sync_to_async(state.save)()

            # Advance turn (using transition_to so it handles logic consistently)
            from engine.transitions import UNDERCOVER_DISCUSSION_TIMER
            await database_sync_to_async(transition_to)(
                self.room_code, 'UNDERCOVER_DISCUSSION', {}, UNDERCOVER_DISCUSSION_TIMER, True
            )

            # Broadcast update
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "game_state_update"
                }
            )

        except Exception as e:
            print(f"Error handling clue: {e}")
            import traceback
            traceback.print_exc()

    async def handle_admin_fetch_words(self):
        try:
            from games.undercover.models import UndercoverWord
            words = await database_sync_to_async(lambda: list(UndercoverWord.objects.filter(is_active=True).values('id', 'word_common', 'word_undercover')))()
            await self.send(text_data=json.dumps({
                'action': 'admin_words_list',
                'words': words
            }))
        except Exception as e:
            print(f"Error in handle_admin_fetch_words: {e}")

    async def handle_admin_add_word(self, data):
        try:
            from games.undercover.models import UndercoverWord
            common = data.get('common')
            undercover = data.get('undercover')
            if common and undercover:
                await database_sync_to_async(lambda: UndercoverWord.objects.create(word_common=common, word_undercover=undercover))()
                await self.handle_admin_fetch_words()
        except Exception as e:
            print(f"Error in handle_admin_add_word: {e}")

    async def handle_admin_delete_word(self, data):
        try:
            from games.undercover.models import UndercoverWord
            word_id = data.get('id')
            if word_id:
                await database_sync_to_async(lambda: UndercoverWord.objects.filter(id=word_id).delete())()
                await self.handle_admin_fetch_words()
        except Exception as e:
            print(f"Error in handle_admin_delete_word: {e}")

    @database_sync_to_async
    def get_player_name(self, player_id):
        try:
            p = Player.objects.get(id=player_id)
            return p.name
        except Exception:
            return "Unknown"

    @database_sync_to_async
    def get_players_list(self):
        """Get current players list for state broadcasts."""
        try:
            room = Room.objects.get(code=self.room_code)
            return [{
                'id': str(p.id),
                'name': p.name,
                'status': p.status,
                'points': p.points,
                'spin_count': p.spin_count,
                'shield_count': p.shield_count,
                'swap_count': p.swap_count
            } for p in room.players.all()]
        except Exception:
            return []

    async def handle_powerup_action(self, player_id, ability_type, action_data):
        """Handle a player's power-up ability action during GACHA_POWERUP."""
        try:
            room = await database_sync_to_async(lambda: Room.objects.get(code=self.room_code))()
            state = await database_sync_to_async(lambda: room.game_state)()

            if state.current_state != 'GACHA_POWERUP':
                await self.send(text_data=json.dumps({
                    "action": "error",
                    "message": "Not in power-up phase"
                }))
                return

            if not state.state_data:
                state.state_data = {}
            if 'powerup_actions' not in state.state_data:
                state.state_data['powerup_actions'] = {}

            # Store the action
            state.state_data['powerup_actions'][str(player_id)] = action_data

            # Update ability status in the abilities list
            abilities = state.state_data.get('powerup_abilities', [])
            for ab in abilities:
                if ab['player_id'] == str(player_id):
                    ab['status'] = 'submitted'
                    break

            state.state_data['powerup_abilities'] = abilities
            await database_sync_to_async(state.save)()

            # Broadcast updated powerup state
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "room_message",
                    "action": "powerup_update",
                    "player_id": str(player_id),
                    "ability_type": ability_type,
                    "status": "submitted",
                    "abilities": abilities,
                }
            )

            # Check if all players with active abilities (steal, swap) have acted
            pending = [a for a in abilities if a['status'] in ('pending', 'unused') and a['ability'] in ('steal', 'swap')]
            if not pending:
                import asyncio
                await asyncio.sleep(1.0)
                await self.auto_resolve_and_advance()

        except Exception:
            import traceback
            traceback.print_exc()

    async def auto_advance_from_result(self, delay=3.0):
        """Logic to decide if we go to Power-Up, Next Round, or Finish after GACHA_RESULT."""
        import asyncio
        await asyncio.sleep(delay)  # Wait for results to be visible
        
        # --- STATE GUARD ---
        # Ensure we are still in the state we expect before advancing
        # This prevents race conditions where multiple picks trigger multiple advances
        state_obj = await self.get_room_state_data()
        if not state_obj or state_obj['current_state'] != 'GACHA_RESULT':
            return

        has_powerups = await self.check_has_powerups_flag()
        if has_powerups:
            await database_sync_to_async(transition_to)(
                self.room_code, 'GACHA_POWERUP', {}, None, True
            )
        else:
            # Add a bit more delay for players to read results if no powerups
            await asyncio.sleep(3.0) 
            
            # Re-check state AGAIN after second sleep
            state_obj = await self.get_room_state_data()
            if not state_obj or state_obj['current_state'] != 'GACHA_RESULT':
                return

            active_count = await self.get_active_player_count()
            has_next = await self.check_has_next_round_flag()
            
            if active_count == 0:
                await database_sync_to_async(transition_to)(
                    self.room_code, 'GAME_FINISHED', {}, None, True
                )
            else:
                await self.auto_resolve_and_advance()

    async def auto_advance_from_powerup(self):
        """Automatically resolve power-ups when time expires."""
        import asyncio
        state_obj = await self.get_room_state_data()
        if not state_obj or state_obj['current_state'] != 'GACHA_POWERUP':
            return
            
        timer = state_obj.get('timer', 10)
        # Wait for timer + buffer
        await asyncio.sleep(timer + 1)
        
        # Re-check state: if still in POWERUP, force resolution
        state_obj = await self.get_room_state_data()
        if state_obj and state_obj['current_state'] == 'GACHA_POWERUP':
            await self.auto_resolve_and_advance()

    async def auto_resolve_and_advance(self):
        """Handle logic for advancing after powerups are resolved."""
        from engine.transitions import resolve_powerup_abilities
        import asyncio

        @database_sync_to_async
        def do_resolve():
            from engine.state_manager import update_game_state
            room = Room.objects.get(code=self.room_code)
            state = room.game_state
            gs_data = state.state_data or {}
            
            # Resolve the abilities (modifies round_rewards and commits to Player models)
            gs_data = resolve_powerup_abilities(self.room_code, gs_data)
            
            # Use the state manager to broadcast the updated state to all clients
            update_game_state(self.room_code, state.current_state, gs_data)
            return gs_data

        gs_data = await do_resolve()

        # Broadcast resolved abilities
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "room_message",
                "action": "powerup_resolved",
                "abilities": gs_data.get('powerup_abilities', []),
            }
        )

        # Wait for resolution display
        await asyncio.sleep(2.0)

        # Advance to next round or finish
        round_configs = gs_data.get('round_configs', [])
        current_round = gs_data.get('current_round', 1)
        active_count = await self.get_active_player_count()

        if active_count == 0:
            await database_sync_to_async(transition_to)(
                self.room_code, 'GAME_FINISHED', {}, None, True
            )
        elif current_round < len(round_configs):
            next_round = current_round + 1
            await database_sync_to_async(transition_to)(
                self.room_code, 'GACHA_REVEAL', {
                    'round': next_round,
                    'round_configs': round_configs,
                }, None, True
            )
        else:
            await database_sync_to_async(transition_to)(
                self.room_code, 'GAME_FINISHED', {}, None, True
            )

    async def advance_to_next_round(self):
        """Helper to advance to the next round from GACHA_RESULT."""
        @database_sync_to_async
        def get_next_round_data():
            try:
                room = Room.objects.get(code=self.room_code)
                state = room.game_state
                # Only advance if we are actually still in a state that allows it
                if state.current_state not in ('GACHA_RESULT', 'GACHA_POWERUP'):
                    return None
                    
                gs_data = state.state_data or {}
                return {
                    'current_round': gs_data.get('current_round', 1),
                    'next_round': gs_data.get('current_round', 1) + 1,
                    'round_configs': gs_data.get('round_configs', []),
                    'active_count': Player.objects.filter(room__code=self.room_code, status='active').count()
                }
            except Exception:
                return None

        data = await get_next_round_data()
        if not data: return
        
        if data['active_count'] == 0:
            await database_sync_to_async(transition_to)(
                self.room_code, 'GAME_FINISHED', {}, None, True
            )
        elif data['next_round'] <= len(data['round_configs']):
            # Double check current state data is the same round we think it is
            await database_sync_to_async(transition_to)(
                self.room_code, 'GACHA_REVEAL', {
                    'round': data['next_round'],
                    'round_configs': data['round_configs'],
                }, None, True
            )
        else:
            await database_sync_to_async(transition_to)(
                self.room_code, 'GAME_FINISHED', {}, None, True
            )

    @database_sync_to_async
    def update_spin_config(self, spin_config):
        try:
            room = Room.objects.get(code=self.room_code)
            
            # Update spin cost on room
            if 'spin_cost_points' in spin_config:
                room.spin_cost_points = spin_config['spin_cost_points']
                room.save()
                
            state = room.game_state
            gs_data = state.state_data or {}
            gs_data['spin_config'] = spin_config
            
            # If session is activating, initialize queue
            if spin_config.get('is_active') and not gs_data.get('spin_queue'):
                players = room.players.all().order_by('id')
                queue = []
                for p in players:
                    if p.spin_count > 0:
                        queue.append({'id': str(p.id), 'name': p.name})
                gs_data['spin_queue'] = queue
            
            state.state_data = gs_data
            state.save()
        except Exception:
            pass

    async def auto_advance_spin(self, delay=5.0):
        import asyncio
        await asyncio.sleep(delay)
        
        # Get result before transition to send result event
        gs = await self.get_room_state_data()
        reward = gs['state_data'].get('reward', {})
        
        success, _ = await database_sync_to_async(transition_to)(
            self.room_code, 'SPINWHEEL_RESULT', {}, None, True
        )
        
        if success:
            # Broadcast result event
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'room_message',
                    'action': 'spin_result',
                    'player_name': reward.get('player_name', 'Player'),
                    'reward': reward
                }
            )
            
            pass # state_manager already broadcasted with full data

    async def auto_reset_spin_ready(self, delay=6.0):
        import asyncio
        await asyncio.sleep(delay)
        
        # Check if tournament ended
        @database_sync_to_async
        def check_status():
            try:
                room = Room.objects.get(code=self.room_code)
                state = room.game_state
                gs_data = state.state_data or {}
                return gs_data.get('_tournament_ended', False), len(gs_data.get('spin_queue', [])) > 0
            except Exception:
                return False, False
                
        is_ended, has_queue = await check_status()
        
        if is_ended:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "room_message",
                    "action": "spin_tournament_end"
                }
            )
            # Automatic transition back to LOBBY
            success, _ = await database_sync_to_async(transition_to)(
                self.room_code, 'LOBBY', {'reset': True}, None, True
            )
        else:
            # We ALWAYS go back to READY to wait for the next player to click SPIN
            # Even if there is a queue.
            success, _ = await database_sync_to_async(transition_to)(
                self.room_code, 'SPINWHEEL_READY', {}, None, True
            )
            
        if success:
            pass # state_manager already broadcasted with full data
    async def check_and_trigger_spin(self):
        """Automatically start the spin if there is someone in the queue and we are READY."""
        @database_sync_to_async
        def get_queue_status():
            try:
                room = Room.objects.get(code=self.room_code)
                state = room.game_state
                if state.current_state != 'SPINWHEEL_READY':
                    return False
                gs_data = state.state_data or {}
                if gs_data.get('spin_config', {}).get('is_active') and gs_data.get('spin_queue'):
                    return True
                return False
            except Exception:
                return False
                
        if await get_queue_status():
            await database_sync_to_async(transition_to)(
                self.room_code, 'SPINWHEEL_SPIN', {}, None, True
            )
    async def get_player_name(self, player_id):
        @database_sync_to_async
        def _get():
            try:
                from players.models import Player
                return Player.objects.get(id=player_id).name
            except Exception:
                return "Unknown"
        return await _get()

    async def auto_advance_undercover(self, state, timer, turn_index=None):
        """Automatically advance Undercover phases when timer expires."""
        import asyncio
        if timer <= 0: return
        
        # Wait for the timer duration
        await asyncio.sleep(timer)
        
        # Verify if we are still in the same state before advancing
        state_obj = await self.get_room_state_data()
        if not state_obj or state_obj['current_state'] != state:
            return
            
        # For DISCUSSION, check if we are still on the same turn
        if state == 'UNDERCOVER_DISCUSSION' and turn_index is not None:
            current_gs_data = state_obj.get('state_data', {})
            if current_gs_data.get('current_turn_index') != turn_index:
                return

        if state == 'UNDERCOVER_WORD':
            await database_sync_to_async(transition_to)(
                self.room_code, 'UNDERCOVER_DISCUSSION', {}, None, True
            )
        elif state == 'UNDERCOVER_DISCUSSION':
            # Advance to next turn (transition_to handles the logic)
            await database_sync_to_async(transition_to)(
                self.room_code, 'UNDERCOVER_DISCUSSION', {}, None, True
            )
        elif state == 'UNDERCOVER_VOTE':
            await database_sync_to_async(transition_to)(
                self.room_code, 'UNDERCOVER_RESULT', {}, None, True
            )
            
        # No need for manual broadcast here, transition_to -> update_game_state already did it
        pass
