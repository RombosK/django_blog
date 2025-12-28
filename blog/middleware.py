from django.db import connection
from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger(__name__)

class DatabaseQueryCountMiddleware(MiddlewareMixin):
    """
    Middleware для мониторинга количества запросов к базе данных.
    """
    def process_request(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            # Сохраняем начальное количество запросов
            request.start_queries = len(connection.queries)
        return None

    def process_response(self, request, response):
        if hasattr(request, 'start_queries'):
            start_queries = getattr(request, 'start_queries', 0)
            end_queries = len(connection.queries)
            query_count = end_queries - start_queries

            # Исключаем чат из строгой проверки, т.к. он требует больше запросов
            if request.path.startswith('/chat/'):
                # Для чата увеличиваем порог до 20 запросов
                warning_threshold = 20
            else:
                warning_threshold = 10

            # Логируем, если запросов слишком много
            if query_count > warning_threshold:
                logger.warning(f"Много запросов к БД: {query_count} на {request.path} для пользователя {getattr(request.user, 'username', 'Anonymous')}")


            # Также логируем медленные запросы
            if hasattr(request, 'start_time'):
                import time
                duration = time.time() - request.start_time
                if duration > 1.0:  # Если запрос дольше 1 секунды
                    logger.warning(f"Медленный запрос: {request.path} took {duration:.2f}s with {query_count} queries")

        return response