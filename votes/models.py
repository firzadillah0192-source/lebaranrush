from django.db import models
from rooms.models import Room
from players.models import Player

class Vote(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='votes')
    voter = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='votes_cast')
    target_player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='votes_received')

    class Meta:
        unique_together = ('room', 'voter')

    def __str__(self):
        return f"{self.voter.name} -> {self.target_player.name}"
