from .state_manager import update_game_state

VALID_TRANSITIONS = {
    'LOBBY': ['GACHA_CONFIG', 'UNDERCOVER_WORD', 'SPINWHEEL_READY', 'GAME_FINISHED'],
    
    # Gacha flow (Refined)
    'GACHA_CONFIG': ['GACHA_REVEAL'],
    'GACHA_REVEAL': ['GACHA_SHUFFLE'],
    'GACHA_SHUFFLE': ['GACHA_PICK'],
    'GACHA_PICK': ['GACHA_RESULT'],
    'GACHA_RESULT': ['LOBBY', 'SPINWHEEL_READY'],
    
    # Undercover flow
    'UNDERCOVER_WORD': ['UNDERCOVER_DISCUSSION'],
    'UNDERCOVER_DISCUSSION': ['UNDERCOVER_VOTE'],
    'UNDERCOVER_VOTE': ['UNDERCOVER_RESULT'],
    'UNDERCOVER_RESULT': ['LOBBY', 'SPINWHEEL_READY'],
    
    # Spin Wheel flow
    'SPINWHEEL_READY': ['SPINWHEEL_SPIN'],
    'SPINWHEEL_SPIN': ['SPINWHEEL_RESULT'],
    'SPINWHEEL_RESULT': ['LOBBY', 'GACHA_SETUP', 'UNDERCOVER_WORD'],
    
    # End state
    'GAME_FINISHED': []
}

def transition_to(room_code, new_state, state_data=None, timer=None, force=False):
    """
    Safely transition to a new game state.
    """
    from .state_manager import get_current_state
    current_gs = get_current_state(room_code)
    
    if not current_gs:
        return False, "Room not found"
        
    if not force:
        allowed = VALID_TRANSITIONS.get(current_gs.current_state, [])
        if new_state not in allowed:
            return False, f"Invalid transition from {current_gs.current_state} to {new_state}"
            
    # Handle specialized logic per state
    if new_state == 'SPINWHEEL_SPIN':
        # Generate reward for player
        from games.spinwheel.logic import generate_weighted_reward
        from players.models import Player
        player_id = state_data.get('player_id')
        if player_id:
            try:
                player = Player.objects.get(id=player_id)
                if player.spin_count > 0 or force:
                    if not force:
                        player.spin_count -= 1
                        player.save()
                    
                    reward = generate_weighted_reward(is_guest=False)
                    state_data['reward'] = reward
                    # Auto transition to result after 5s animation
                    timer = 5 
                else:
                    return False, "No spins available"
            except Player.DoesNotExist:
                return False, "Player not found"

    elif new_state == 'GACHA_REVEAL':
        # Generate boxes based on config from previous state (CONFIG)
        from games.gacha.logic import generate_gacha_boxes_v2
        config = state_data or {} # Config passed by host
        boxes = generate_gacha_boxes_v2(
            config.get('box_count', 12),
            config.get('zonk_count', 2),
            config.get('special_items', [])
        )
        state_data = {'boxes': boxes, 'config': config}
        timer = 5 # Reveal for 5s as requested

    elif new_state == 'GACHA_PICK':
        # Handle a player picking a box
        box_id = state_data.get('box_id')
        player_id = state_data.get('player_id')
        player_name = state_data.get('player_name')
        
        if box_id is not None and player_id:
            boxes = current_gs.state_data.get('boxes', [])
            # Find the box and check if it's already taken
            box = next((b for b in boxes if b['id'] == box_id), None)
            if box and box['player_id'] is None:
                # Assign box to player
                box['player_id'] = player_id
                box['player_name'] = player_name
                # Keep state_data updated for current state
                state_data = current_gs.state_data
                state_data['boxes'] = boxes
            else:
                return False, "Box already taken or invalid"

    elif new_state == 'GACHA_RESULT':
        # Apply rewards to players when transitioning to result
        from players.models import Player
        import random
        
        boxes = current_gs.state_data.get('boxes', [])
        all_players = list(Player.objects.filter(room__code=room_code))
        
        for box in boxes:
            if box['player_id']:
                try:
                    p = Player.objects.get(id=box['player_id'])
                    reward = box['reward']
                    
                    if reward['type'] == 'points':
                        p.points += reward['amount']
                    elif reward['type'] == 'spins':
                        p.spin_count += reward['amount']
                    elif reward['type'] == 'zonk':
                        p.points = max(0, p.points - 10) # Small penalty instead of reset
                    elif reward['type'] == 'special':
                        item = reward['item']
                        if item == 'steal':
                            # Steal 15 from random opponent
                            rivals = Player.objects.filter(room__code=room_code).exclude(id=p.id)
                            opponents_with_points = [r for r in rivals if r.points >= 15]
                            if opponents_with_points:
                                victim = random.choice(opponents_with_points)
                                victim.points -= 15
                                victim.save()
                                p.points += 15
                                box['effect_desc'] = f"Stole 15 pts from {victim.name}!"
                        elif item == 'swap':
                            # Swap with highest
                            rivals = Player.objects.filter(room__code=room_code).exclude(id=p.id)
                            if rivals:
                                richest = max(rivals, key=lambda x: x.points)
                                if richest.points > p.points:
                                    # Refresh p to get latest points (in case they were stolen from/to)
                                    p.refresh_from_db()
                                    p.points, richest.points = richest.points, p.points
                                    richest.save()
                                    box['effect_desc'] = f"Swapped points with {richest.name}!"
                        elif item == 'double':
                            p.points *= 2
                            box['effect_desc'] = "Points Doubled!"
                        elif item == 'shield':
                            p.points += 25
                            box['effect_desc'] = "Safe Prize: 25 Points"
                        elif item == 'jackpot_spin':
                            p.spin_count += 10
                            box['effect_desc'] = "10 BONUS SPINS!"
                            
                    p.save()
                    box['revealed'] = True
                except Player.DoesNotExist:
                    continue
        state_data = current_gs.state_data
        state_data['boxes'] = boxes

    elif new_state == 'GAME_FINISHED':
        # Get final leaderboard
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
        except Room.DoesNotExist:
            return False, "Room not found"

    elif new_state == 'LOBBY' and force:
        # Check if we should reset player stats (Play Again)
        if state_data and state_data.get('reset'):
            from rooms.models import Room
            try:
                room = Room.objects.get(code=room_code)
                for p in room.players.all():
                    p.points = 0
                    p.spin_count = 0
                    p.save()
            except Room.DoesNotExist:
                pass

    success = update_game_state(room_code, new_state, state_data, timer)
    if success:
        return True, "Transition successful"
    return False, "Failed to update state"
