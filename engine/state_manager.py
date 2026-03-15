import json
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rooms.models import GameState, Room, GameSession, RoundState
from django.utils import timezone
from django.db import models

def update_game_state(room_code, new_state, state_data=None, timer=None):
    """
    Update the game state for a room and broadcast it via WebSocket.
    """
    try:
        room = Room.objects.get(code=room_code)
        game_state, created = GameState.objects.get_or_create(room=room)
        
        game_state.current_state = new_state
        if state_data is not None:
            game_state.state_data = state_data
        
        game_state.state_started_at = timezone.now()
        game_state.timer_duration = timer
        game_state.save()
        
        # Broadcast to room group
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"room_{room_code}",
            {
                "type": "game_state_update",
                "state": new_state,
                "data": game_state.state_data,
                "timer": timer,
                "started_at": game_state.state_started_at.isoformat()
            }
        )
        return True
    except Room.DoesNotExist:
        return False

def get_current_state(room_code):
    try:
        room = Room.objects.get(code=room_code)
        game_state, created = GameState.objects.get_or_create(room=room)
        return game_state
    except Room.DoesNotExist:
        return None

def reset_gacha_game(room_code):
    """
    Reset the Gacha game for a new session while preserving persistent player rewards.
    """
    import uuid
    room = Room.objects.get(code=room_code)
    try:
        game_session, _ = GameSession.objects.get_or_create(
            room=room,
            defaults={'game_id': str(uuid.uuid4())}
        )

        # Reset round-specific states
        game_session.current_round = 1
        game_session.save()

        RoundState.objects.filter(game_session=game_session).delete()
        RoundState.objects.create(
            game_session=game_session,
            round_number=1,
            box_state={},
            picks={},
            abilities={},
            eliminations=[]
        )
    except Exception as e:
        print(f"[ERROR] Session Reset error: {e}")

    # Reset player statuses for new tournament
    for player in room.players.all():
        player.status = 'active'
        player.double_next_round = False
        player.pending_ability = None
        # Make sure current_pick and ability_used properties are conceptually clear 
        # (they're actually managed in GameState JSON, but we've explicitly reset the JSON in transitions.py)
        player.save()
