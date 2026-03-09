from .state_manager import update_game_state

VALID_TRANSITIONS = {
    'LOBBY': ['GACHA_SETUP', 'UNDERCOVER_WORD', 'SPINWHEEL_READY', 'GAME_FINISHED'],
    
    # Gacha flow
    'GACHA_SETUP': ['GACHA_REVEAL'],
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

    elif new_state == 'GACHA_SETUP':
        # Initialize boxes for the room
        from games.gacha.logic import generate_gacha_boxes
        from rooms.models import Room
        try:
            room = Room.objects.get(code=room_code)
            player_count = room.players.count()
            boxes = generate_gacha_boxes(player_count)
            state_data = state_data or {}
            state_data['boxes'] = boxes
        except Room.DoesNotExist:
            return False, "Room not found"

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
        boxes = current_gs.state_data.get('boxes', [])
        for box in boxes:
            if box['player_id']:
                try:
                    p = Player.objects.get(id=box['player_id'])
                    reward = box['reward']
                    if reward['type'] == 'points':
                        p.points += reward['amount']
                    elif reward['type'] == 'spins':
                        p.spin_count += reward['amount']
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
