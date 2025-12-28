import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from django.contrib.auth.models import User
from blog.models import Message, ChatRoom
from django.core.cache import cache
from django.conf import settings
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)

class OptimizedChatConsumer(WebsocketConsumer):
    """
    Оптимизированная версия чат-консьюмера с улучшенной производительностью
    """
    def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        # Преобразуем имя комнаты в допустимый формат для группы
        import re
        safe_room_name = re.sub(r'[^a-zA-Z0-9\-_\.]', '', self.room_name)
        if not safe_room_name:
            safe_room_name = 'default'
        self.room_group_name = f'chat_{safe_room_name}'

        # Присоединяемся к группе комнаты
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )

        self.accept()

        # Отправляем сообщение о подключении
        from django.utils import timezone
        localized_time = timezone.localtime(timezone.now())
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': f'Пользователь {self.scope["user"].username} присоединился к чату',
                'username': 'System',
                'timestamp': localized_time.strftime('%H:%M')  # Используем локализованное время
            }
        )

    def disconnect(self, close_code):
        # Покидаем группу комнаты
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message = text_data_json.get('message', '')

            # Проверяем, что пользователь аутентифицирован
            if not self.scope['user'].is_authenticated:
                self.send(text_data=json.dumps({
                    'error': 'Authentication required'
                }))
                return

            username = self.scope['user'].username

            # Получаем комнату с минимальным количеством запросов
            room, created = ChatRoom.objects.get_or_create(
                name=self.room_name,
                defaults={'topic': f'Чат для {self.room_name}'}
            )

            # Обработка сообщения
            if message and message != '/join':
                # Ограничиваем длину сообщения
                message_content = message[:1000]
                
                # Создаем сообщение с минимальным количеством операций
                new_message = Message.objects.create(
                    room=room,
                    user=self.scope['user'],
                    content=message_content
                )

                # Отправляем сообщение в группу комнаты
                from django.utils import timezone
                from datetime import datetime
                # Используем локализованное время для корректного отображения с учетом часового пояса
                localized_time = timezone.localtime(timezone.now())
                async_to_sync(self.channel_layer.group_send)(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': message_content,
                        'username': username,
                        'timestamp': localized_time.strftime('%H:%M')  # Используем локализованное время
                    }
                )
        except json.JSONDecodeError:
            self.send(text_data=json.dumps({
                'error': 'Invalid JSON'
            }))
        except Exception as e:
            logger.error(f"Error in chat consumer: {str(e)}")
            self.send(text_data=json.dumps({
                'error': 'Server error'
            }))

    def chat_message(self, event):
        message = event['message']
        username = event['username']
        timestamp = event.get('timestamp', timezone.now().strftime('%H:%M'))

        # Отправляем сообщение клиенту с текущим временем
        self.send(text_data=json.dumps({
            'message': message,
            'username': username,
            'timestamp': timestamp
        }))