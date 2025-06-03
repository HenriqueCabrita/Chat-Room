from channels.generic.websocket import AsyncWebsocketConsumer
import json
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from .models import ChatRoom, ChatMessage
import logging

logger = logging.getLogger(__name__)  # For error logging

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Fixed group_discard arguments
        await self.channel_layer.group_discard(
            self.room_group_name,  # Correct first argument
            self.channel_name
        )
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message = data['message']
            username = data['username']
            room = data['room']

            # Save message before broadcasting
            await self.save_message(username, room, message)

            await self.channel_layer.group_send(
                self.room_group_name, {
                    'type': 'chat_message',
                    'message': message,
                    'username': username,
                    'room': room,
                }
            )

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @sync_to_async
    def save_message(self, username, room_slug, message):
        try:
            user = User.objects.get(username=username)
            room = ChatRoom.objects.get(slug=room_slug)
            ChatMessage.objects.create(
                user=user, 
                room=room, 
                message_content=message
            )
        except User.DoesNotExist:
            logger.error(f"User {username} not found")
        except ChatRoom.DoesNotExist:
            logger.error(f"Room {room_slug} not found")
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
