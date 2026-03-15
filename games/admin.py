from django.contrib import admin

from .models import GachaRewardConfig, GameResult


@admin.register(GameResult)
class GameResultAdmin(admin.ModelAdmin):
    list_display = ('room', 'player', 'game_name', 'points')
    list_filter = ('game_name',)
    search_fields = ('player__name', 'room__code', 'game_name')


@admin.register(GachaRewardConfig)
class GachaRewardConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'reward_type', 'amount', 'weight', 'is_active')
    list_filter = ('reward_type', 'is_active')
    search_fields = ('name',)
    ordering = ('name',)
