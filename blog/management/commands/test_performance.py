"""
Скрипт для тестирования производительности после оптимизации
"""
import os
import django
from django.conf import settings
from django.test import RequestFactory
import time
from django.core.management.base import BaseCommand
from blog.models import Post, Message, ChatRoom
from django.contrib.auth.models import User
from django.db import connection
from django.core.cache import cache

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blog_project.settings')
django.setup()

class Command(BaseCommand):
    help = 'Тестирование производительности после оптимизации'

    def handle(self, *args, **options):
        self.stdout.write('Запуск тестирования производительности...')
        
        # Тестирование производительности запросов
        self.test_query_performance()
        
        # Тестирование производительности кеширования
        self.test_cache_performance()
        
        # Тестирование производительности чата
        self.test_chat_performance()
        
        self.stdout.write(
            self.style.SUCCESS('Тестирование производительности завершено')
        )

    def test_query_performance(self):
        """Тестирование производительности запросов к БД"""
        self.stdout.write('Тестирование производительности запросов...')
        
        # Тестирование получения опубликованных постов
        start_time = time.time()
        posts = Post.objects.filter(is_published=True).select_related('author').only(
            'title', 'created_at', 'author__username'
        )[:10]
        query_time = time.time() - start_time
        
        self.stdout.write(f'  Время запроса постов: {query_time:.4f}с')
        
        # Тестирование количества запросов
        initial_queries = len(connection.queries)
        for post in posts:
            _ = post.author.username  # Доступ к связанному объекту
        additional_queries = len(connection.queries) - initial_queries
        
        self.stdout.write(f'  Дополнительные запросы для связанных объектов: {additional_queries}')

    def test_cache_performance(self):
        """Тестирование производительности кеширования"""
        self.stdout.write('Тестирование производительности кеширования...')
        
        # Тестирование установки значения в кеш
        start_time = time.time()
        cache.set('test_key', 'test_value', 300)
        set_time = time.time() - start_time
        
        # Тестирование получения значения из кеша
        start_time = time.time()
        value = cache.get('test_key')
        get_time = time.time() - start_time
        
        self.stdout.write(f'  Время установки в кеш: {set_time:.6f}с')
        self.stdout.write(f'  Время получения из кеша: {get_time:.6f}с')
        
        # Тестирование очистки кеша
        cache.delete('test_key')

    def test_chat_performance(self):
        """Тестирование производительности чата"""
        self.stdout.write('Тестирование производительности чата...')
        
        # Создание тестовой комнаты
        room, created = ChatRoom.objects.get_or_create(name='test_performance')
        
        # Тестирование получения последних сообщений
        start_time = time.time()
        messages = Message.objects.filter(room=room).select_related('user').only(
            'content', 'created_at', 'user__username'
        ).order_by('-created_at')[:50]
        query_time = time.time() - start_time
        
        self.stdout.write(f'  Время запроса сообщений чата: {query_time:.4f}с')
        
        # Тестирование оптимизированного метода
        start_time = time.time()
        from blog.performance_utils import get_recent_messages_optimized
        optimized_messages = get_recent_messages_optimized(room, limit=50)
        optimized_time = time.time() - start_time
        
        self.stdout.write(f'  Время оптимизированного запроса: {optimized_time:.4f}с')
        
        if query_time > optimized_time:
            improvement = ((query_time - optimized_time) / query_time) * 100
            self.stdout.write(f'  Улучшение производительности: {improvement:.2f}%')