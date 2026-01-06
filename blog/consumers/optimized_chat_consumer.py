import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from blog.models import Message, ChatRoom
from django.core.cache import cache
from django.conf import settings
import logging
from django.utils import timezone
from blog.moderation_utils import moderate_message, record_user_message
import re

logger = logging.getLogger(__name__)

class OptimizedChatConsumer(AsyncWebsocketConsumer):
    """
    Оптимизированная версия чат-консьюмера с улучшенной производительностью
    """
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        # Преобразуем имя комнаты в допустимый формат для группы
        safe_room_name = re.sub(r'[^a-zA-Z0-9\-_\.]', '', self.room_name)
        if not safe_room_name:
            safe_room_name = 'default'
        self.room_group_name = f'chat_{safe_room_name}'

        # Присоединяемся к группе комнаты
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Отправляем сообщение о подключении
        localized_time = timezone.localtime(timezone.now())
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': f'Пользователь {self.scope["user"].username} присоединился к чату',
                'username': 'System',
                'timestamp': localized_time.strftime('%H:%M')  # Используем локализованное время
            }
        )

    async def disconnect(self, close_code):
        # Покидаем группу комнаты
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message = text_data_json.get('message', '')

            # Проверяем, что пользователь аутентифицирован
            if not self.scope['user'].is_authenticated:
                await self.send(text_data=json.dumps({
                    'error': 'Authentication required'
                }))
                return

            username = self.scope['user'].username

            # Получаем комнату с минимальным количеством запросов
            room = await self.get_or_create_room()

            # Обработка сообщения
            if message and message != '/join':
                # Ограничиваем длину сообщения
                message_content = message[:1000]

                # Проверяем сообщение с помощью автоматической модерации
                is_blocked, reason = await database_sync_to_async(moderate_message)(
                    self.scope['user'],
                    room,
                    message_content
                )

                if is_blocked:
                    # Отправляем пользователю уведомление о блокировке
                    await self.send(text_data=json.dumps({
                        'error': f'Ваше сообщение было заблокировано: {reason}',
                        'moderation_blocked': True
                    }))
                    return

                # Создаем сообщение с минимальным количеством операций
                new_message = await database_sync_to_async(Message.objects.create)(
                    room=room,
                    user=self.scope['user'],
                    content=message_content,
                    is_moderated=True  # Помечаем, что сообщение прошло модерацию
                )

                # Записываем факт отправки сообщения для отслеживания частоты
                await database_sync_to_async(record_user_message)(
                    self.scope['user'],
                    room
                )

                # Отправляем сообщение в группу комнаты
                # Используем локализованное время для корректного отображения с учетом часового пояса
                localized_time = timezone.localtime(timezone.now())
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': message_content,
                        'username': username,
                        'timestamp': localized_time.strftime('%H:%M')  # Используем локализованное время
                    }
                )
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'error': 'Invalid JSON'
            }))
        except Exception as e:
            logger.error(f"Error in chat consumer: {str(e)}")
            await self.send(text_data=json.dumps({
                'error': 'Server error'
            }))

    async def chat_message(self, event):
        message = event['message']
        username = event['username']
        timestamp = event.get('timestamp', timezone.now().strftime('%H:%M'))

        # Отправляем сообщение клиенту с текущим временем
        await self.send(text_data=json.dumps({
            'message': message,
            'username': username,
            'timestamp': timestamp
        }))

    @database_sync_to_async
    def get_or_create_room(self):
        """Асинхронный метод для получения или создания комнаты"""
        room, created = ChatRoom.objects.get_or_create(
            name=self.room_name,
            defaults={'topic': f'Чат для {self.room_name}'}
        )
        return room