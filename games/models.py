from django.db import models
from rooms.models import Room
from players.models import Player


class GameResult(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='results')
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='results')
    game_name = models.CharField(max_length=50)
    points = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.player.name} - {self.game_name}: {self.points} pts"


class GachaRewardConfig(models.Model):
    id = models.BigAutoField(primary_key=True)
    REWARD_TYPE_CHOICES = (
        ('points', 'Points'),
        ('spins', 'Spins'),
    )

    name = models.CharField(max_length=100)
    reward_type = models.CharField(max_length=20, choices=REWARD_TYPE_CHOICES)
    amount = models.PositiveIntegerField(default=1)
    weight = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.reward_type}:{self.amount})"
