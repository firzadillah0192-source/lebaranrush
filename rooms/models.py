from django.db import models
import uuid

class Room(models.fields.UUIDField):
    pass

# I'll properly define this
import random
import string

def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

class Room(models.Model):
    STATUS_CHOICES = (
        ('waiting', 'Waiting'),
        ('playing', 'Playing'),
        ('finished', 'Finished'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=6, unique=True, default=generate_room_code)
    host_session = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    current_game = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    spin_cost_points = models.IntegerField(default=10)

    def __str__(self):
        return f"Room {self.code}"

class GameSession(models.Model):
    game_id = models.CharField(max_length=255, unique=True)
    game_type = models.CharField(max_length=50, default='gacha')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='sessions')
    current_round = models.IntegerField(default=1)

    def __str__(self):
        return f"Session {self.game_id} for Room {self.room.code}"

class RoundState(models.Model):
    game_session = models.ForeignKey(GameSession, on_delete=models.CASCADE, related_name='rounds')
    round_number = models.IntegerField()
    box_state = models.JSONField(default=dict)
    picks = models.JSONField(default=dict)
    abilities = models.JSONField(default=dict)
    eliminations = models.JSONField(default=list)

    class Meta:
        unique_together = ('game_session', 'round_number')

    def __str__(self):
        return f"Round {self.round_number} for Session {self.game_session.game_id}"

class GameState(models.Model):
    STATE_CHOICES = (
        ('LOBBY', 'Lobby'),
        # Gacha States
        ('GACHA_CONFIG', 'Gacha Config'),
        ('GACHA_REVEAL', 'Gacha Reveal'),
        ('GACHA_SHUFFLE', 'Gacha Shuffle'),
        ('GACHA_PICK', 'Gacha Pick'),
        ('GACHA_INTERACT', 'Gacha Interaction'),
        ('GACHA_RESULT', 'Gacha Result'),
        # Undercover States
        ('UNDERCOVER_WORD', 'Undercover Word Reveal'),
        ('UNDERCOVER_DISCUSSION', 'Undercover Discussion'),
        ('UNDERCOVER_VOTE', 'Undercover Vote'),
        ('UNDERCOVER_RESULT', 'Undercover Result'),
        # Spin Wheel States
        ('SPINWHEEL_READY', 'Spin Wheel Ready'),
        ('SPINWHEEL_SPIN', 'Spin Wheel Spin'),
        ('SPINWHEEL_RESULT', 'Spin Wheel Result'),
        # End State
        ('GAME_FINISHED', 'Game Finished'),
    )

    room = models.OneToOneField(Room, on_delete=models.CASCADE, related_name='game_state')
    current_state = models.CharField(max_length=30, choices=STATE_CHOICES, default='LOBBY')
    state_data = models.JSONField(default=dict, blank=True)
    state_started_at = models.DateTimeField(auto_now_add=True)
    timer_duration = models.IntegerField(null=True, blank=True) # in seconds

    def __str__(self):
        return f"State {self.current_state} for Room {self.room.code}"
