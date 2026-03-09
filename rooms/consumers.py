import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Room, GameState
from players.models import Player
from engine.transitions import transition_to
from engine.state_manager import get_current_state

class RoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code']
        self.room_group_name = f'room_{self.room_code}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Send current state upon connection
        state = await self.get_room_state()
        if state:
            await self.send(text_data=json.dumps({
                "action": "game_state_update",
                "state": state.current_state,
                "data": state.state_data,
                "timer": state.timer_duration,
                "started_at": state.state_started_at.isoformat() if state.state_started_at else None
            }))

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')

        if action == 'player_join':
            player_id = data.get('player_id')
            player_name = data.get('player_name')
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'room_message',
                    'action': 'player_join',
                    'player_id': player_id,
                    'player_name': player_name,
                }
            )

        elif action == 'chat_message':
            player_id = data.get('player_id')
            player_name = data.get('player_name')
            message = data.get('message')
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'room_message',
                    'action': 'chat_message',
                    'player_id': player_id,
                    'player_name': player_name,
                    'message': message,
                }
            )

        elif action == 'state_transition_request':
            # This is typically sent by the Host
            new_state = data.get('new_state')
            state_data = data.get('state_data', {})
            timer = data.get('timer')
            force = data.get('force', False)
            
            # Use engine to transition (handles DB update and group broadcast)
            await database_sync_to_async(transition_to)(
                self.room_code, new_state, state_data, timer, force
            )

        elif action == 'exchange_points_request':
            player_id = data.get('player_id')
            await self.exchange_points(player_id)

    # Receive message from room group
    async def room_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps(event))

    async def game_state_update(self, event):
        # Specific handler for state updates from engine
        await self.send(text_data=json.dumps({
            "action": "game_state_update",
            "state": event['state'],
            "data": event['data'],
            "timer": event['timer'],
            "started_at": event['started_at']
        }))

    @database_sync_to_async
    def get_room_state(self):
        try:
            room = Room.objects.get(code=self.room_code)
            state, _ = GameState.objects.get_or_create(room=room)
            return state
        except Exception:
            return None

    @database_sync_to_async
    def exchange_points(self, player_id):
        from players.models import Player
        from rooms.models import Room
        try:
            player = Player.objects.get(id=player_id)
            room = Room.objects.get(code=self.room_code)
            if player.points >= room.spin_cost_points:
                player.points -= room.spin_cost_points
                player.spin_count += 1
                player.save()
        except Exception as e:
            print(f"Error exchanging points: {e}")
