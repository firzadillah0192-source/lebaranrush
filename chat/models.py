from django.db import models
from rooms.models import Room
from players.models import Player

class ChatMessage(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='chat_messages')
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='chat_messages')
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.player.name}: {self.message}"
