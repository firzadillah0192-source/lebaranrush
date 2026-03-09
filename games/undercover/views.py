from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .game_logic import start_undercover_game

@require_POST
def api_start_undercover(request, room_code):
    result = start_undercover_game(room_code)
    return JsonResponse(result)
