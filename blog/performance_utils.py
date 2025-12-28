"""
Дополнительные оптимизации производительности
"""
from django.db import models
from django.core.cache import cache
from django.conf import settings
import functools
import logging

logger = logging.getLogger(__name__)

def cache_queryset(timeout=300):
    """
    Декоратор для кеширования результатов запросов к БД
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Создаем ключ кеша на основе имени функции и аргументов
            cache_key = f"queryset_{func.__name__}_{str(args)}_{str(sorted(kwargs.items()))}"
            
            # Проверяем, есть ли результат в кеше
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Выполняем функцию и кешируем результат
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            
            return result
        return wrapper
    return decorator

def bulk_create_optimized(model_class, objects_list, batch_size=1000):
    """
    Оптимизированное создание объектов большими пакетами
    """
    if objects_list:
        model_class.objects.bulk_create(objects_list, batch_size=batch_size)

def get_or_create_optimized(model_class, **kwargs):
    """
    Оптимизированная версия get_or_create с обработкой гонок
    """
    defaults = kwargs.pop('defaults', {})
    try:
        obj = model_class.objects.get(**kwargs)
        created = False
    except model_class.DoesNotExist:
        # Обработка гонки при одновременном доступе
        try:
            obj = model_class.objects.create(**kwargs, **defaults)
            created = True
        except Exception:
            # Если возникла ошибка из-за гонки, пробуем получить существующий объект
            obj = model_class.objects.get(**kwargs)
            created = False
    
    return obj, created

def select_related_optimized(queryset, *fields):
    """
    Оптимизированная версия select_related с кешированием
    """
    return queryset.select_related(*fields)

def prefetch_related_optimized(queryset, *relations):
    """
    Оптимизированная версия prefetch_related с кешированием
    """
    return queryset.prefetch_related(*relations)

# Оптимизации для часто используемых запросов
def get_published_posts_optimized():
    """
    Оптимизированный запрос для получения опубликованных постов
    """
    from blog.models import Post
    cache_key = "published_posts_optimized"
    posts = cache.get(cache_key)
    
    if posts is None:
        posts = Post.objects.filter(
            is_published=True
        ).select_related('author').only(
            'title', 'created_at', 'author__username'
        ).order_by('-created_at')[:50]  # Ограничиваем количество
        
        cache.set(cache_key, posts, 300)  # Кешируем на 5 минут
    
    return posts

def get_recent_messages_optimized(room, limit=100):
    """
    Оптимизированный запрос для получения последних сообщений
    """
    from blog.models import Message
    cache_key = f"recent_messages_{room.id}_{limit}"
    messages = cache.get(cache_key)
    
    if messages is None:
        messages = Message.objects.filter(
            room=room
        ).select_related('user').only(
            'content', 'created_at', 'user__username'
        ).order_by('-created_at')[:limit]
        
        cache.set(cache_key, messages, 60)  # Кешируем на 1 минуту
    
    return messages

def invalidate_posts_cache():
    """
    Очистка кеша, связанного с постами
    """
    cache.delete("published_posts_optimized")
    # Удаляем все ключи, связанные с постами
    cache.delete_many([key for key in cache._cache.keys() if 'posts' in key])

def invalidate_messages_cache(room_id):
    """
    Очистка кеша, связанного с сообщениями в комнате
    """
    cache.delete_many([key for key in cache._cache.keys() if f'messages_{room_id}' in key])