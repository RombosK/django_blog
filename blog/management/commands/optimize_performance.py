"""
Дополнительные оптимизации для улучшения производительности
"""
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from blog.models import Message
import logging

logger = logging.getLogger(__name__)

def optimize_database():
    """
    Функция для оптимизации базы данных
    """
    if 'sqlite3' in settings.DATABASES['default']['ENGINE']:
        with connection.cursor() as cursor:
            # Оптимизации для SQLite
            cursor.execute("PRAGMA journal_mode=WAL;")  # Улучшает параллельный доступ
            cursor.execute("PRAGMA synchronous=NORMAL;")  # Улучшает производительность
            cursor.execute("PRAGMA cache_size=10000;")  # Увеличиваем размер кеша
            cursor.execute("PRAGMA temp_store=memory;")  # Временные таблицы в памяти
            logger.info("Оптимизации SQLite применены")

def cleanup_old_messages(max_messages_per_room=1000):
    """
    Очистка старых сообщений для уменьшения размера БД
    """
    from blog.models import ChatRoom
    
    for room in ChatRoom.objects.all():
        # Получаем количество сообщений в комнате
        total_messages = room.messages.count()
        
        if total_messages > max_messages_per_room:
            # Удаляем старые сообщения, оставляя только последние max_messages_per_room
            messages_to_delete = room.messages.order_by('-created_at')[max_messages_per_room:]
            count = messages_to_delete.count()
            messages_to_delete.delete()
            logger.info(f"Удалено {count} старых сообщений из комнаты {room.name}")

class Command(BaseCommand):
    help = 'Оптимизация производительности приложения'

    def handle(self, *args, **options):
        self.stdout.write('Запуск оптимизаций...')
        
        # Применяем оптимизации БД
        optimize_database()
        
        # Очищаем старые сообщения
        cleanup_old_messages()
        
        self.stdout.write(
            self.style.SUCCESS('Оптимизации успешно применены')
        )