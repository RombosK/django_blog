from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.conf import settings
import hashlib

def get_cache_key(prefix, *args):
    """
    Создает ключ кэша на основе префикса и аргументов
    """
    key = ':'.join([str(arg) for arg in args])
    hash_key = hashlib.md5(key.encode('utf-8')).hexdigest()
    return f"{prefix}:{hash_key}"

def cache_page_data(key_prefix, timeout=300):
    """
    Декоратор для кэширования данных страницы
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            # Создаем уникальный ключ кэша на основе URL и параметров
            cache_key = get_cache_key(key_prefix, request.path, str(args), str(sorted(kwargs.items())))
            
            # Попробуем получить данные из кэша
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return cached_data
            
            # Выполняем вьюху и кэшируем результат
            response = view_func(request, *args, **kwargs)
            
            # Кэшируем только успешные ответы
            if hasattr(response, 'status_code') and response.status_code == 200:
                cache.set(cache_key, response, timeout)
                
            return response
        return wrapper
    return decorator

def invalidate_cache_key(prefix, *args):
    """
    Инвалидирует кэш по префиксу и аргументам
    """
    cache_key = get_cache_key(prefix, *args)
    cache.delete(cache_key)
    return cache_key

def invalidate_template_fragment(fragment_name, *args):
    """
    Инвалидирует фрагмент шаблона
    """
    key = make_template_fragment_key(fragment_name, args)
    cache.delete(key)
    return key

def get_cached_posts(page=1, page_size=5, timeout=300):
    """
    Кэширует список постов с пагинацией
    """
    cache_key = get_cache_key('posts_list', page, page_size)
    cached_posts = cache.get(cache_key)

    if cached_posts is None:
        from blog.models import Post
        posts = Post.objects.filter(is_published=True).select_related('author').only(
            'title', 'created_at', 'author__username'
        ).order_by('-created_at')

        # Пагинация
        start = (page - 1) * page_size
        end = start + page_size
        cached_posts = posts[start:end]

        # Кэшируем результат
        cache.set(cache_key, cached_posts, timeout)

    return cached_posts
