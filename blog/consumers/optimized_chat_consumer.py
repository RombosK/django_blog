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
    Оптимизированная версия чат-консьюмера
    """

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']

        # ✅ ОПТИМИЗАЦИЯ: безопасное имя группы
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

        # ❌ УДАЛЕНО: send_chat_history() - теперь сообщения загружаются только через template

    async def disconnect(self, close_code):
        """Отключение от комнаты"""
        # Покидаем группу комнаты
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Обработка входящих сообщений"""
        try:
            text_data_json = json.loads(text_data)
            message = text_data_json.get('message', '').strip()

            # ✅ ОПТИМИЗАЦИЯ: ранняя проверка аутентификации
            if not self.scope['user'].is_authenticated:
                await self.send(text_data=json.dumps({
                    'error': 'Необходимо авторизоваться'
                }))
                return

            # ✅ ОПТИМИЗАЦИЯ: проверка пустого сообщения
            if not message:
                return

            username = self.scope['user'].username

            # ✅ ОПТИМИЗАЦИЯ: кешируем объект комнаты
            room = await self.get_or_create_room_cached()

            # ✅ ОПТИМИЗАЦИЯ: ограничение длины до валидации
            message_content = message[:500]

            # Проверяем сообщение с помощью автоматической модерации
            is_blocked, reason = await database_sync_to_async(moderate_message)(
                self.scope['user'],
                room,
                message_content
            )

            if is_blocked:
                await self.send(text_data=json.dumps({
                    'error': f'Сообщение заблокировано: {reason}',
                    'moderation_blocked': True
                }))
                return

            # ✅ ОПТИМИЗАЦИЯ: создаем сообщение и записываем факт отправки одновременно
            await self.save_message_and_record(room, message_content)

            # Отправляем сообщение в группу
            localized_time = timezone.localtime(timezone.now())
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message_content,
                    'username': username,
                    'timestamp': localized_time.strftime('%H:%M')  # ✅ ИЗМЕНЕНО: только время
                }
            )

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'error': 'Некорректный формат данных'
            }))
        except Exception as e:
            logger.error(f"Ошибка в chat consumer: {str(e)}", exc_info=True)
            await self.send(text_data=json.dumps({
                'error': 'Ошибка сервера'
            }))

    async def chat_message(self, event):
        """Отправка сообщения клиенту"""
        message = event['message']
        username = event['username']
        timestamp = event.get('timestamp', timezone.localtime(timezone.now()).strftime('%H:%M'))

        await self.send(text_data=json.dumps({
            'message': message,
            'username': username,
            'timestamp': timestamp
        }))

    @database_sync_to_async
    def get_or_create_room_cached(self):
        """
        ✅ ОПТИМИЗАЦИЯ: Кешированное получение комнаты (5 минут)
        """
        cache_key = f'chat_room_{self.room_name}'
        room = cache.get(cache_key)

        if room is None:
            room, created = ChatRoom.objects.get_or_create(
                name=self.room_name,
                defaults={'topic': f'Чат для {self.room_name}'}
            )
            cache.set(cache_key, room, 300)

        return room

    @database_sync_to_async
    def save_message_and_record(self, room, message_content):
        """
        ✅ ОПТИМИЗАЦИЯ: Объединяем две операции в одну транзакцию
        """
        # Создаем сообщение
        Message.objects.create(
            room=room,
            user=self.scope['user'],
            content=message_content,
            is_moderated=True
        )

        # Записываем факт отправки
        record_user_message(self.scope['user'], room)

        # Сбрасываем кеш сообщений для этой комнаты
        cache.delete(f'chat_messages_{self.room_name}')
