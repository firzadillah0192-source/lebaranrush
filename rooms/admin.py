from django.contrib import admin

from .models import GameSession, GameState, Room, RoundState


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('code', 'status', 'current_game', 'spin_cost_points', 'created_at')
    list_filter = ('status', 'current_game', 'created_at')
    search_fields = ('code', 'host_session')
    ordering = ('-created_at',)


@admin.register(GameSession)
class GameSessionAdmin(admin.ModelAdmin):
    list_display = ('game_id', 'game_type', 'room', 'current_round')
    list_filter = ('game_type',)
    search_fields = ('game_id', 'room__code')


@admin.register(RoundState)
class RoundStateAdmin(admin.ModelAdmin):
    list_display = ('game_session', 'round_number')
    search_fields = ('game_session__game_id',)


@admin.register(GameState)
class GameStateAdmin(admin.ModelAdmin):
    list_display = ('room', 'current_state', 'state_started_at', 'timer_duration')
    list_filter = ('current_state',)
    search_fields = ('room__code',)
