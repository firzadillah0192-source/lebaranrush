import random
from .models import UndercoverWord
from players.models import Player
from rooms.models import Room

def start_undercover_game(room_code):
    room = Room.objects.get(code=room_code)
    players = list(room.players.filter(status='active'))
    
    if len(players) < 3:
        return {"success": False, "error": "Need at least 3 players to play Undercover"}

    # Select random active word pair
    word_pairs = list(UndercoverWord.objects.filter(is_active=True))
    if not word_pairs:
        return {"success": False, "error": "No active words found in the database. Ask Admin to add some!"}

    selected_pair = random.choice(word_pairs)
    
    # Assign roles
    undercover_player = random.choice(players)
    
    # Save current game data in room state or session (for now, simply return the data)
    room.current_game = 'undercover'
    
    # We would normally store the word assignments in a model or cache, but for now we format the payload
    # Let's create a dictionary mapping player IDs to their words to broadcast individually or keep in memory
    
    player_assignments = {}
    for p in players:
        if p.id == undercover_player.id:
            player_assignments[str(p.id)] = {"role": "undercover", "word": selected_pair.word_undercover}
        else:
            player_assignments[str(p.id)] = {"role": "civilian", "word": selected_pair.word_common}
            
    # We might need to store this state in the database if the game must persist across server restarts,
    # but for now, we'll assume we can pass this state via web sockets to the host, who acts as the source of truth
    # OR better yet, we can save it in the database. Let's add a JSONField to Room, or just assume the Host holds the state for now.
    
    return {
        "success": True,
        "assignments": player_assignments,
        "undercover_playerId": str(undercover_player.id)
    }

def reveal_undercover(room_code):
    pass # Host triggers reveal, front-end handles animation
