from django_comments.moderation import CommentModerator, moderator
from .models import Post
from .moderation_utils import moderate_message


class PostCommentModerator(CommentModerator):
    """
    Модератор комментариев к постам
    """
    email_notification = True
    auto_close_field = "created_at"
    close_after = 30  # закрывать комменты через 30 дней

    def moderate(self, comment, content_object, request):
        """
        Модерация комментария
        Возвращает True, если комментарий нужно скрыть (is_public=False)
        """
        # Проверяем комментарий с помощью нашей системы модерации
        # Используем анонимного пользователя, если комментарий не от зарегистрированного пользователя
        user = comment.user if comment.user_id else None
        is_blocked, reason = moderate_message(
            user=user,
            room=None,  # Для комментариев к постам комнаты нет
            content=comment.comment
        )
        
        if is_blocked:
            # Логируем причину модерации
            print(f"Comment moderated: {reason}")
            # Возвращаем True, чтобы скрыть комментарий (is_public=False)
            return True
        
        # Комментарий прошел модерацию, разрешаем публикацию
        return False


# Регистрируем модератор для модели Post
moderator.register(Post, PostCommentModerator)