from django.urls import re_path
from ..consumers.optimized_chat_consumer import OptimizedChatConsumer

# WebSocket маршруты для чата
websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<room_name>[^/]+)/$', OptimizedChatConsumer.as_asgi()),
]