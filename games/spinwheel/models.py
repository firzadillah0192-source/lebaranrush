from django.db import models
from rooms.models import Room
import uuid

class GuestSpinToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='guest_tokens')
    guest_name = models.CharField(max_length=100, blank=True, null=True)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Token {self.token} ({'Used' if this.is_used else 'Available'})"
