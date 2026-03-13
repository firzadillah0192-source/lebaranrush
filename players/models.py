from django.db import models
import uuid
from rooms.models import Room

class Player(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('disconnected', 'Disconnected'),
        ('eliminated', 'Eliminated'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='players')
    session_id = models.CharField(max_length=255)
    score = models.IntegerField(default=0)
    points = models.IntegerField(default=0)
    spin_count = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    shield_count = models.IntegerField(default=0)
    swap_count = models.IntegerField(default=0)
    double_next_round = models.BooleanField(default=False)
    pending_ability = models.CharField(max_length=50, blank=True, null=True)
    snack_count = models.IntegerField(default=0)
    jackpot_count = models.IntegerField(default=0)

    def __str__(self):
        return self.name
