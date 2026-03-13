from django.utils import timezone
from . import state_manager
from .state_manager import get_current_state

VALID_TRANSITIONS = {
    'LOBBY': ['GACHA_CONFIG', 'UNDERCOVER_WORD', 'SPINWHEEL_READY', 'GAME_FINISHED'],
    
    # Gacha flow (with Power-Up phase)
    'GACHA_CONFIG': ['GACHA_REVEAL'],
    'GACHA_REVEAL': ['GACHA_SHUFFLE'],
    'GACHA_SHUFFLE': ['GACHA_PICK'],
    'GACHA_PICK': ['GACHA_RESULT'],
    'GACHA_RESULT': ['GACHA_POWERUP', 'LOBBY', 'SPINWHEEL_READY', 'GACHA_CONFIG'],
    'GACHA_POWERUP': ['GACHA_CONFIG', 'LOBBY'],
    
    # Undercover flow
    'UNDERCOVER_WORD': ['UNDERCOVER_DISCUSSION'],
    'UNDERCOVER_DISCUSSION': ['UNDERCOVER_VOTE'],
    'UNDERCOVER_VOTE': ['UNDERCOVER_RESULT'],
    'UNDERCOVER_RESULT': ['LOBBY', 'SPINWHEEL_READY'],
    
    # Spin Wheel flow
    'SPINWHEEL_READY': ['SPINWHEEL_SPIN'],
    'SPINWHEEL_SPIN': ['SPINWHEEL_RESULT'],
    'SPINWHEEL_RESULT': ['LOBBY', 'GACHA_CONFIG', 'UNDERCOVER_WORD', 'SPINWHEEL_READY'],
    
    # End state
    'GAME_FINISHED': []
}

def transition_to(room_code, new_state, state_data=None, timer=None, force=False):
    """
    Safely transition to a new game state.
    """
    current_gs = get_current_state(room_code)
    
    if not current_gs:
        return False, "Room not found"
        
    if not force:
        allowed = VALID_TRANSITIONS.get(current_gs.current_state, [])
        if new_state not in allowed:
            if new_state != 'GACHA_PICK_SUBMIT':
                return False, f"Invalid transition from {current_gs.current_state} to {new_state}"

    # Handle specialized logic per state
    if new_state == 'SPINWHEEL_READY':
        room_code = current_gs.room.code
        gs_data = current_gs.state_data or {}
        spin_config = gs_data.get('spin_config', {})
        
        # If we came from RESULT, pop the finished player
        if current_gs.current_state == 'SPINWHEEL_RESULT':
            queue = gs_data.get('spin_queue', [])
            if queue:
                queue.pop(0)
                gs_data['spin_queue'] = queue
            
            # After popping, check if we should end
            cost = spin_config.get('spin_cost_points', 10)
            if not queue:
                from players.models import Player
                players = Player.objects.filter(room__code=room_code)
                can_spin = any(p.spin_count > 0 or p.points >= cost for p in players)
                if not can_spin:
                    # Transition to LOBBY
                    gs_data['_tournament_ended'] = True
                    state_manager.update_game_state(room_code, 'LOBBY', {'reset': True}, None)
                    return True, "Tournament ended"

        # Initialize queue if active and no queue exists
        if spin_config.get('is_active') and not gs_data.get('spin_queue'):
            from players.models import Player
            players = list(Player.objects.filter(room__code=room_code).order_by('id'))
            
            # Round-robin allocation of tickets to queue
            queue = []
            if players:
                max_tickets = max(p.spin_count for p in players)
                for i in range(max_tickets):
                    for p in players:
                        if p.spin_count > i:
                            queue.append({'id': str(p.id), 'name': p.name})
            
            gs_data['spin_queue'] = queue
            
        if not gs_data.get('spin_history'):
            gs_data['spin_history'] = []
            
        # Clear current results
        gs_data['reward'] = None
        gs_data['current_spinner_id'] = None
            
        state_data = gs_data
        timer = None

    elif new_state == 'SPINWHEEL_SPIN':
        import random
        from players.models import Player
        print(f"[TRANSITION] SPINWHEEL_SPIN requested for room {room_code}")
        
        gs_data = current_gs.state_data or {}
        spin_config = gs_data.get('spin_config', {})
        queue = gs_data.get('spin_queue', [])
        
        if not spin_config.get('is_active') and not force:
            return False, "Spin session not active"

        if not queue and not force:
            return False, "No players in queue"

        # Peek next player from queue (don't pop yet, per user instruction: remove after finish)
        current_spinner = None
        if queue:
            current_spinner = queue[0]
            player_id = current_spinner['id']
        else:
            player_id = state_data.get('player_id')
            
        if player_id:
            try:
                player = Player.objects.get(id=player_id)
                print(f"[TRANSITION] Found player {player.name} (Spins: {player.spin_count})")
                
                if player.spin_count > 0 or force:
                    # Decrement only if it's a real spin (not a re-spin or admin force)
                    # But we always want to decrement if player manually clicked.
                    # Per user flow: manually triggered spin MUST decrement.
                    if player.spin_count > 0:
                        player.spin_count -= 1
                        player.save()
                        print(f"[TRANSITION] Decremented spin count for {player.name}. Now: {player.spin_count}")
                    
                    segments = spin_config.get('segments', [])
                    if segments:
                        chosen_index = random.randint(0, len(segments) - 1)
                        chosen = segments[chosen_index]
                        # Construct a reward object
                        reward = {
                            'type': chosen.get('type'),
                            'amount': chosen.get('value', 1),
                            'label': '',
                            'player_name': player.name,
                            'player_id': str(player.id),
                            'custom_name': chosen.get('custom_name', ''),
                            'chosen_index': chosen_index,
                            'total_segments': len(segments)
                        }
                        # Generate label
                        if reward['type'] == 'points': reward['label'] = f"+{reward['amount']} Points"
                        elif reward['type'] == 'snack_reward': 
                            reward['label'] = f"Snack: {reward['custom_name']}" if reward['custom_name'] else "Snack Reward!"
                        elif reward['type'] == 'spin_again': reward['label'] = "Spin Again!"
                        elif reward['type'] == 'jackpot': reward['label'] = "JACKPOT!"
                        elif reward['type'] == 'zonk': reward['label'] = "ZONK!"
                        elif reward['type'] == 'double_points': reward['label'] = "Double Points!"
                        elif reward['type'] == 'custom':
                            reward['label'] = reward['custom_name'] or "Custom Prize!"
                        
                        # Merge with existing gs_data
                        new_gs_data = gs_data.copy()
                        new_gs_data['reward'] = reward
                        new_gs_data['player_id'] = player_id
                        new_gs_data['current_spinner_id'] = player_id
                        # Prediction for next spinner
                        new_gs_data['next_spinner_id'] = queue[1]['id'] if len(queue) > 1 else None
                        
                        print(f"[TRANSITION] Spin successful: {reward['label']} (Index: {chosen_index})")
                        state_data = new_gs_data
                        timer = 5 # Spin animation time (User requested 4-6s)
                    else:
                        print(f"[TRANSITION] Spin failed: Wheel not configured")
                        return False, "Wheel not configured"
                else:
                    print(f"[TRANSITION] Spin failed: No spins available for {player.name}")
                    return False, "No spins available"
            except Player.DoesNotExist:
                print(f"[TRANSITION] Spin failed: Player {player_id} not found")
                return False, "Player not found"
        else:
            return False, "Player ID required"

    elif new_state == 'GACHA_REVEAL':
        from games.gacha.logic import generate_gacha_boxes_v2
        config = state_data or {}
        current_round = config.get('round', 1)
        round_configs = config.get('round_configs', [])
        
        if round_configs and len(round_configs) >= current_round:
            round_setup = round_configs[current_round - 1]
            manual_boxes = round_setup.get('manual_slots')
            box_count = round_setup.get('box_count')
        else:
            manual_boxes = config.get('boxes')
            box_count = config.get('box_count', 12)
        
        if manual_boxes:
            from games.gacha.logic import process_manual_boxes
            boxes = process_manual_boxes(manual_boxes)
        else:
            boxes = generate_gacha_boxes_v2(
                box_count,
                config.get('zonk_count', 2),
                config.get('special_items', [])
            )
        
        state_data = {
            'boxes': boxes, 
            'config': config, 
            'picks': {},
            'interactions': {},
            'current_round': current_round,
            'round_configs': round_configs,
        }
        timer = config.get('timer', 5)

    elif new_state == 'GACHA_SHUFFLE':
        import random
        import copy
        import time
        gs_data = copy.deepcopy(current_gs.state_data)
        boxes = gs_data.get('boxes', [])
        old_ids = [b['id'] for b in boxes]
        random.shuffle(boxes)
        new_ids = [b['id'] for b in boxes]
        gs_data['boxes'] = boxes
        gs_data['shuffle_old_order'] = old_ids
        gs_data['shuffle_new_order'] = new_ids
        gs_data['server_time'] = int(time.time() * 1000)
        state_data = gs_data
        timer = 5

    elif new_state == 'GACHA_PICK':
        import copy
        state_data = copy.deepcopy(current_gs.state_data)
        if 'picks' not in state_data:
            state_data['picks'] = {}
        state_data.pop('shuffle_old_order', None)
        state_data.pop('shuffle_new_order', None)
        # NO timer — wait indefinitely until ALL active players have picked.
        # The round will only resolve when check_all_picked returns True.
        timer = None

    elif new_state == 'GACHA_PICK_SUBMIT':
        import copy
        box_id = state_data.get('box_id')
        player_id = str(state_data.get('player_id'))
        player_name = state_data.get('player_name')
        
        if current_gs.current_state != 'GACHA_PICK':
            return False, "Not in picking phase"
            
        gs_data = copy.deepcopy(current_gs.state_data)
        boxes = gs_data.get('boxes', [])
        picks = gs_data.get('picks', {})
        
        # --- ATOMIC GUARD ---
        if player_id in picks:
            return False, "You have already picked a box"
            
        box = next((b for b in boxes if str(b['id']) == str(box_id)), None)
        if not box:
            return False, "Box not found"
        if box['player_id'] is not None:
            return False, "Box already taken"

        # --- CLAIM BOX ---
        from players.models import Player
        box['player_id'] = player_id
        box['player_name'] = player_name
        picks[player_id] = box_id
        
        pick_event = {
            'box_id': box_id,
            'player_id': player_id,
            'player_name': player_name,
            'reward': None,
            'event_type': 'prize_won',
        }
        
        try:
            p = Player.objects.get(id=player_id)
            
            # --- SECURITY GUARD ---
            if p.status != 'active':
                return False, "You are eliminated and cannot pick."
                
            reward = box['reward']
            is_powerup_ability = False
            
            # Check if this reward should be deferred to Power-Up phase
            if reward.get('type') == 'zonk' and p.shield_count > 0:
                # Zonk + has shield → defer to powerup
                is_powerup_ability = True
                box['powerup'] = 'shield'
            elif reward.get('type') == 'zonk':
                # Zonk without shield → immediate elimination
                apply_box_reward(p, box, room_code)
                box['revealed'] = True
                pick_event['event_type'] = 'player_eliminated'
                pick_event['reward'] = reward
            elif reward.get('type') == 'special' and reward.get('item') in ('steal', 'swap', 'double'):
                # Special abilities → defer to powerup
                is_powerup_ability = True
                box['powerup'] = reward['item']
            else:
                # Regular rewards (points, snacks, spins, shield, jackpot) → apply immediately
                apply_box_reward(p, box, room_code)
                pick_event['reward'] = reward
                box['revealed'] = True

            if is_powerup_ability:
                box['revealed'] = False
                pick_event['event_type'] = 'powerup_pending'
                pick_event['reward'] = reward
                
        except Player.DoesNotExist:
            pass

        gs_data['boxes'] = boxes
        gs_data['picks'] = picks
        gs_data['_last_pick_event'] = pick_event
        
        all_picked = check_all_picked(room_code, picks)
        gs_data['_all_picked'] = all_picked
        
        state_manager.update_game_state(room_code, 'GACHA_PICK', gs_data) 
        return True, "Selection recorded"

    elif new_state == 'GACHA_RESULT':
        from players.models import Player
        import copy
        gs_data = copy.deepcopy(current_gs.state_data)
        boxes = gs_data.get('boxes', [])
        picks = gs_data.get('picks', {})
        all_players = Player.objects.filter(room__code=room_code, status='active')
        
        # --- GUARD: Do NOT resolve if any active player has not picked ---
        active_ids = set(str(p.id) for p in all_players)
        picked_ids = set(picks.keys())
        missing_players = active_ids - picked_ids
        if missing_players and not force:
            missing_names = [p.name for p in all_players if str(p.id) in missing_players]
            return False, f"Waiting for players to pick: {', '.join(missing_names)}"
        
        # NO auto-assignment. Players who have not picked simply do not receive a box.
        # (This block intentionally left empty — no assign_random_box / assign_zonk.)

        # Apply remaining basic rewards (skip powerup abilities)
        for box in boxes:
            if not box.get('player_id') or box.get('revealed'): continue
            if box.get('powerup'):
                continue  # Skip — handled in GACHA_POWERUP
            try:
                p = Player.objects.get(id=box['player_id'])
                reward = box['reward']
                # Auto-picked boxes: check if they're powerup abilities
                if reward.get('type') == 'zonk' and p.shield_count > 0:
                    box['powerup'] = 'shield'
                    continue
                elif reward.get('type') == 'special' and reward.get('item') in ('steal', 'swap', 'double'):
                    box['powerup'] = reward['item']
                    continue
                apply_box_reward(p, box, room_code)
                box['revealed'] = True
            except Player.DoesNotExist: continue
        
        # Collect powerup abilities
        powerup_abilities = []
        
        # 1. Add carried abilities from previous rounds
        for p in all_players:
            if p.pending_ability:
                powerup_abilities.append({
                    'player_id': str(p.id),
                    'player_name': p.name,
                    'ability': p.pending_ability,
                    'box_id': None,
                    'reward_label': f"Carried {p.pending_ability.upper()}",
                    'status': 'unused',
                })
        
        # 2. Add current round abilities
        for box in boxes:
            if box.get('powerup') and box.get('player_id'):
                try:
                    p = Player.objects.get(id=box['player_id'])
                    # If they already have a carried ability, they overwrite it/queue it.
                    # We will just append it as a separate powerup event.
                    powerup_abilities.append({
                        'player_id': str(p.id),
                        'player_name': p.name,
                        'ability': box['powerup'],
                        'box_id': box['id'],
                        'reward_label': box['reward'].get('label', ''),
                        'status': 'unused',
                    })
                except Player.DoesNotExist:
                    pass
        
        # Build round results summary
        round_results = []
        for box in boxes:
            if box.get('player_id'):
                reward = box.get('reward', {}) or {}
                try:
                    p = Player.objects.get(id=box['player_id'])
                    round_results.append({
                        'player_id': str(p.id),
                        'player_name': p.name,
                        'reward_label': reward.get('label', 'Unknown'),
                        'reward_type': reward.get('type', ''),
                        'reward_item': reward.get('item', ''),
                        'eliminated': p.status == 'eliminated',
                        'auto_picked': box.get('auto_picked', False),
                        'has_powerup': bool(box.get('powerup')),
                        'powerup_type': box.get('powerup', ''),
                    })
                except Player.DoesNotExist:
                    pass
        
        state_data = gs_data
        state_data['boxes'] = boxes
        state_data['picks'] = picks
        state_data['round_results'] = round_results
        state_data['powerup_abilities'] = powerup_abilities
        state_data['_has_powerups'] = len(powerup_abilities) > 0
        
        # Add default timers if no explicit timer is provided
        if timer is None:
            from players.models import Player
            active_count = Player.objects.filter(room__code=room_code, status='active').count()
            
            if state_data['_has_powerups']:
                timer = 3
            elif active_count == 0 or gs_data.get('current_round', 1) >= len(gs_data.get('round_configs', [])):
                timer = 6
            else:
                timer = 6

    elif new_state == 'GACHA_POWERUP':
        import copy
        gs_data = copy.deepcopy(current_gs.state_data)
        gs_data['powerup_actions'] = {}
        state_data = gs_data
        timer = 10

    elif new_state == 'UNDERCOVER_WORD':
        # Initializing data is already done by start_undercover_game result
        # Just ensure assignments are present
        pass

    elif new_state == 'UNDERCOVER_DISCUSSION':
        state_data = current_gs.state_data or {}
        
        # Initialize turn-based discussion ONLY if not already in progress
        if 'turn_order' not in state_data:
            assignments = state_data.get('assignments', {})
            import random
            player_ids = list(assignments.keys())
            random.shuffle(player_ids)
            
            state_data['turn_order'] = player_ids
            state_data['current_turn_index'] = 0
            state_data['clues'] = []
            timer = 15
        else:
            # Advance to next player or to VOTING
            state_data['current_turn_index'] += 1
            if state_data['current_turn_index'] >= len(state_data['turn_order']):
                # All players have spoken, transition to VOTING
                return transition_to(room_code, 'UNDERCOVER_VOTE', {}, 30, True)
            timer = 15

    elif new_state == 'UNDERCOVER_VOTE':
        state_data = current_gs.state_data or {}
        state_data['votes'] = {}
        timer = state_data.get('timer', 30)

    elif new_state == 'UNDERCOVER_RESULT':
        gs_data = current_gs.state_data or {}
        votes = gs_data.get('votes', {})
        assignments = gs_data.get('assignments', {})
        current_round = gs_data.get('round', 1)
        total_rounds = 5
        
        # Count votes
        vote_counts = {}
        for voter, target in votes.items():
            vote_counts[target] = vote_counts.get(target, 0) + 1
        
        # Find player with most votes (Eliminated Player)
        most_voted_id = None
        is_undercover_caught = False
        if vote_counts:
            # Handle ties by picking the first one
            most_voted_id = max(vote_counts, key=vote_counts.get)
            most_voted_assignment = assignments.get(most_voted_id, {})
            is_undercover_caught = most_voted_assignment.get('role') == 'undercover'
            
        gs_data['most_voted_id'] = most_voted_id
        gs_data['is_undercover_caught'] = is_undercover_caught
        gs_data['vote_counts'] = vote_counts
        gs_data['eliminated_player'] = most_voted_id
        
        # Word info
        undercover_id = next((pid for pid, a in assignments.items() if a['role'] == 'undercover'), None)
        undercover_word = assignments.get(undercover_id, {}).get('word', '???')
        civilian_word = next((a['word'] for pid, a in assignments.items() if a['role'] == 'civilian'), '???')
        
        gs_data['undercover_player_id'] = undercover_id
        gs_data['undercover_player_name'] = "" # Will fill below
        gs_data['civilian_word'] = civilian_word
        gs_data['undercover_word'] = undercover_word
        
        # Find winner
        round_winner = "civilians" if is_undercover_caught else "undercover"
        gs_data['round_winner'] = round_winner
        
        # Apply points and build scoreboard
        from players.models import Player
        players = Player.objects.filter(room__code=room_code)
        
        if is_undercover_caught:
            # Civilians win: Everyone except the undercover gets points
            for p in players:
                if str(p.id) != undercover_id:
                    p.points += 20
                    p.save()
        else:
            # Undercover wins: Spy gets points
            if undercover_id:
                try:
                    u = Player.objects.get(id=undercover_id)
                    u.points += 50
                    u.save()
                except Player.DoesNotExist: pass
        
        # Update names and scoreboard
        scoreboard = {}
        for p in players:
            scoreboard[p.name] = p.points
            if str(p.id) == undercover_id:
                gs_data['undercover_player_name'] = p.name
                
        gs_data['scoreboard'] = scoreboard
        gs_data['round'] = current_round
        gs_data['total_rounds'] = total_rounds
        gs_data['is_tournament_finished'] = current_round >= total_rounds
        
        state_data = gs_data
        timer = 0 # Wait for host to click Next Round

    elif new_state == 'GAME_FINISHED':
        from players.models import Player
        from rooms.models import Room
        try:
            room = Room.objects.get(code=room_code)
            players = room.players.all().order_by('-points')
            leaderboard = []
            for i, p in enumerate(players):
                leaderboard.append({
                    'rank': i + 1,
                    'name': p.name,
                    'points': p.points,
                    'spins': p.spin_count,
                    'id': str(p.id)
                })
            state_data = state_data or {}
            state_data['leaderboard'] = leaderboard
        except Room.DoesNotExist: pass

    elif new_state == 'SPINWHEEL_RESULT':
        from players.models import Player
        
        # --- IDEMPOTENCY GUARD ---
        if current_gs.current_state == 'SPINWHEEL_RESULT':
            return False, "Already in SPINWHEEL_RESULT state"
            
        gs_data = current_gs.state_data or {}
        reward = gs_data.get('reward')
        player_id = gs_data.get('player_id')
        
        if reward and player_id:
            try:
                player = Player.objects.get(id=player_id)
                # Apply reward
                rtype = reward.get('type')
                amount = int(reward.get('amount', 1))
                
                if rtype == 'points':
                    player.points += amount
                elif rtype == 'snack_reward':
                    player.snack_count += amount
                    player.points += 10 * amount
                elif rtype == 'spin_again':
                    player.spin_count += 1
                elif rtype == 'jackpot':
                    player.jackpot_count += 1
                    player.spin_count += 1
                elif rtype == 'zonk':
                    player.points = max(0, player.points - 10)
                elif rtype == 'double_points':
                    player.double_next_round = True
                
                player.save()
                
                # Add to history
                history = gs_data.get('spin_history', [])
                history.insert(0, {
                    'player_name': player.name,
                    'label': reward['label'],
                    'type': rtype,
                    'time': str(timezone.now())
                })
                gs_data['spin_history'] = history[:50] # Keep last 50
                
            except Player.DoesNotExist:
                pass
        
        # Check for SPIN_TOURNAMENT_END
        queue = gs_data.get('spin_queue', [])
        spin_config = gs_data.get('spin_config', {})
        cost = gs_data.get('spin_config', {}).get('spin_cost_points', 10)
        
        # If queue is empty, check if anyone could possibly spin
        can_anyone_spin = False
        if not queue:
            room = current_gs.room
            players = Player.objects.filter(room=room)
            for p in players:
                if p.spin_count > 0 or p.points >= cost:
                    can_anyone_spin = True
                    break
        else:
            can_anyone_spin = True
            
        if not can_anyone_spin:
            # We will handle the broadcast in consumer, but maybe change state?
            # User wants SPIN_TOURNAMENT_END broadcast.
            gs_data['_tournament_ended'] = True

        state_data = gs_data
        timer = 6 # Result display time

    elif new_state == 'LOBBY' and force:
        if state_data and state_data.get('reset'):
            from .state_manager import reset_gacha_game
            try:
                reset_gacha_game(room_code)
            except Exception as e:
                print(f"[ERROR] reset_gacha_game failed: {e}")
                
        # To reset game-related state (current_round, box_state, picks, etc)
        # but preserve spin configurations across tournaments:
        old_data = current_gs.state_data or {}
        state_data = {}
        if 'spin_config' in old_data:
            state_data['spin_config'] = old_data['spin_config']
        if 'spin_history' in old_data:
            state_data['spin_history'] = old_data['spin_history']

    success = state_manager.update_game_state(room_code, new_state, state_data, timer)
    if success:
        return True, "Transition successful"
    return False, "Failed to update state"


def apply_box_reward(player, box, room_code, player_choice=None):
    """ Helper to apply non-powerup rewards from a box to a player. """
    from players.models import Player
    import random
    
    reward = box['reward']
    player.refresh_from_db()

    # --- APPLY DOUBLE NEXT ROUND EFFECT ---
    if player.double_next_round and reward.get('type') != 'zonk':
        if reward.get('type') in ('points', 'spins', 'snack'):
            reward['amount'] = reward.get('amount', 1) * 2
            reward['label'] += " x2"
        # Reset after use
        player.double_next_round = False
    elif reward.get('type') == 'zonk':
        # Clear double if hit zonk (per user instruction)
        player.double_next_round = False

    if reward['type'] == 'points':
        player.points += reward['amount']
    elif reward['type'] == 'spins':
        player.spin_count += reward['amount']
    elif reward['type'] == 'snack':
        player.snack_count += reward.get('amount', 1)
        player.points += 10 * reward.get('amount', 1)
    elif reward['type'] == 'zonk':
        player.points = max(0, player.points - 10)
        player.status = 'eliminated'
        box['eliminated'] = True
    elif reward['type'] == 'special':
        item = reward['item']
        if item == 'shield':
            player.shield_count += 1
            box['effect_desc'] = "+1 Shield Gained!"
        elif item == 'jackpot_spin':
            player.spin_count += 1
            player.jackpot_count += 1
            box['effect_desc'] = "REWARD: 1 SPIN + 1 JACKPOT TOKEN!"
        # steal, swap, double are handled in powerup phase
    
    player.save()


def resolve_powerup_abilities(room_code, gs_data):
    """
    Resolve all powerup abilities in order: Shield → Steal → Swap → Double.
    Returns updated gs_data with all abilities applied.
    """
    from players.models import Player
    import random
    
    abilities = gs_data.get('powerup_abilities', [])
    actions = gs_data.get('powerup_actions', {})
    boxes = gs_data.get('boxes', [])
    
    # Sort by execution order
    order = {'shield': 1, 'steal': 2, 'swap': 3, 'double': 4}
    abilities.sort(key=lambda a: order.get(a['ability'], 99))
    
    for ability in abilities:
        pid = ability['player_id']
        ab_type = ability['ability']
        box_id = ability.get('box_id')
        action = actions.get(pid, {})
        box = next((b for b in boxes if b.get('id') == box_id), None)
            
        try:
            player = Player.objects.get(id=pid)
        except Player.DoesNotExist:
            continue
        
        player.refresh_from_db()
        
        has_acted = str(pid) in actions
        
        # If no action was taken, they carry the ability to the next round
        if not has_acted:
            if ab_type == 'shield':
                # Carry shield, but accept Zonk for this round
                player.points = max(0, player.points - 10)
                player.status = 'eliminated'
                if box:
                    box['revealed'] = True
                    box['eliminated'] = True
                    box['effect_desc'] = "ZONK - Eliminated! (Shield Carried)"
                ability['status'] = 'carried'
                # Notice we do NOT decrement shield_count, so they keep it. There's no need to set pending_ability for shield since shield_count persists natively.
            else:
                player.pending_ability = ab_type
                ability['status'] = 'carried'
                if box:
                    box['revealed'] = True
                    box['effect_desc'] = f"{ab_type.upper()} CARRIED ➡️"
            player.save()
            continue
            
        # Player acted:
        if ab_type == 'shield':
            use_shield = action.get('value', False)
            if use_shield and player.shield_count > 0:
                player.shield_count -= 1
                if box:
                    box['revealed'] = True
                    box['effect_desc'] = "Shield Used! Safe from Zonk."
                ability['status'] = 'used'
            else:
                player.points = max(0, player.points - 10)
                player.status = 'eliminated'
                if box:
                    box['revealed'] = True
                    box['eliminated'] = True
                    box['effect_desc'] = "ZONK - Eliminated!"
                ability['status'] = 'carried'
            player.save()
            
        elif ab_type == 'steal':
            target_id = action.get('target_id')
            if target_id:
                try:
                    victim = Player.objects.get(id=target_id)
                    steal_amount = min(15, victim.points)
                    victim.points = max(0, victim.points - steal_amount)
                    victim.save()
                    player.points += steal_amount
                    if box:
                        box['revealed'] = True
                        box['effect_desc'] = f"Stole {steal_amount} pts from {victim.name}!"
                    ability['status'] = 'used'
                    ability['target_name'] = victim.name
                    player.pending_ability = None
                except Player.DoesNotExist:
                    if box: box['revealed'] = True
                    ability['status'] = 'carried'
            else:
                # If they hit skip button during steal
                if box:
                    box['revealed'] = True
                    box['effect_desc'] = "STEAL CARRIED ➡️"
                ability['status'] = 'carried'
                player.pending_ability = 'steal'
            player.save()

        elif ab_type == 'swap':
            target_id = action.get('target_id')
            if target_id:
                try:
                    rival = Player.objects.get(id=target_id)
                    player.points, rival.points = rival.points, player.points
                    rival.save()
                    if box:
                        box['revealed'] = True
                        box['effect_desc'] = f"Swapped points with {rival.name}!"
                    ability['status'] = 'used'
                    ability['target_name'] = rival.name
                    player.pending_ability = None
                except Player.DoesNotExist:
                    if box: box['revealed'] = True
                    ability['status'] = 'carried'
            else:
                if box:
                    box['revealed'] = True
                    box['effect_desc'] = "SWAP CARRIED ➡️"
                ability['status'] = 'carried'
                player.pending_ability = 'swap'
            player.save()

        elif ab_type == 'double':
            activate = action.get('value', False)
            if activate:
                player.double_next_round = True
                if box:
                    box['revealed'] = True
                    box['effect_desc'] = "Double activated for NEXT round!"
                ability['status'] = 'used'
                player.pending_ability = None
            else:
                if box:
                    box['revealed'] = True
                    box['effect_desc'] = "DOUBLE CARRIED ➡️"
                ability['status'] = 'carried'
                player.pending_ability = 'double'
            player.save()
        
        if box:
            box.pop('powerup', None)
    
    gs_data['boxes'] = boxes
    gs_data['powerup_abilities'] = abilities
    return gs_data


def check_all_picked(room_code, picks):
    """Check if all active players have picked a box."""
    from players.models import Player
    from rooms.models import Room
    try:
        room = Room.objects.get(code=room_code)
        active_players = room.players.filter(status='active')
        active_count = active_players.count()
        picked_count = len(picks)
        
        # If no active players remain, but picks were made, everyone was eliminated this round.
        if active_count == 0:
            return picked_count > 0
        
        # Only use active player IDs to verify completion
        active_ids = set(str(p.id) for p in active_players)
        picked_ids = set(picks.keys())
        # All active players must be present in the picked set
        return active_ids.issubset(picked_ids)
    except Room.DoesNotExist:
        return False

def check_pick_completion(room_code):
    """
    Check if all active players have made their picks and progress the round.
    Only resolves when EVERY active player has explicitly picked.
    """
    current_gs = get_current_state(room_code)
    if not current_gs:
        return False, "Room not found"

    picks = current_gs.state_data.get('picks', {})
    
    if check_all_picked(room_code, picks):
        transition_to(room_code, 'GACHA_RESULT')

def automatic_round_progression(room_code):
    """
    Automatically progress through the phases of a round.
    """
    current_gs = get_current_state(room_code)
    if not current_gs:
        return False, "Room not found"

    current_state = current_gs.current_state
    if current_state == 'GACHA_PICK':
        # Check if all active players have explicitly picked
        picks = current_gs.state_data.get('picks', {})
        if check_all_picked(room_code, picks):
            transition_to(room_code, 'GACHA_RESULT')

    elif current_state == 'GACHA_RESULT':
        # Resolve abilities if any
        abilities = current_gs.state_data.get('abilities', {})
        players_need_action = [p for p in abilities if abilities[p] in ['shield', 'steal', 'swap', 'double']]
        if not players_need_action:
            transition_to(room_code, 'ROUND_RESULT')

    elif current_state == 'ROUND_RESULT':
        # Progress to the next round
        game_session = GameSession.objects.get(room__code=room_code)
        game_session.current_round += 1
        game_session.save()

        # Initialize new round state
        RoundState.objects.create(
            game_session=game_session,
            round_number=game_session.current_round,
            box_state={},
            picks={},
            abilities={},
            eliminations=[]
        )
        transition_to(room_code, 'GACHA_PICK')

def resolve_ability_phase(room_code):
    """
    Resolve the ability phase by checking if all players with abilities have acted.
    """
    current_gs = get_current_state(room_code)
    if not current_gs:
        return False, "Room not found"

    abilities = current_gs.state_data.get('abilities', {})
    players_need_action = [p for p in abilities if abilities[p] in ['shield', 'steal', 'swap', 'double']]

    if players_need_action:
        # Check if all players have submitted their actions
        actions_submitted = all(abilities[p].get('action_submitted', False) for p in players_need_action)
        if actions_submitted:
            transition_to(room_code, 'ROUND_RESULT')
    else:
        # Skip the ability phase if no players have abilities
        transition_to(room_code, 'ROUND_RESULT')

def check_end_condition(room_code):
    """
    Check if the game should end based on the number of remaining boxes.
    """
    current_gs = get_current_state(room_code)
    if not current_gs:
        return False, "Room not found"

    boxes = current_gs.state_data.get('boxes', [])
    remaining_boxes = len([b for b in boxes if not b.get('revealed')])

    if remaining_boxes <= 3:  # Example threshold
        transition_to(room_code, 'GAME_FINISHED')
