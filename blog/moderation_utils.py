import re
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from .models import ModerationSettings, UserMessageRate, Message, UserBan
from .lexicon import PROHIBITED_WORDS, TOXIC_INDICATORS


def check_user_ban(user, room=None):
    """
    Проверяет, заблокирован ли пользователь
    Возвращает: (is_banned, reason)
    """
    # Сначала проверим и очистим истекшие баны
    cleanup_expired_bans()

    # Проверяем активные баны для пользователя
    active_bans = UserBan.objects.filter(
        user=user,
        is_active=True
    )

    # Если указана комната, проверяем баны для этой комнаты или глобальные
    if room:
        active_bans = active_bans.filter(
            Q(room=room) | Q(room=None)  # Бан может быть как для конкретной комнаты, так и глобальный
        )

    for ban in active_bans:
        # Пользователь заблокирован
        if ban.is_permanent:
            return True, f"Пользователь заблокирован навсегда. Причина: {ban.reason}"
        elif ban.expires_at:
            return True, f"Пользователь заблокирован до {ban.expires_at.strftime('%d.%m.%Y %H:%M')}. Причина: {ban.reason}"
        else:
            return True, f"Пользователь заблокирован. Причина: {ban.reason}"

    # Пользователь не заблокирован
    return False, ""


def check_blocked_words(content, blocked_words_list):
    """
    Проверяет содержимое сообщения на наличие заблокированных слов
    """
    if not blocked_words_list:
        return False, ""

    content_lower = content.lower()
    for word in blocked_words_list:
        if word in content_lower:
            # Проверяем, является ли слово отдельным словом, а не частью другого слова
            pattern = r'\b' + re.escape(word) + r'\b'
            if re.search(pattern, content_lower):
                return True, "Будьте вежливы"

    return False, ""


def check_prohibited_words(content):
    """
    Проверяет содержимое сообщения на наличие заранее определенных запрещенных слов
    """
    content_lower = content.lower()
    for word in PROHIBITED_WORDS:
        # Проверяем, является ли слово отдельным словом, а не частью другого слова
        pattern = r'\b' + re.escape(word) + r'\b'
        if re.search(pattern, content_lower):
            return True, "Будьте вежливы"

    return False, ""


def check_message_rate(user, room, max_messages_per_minute):
    """
    Проверяет частоту сообщений пользователя
    """
    time_threshold = timezone.now() - timedelta(minutes=1)

    # Подсчитываем количество сообщений пользователя за последнюю минуту
    recent_messages_count = UserMessageRate.objects.filter(
        user=user,
        room=room,
        timestamp__gte=time_threshold
    ).count()

    if recent_messages_count >= max_messages_per_minute:
        return True, f"Превышено ограничение частоты сообщений: {max_messages_per_minute} в минуту"

    return False, ""


def check_toxicity(content):
    """
    Проверяет сообщение на токсичность
    Это упрощенная реализация - в реальном проекте можно интегрировать с ML-моделью
    """
    content_lower = content.lower()

    for indicator in TOXIC_INDICATORS:
        pattern = r'\b' + re.escape(indicator) + r'\b'
        if re.search(pattern, content_lower):
            return True, "Будьте вежливы"

    return False, ""


def moderate_message(user, room, content):
    """
    Основная функция автоматической модерации
    Возвращает: (is_blocked, reason)
    """
    try:
        # Сначала проверяем, не заблокирован ли пользователь
        is_banned, ban_reason = check_user_ban(user, room)
        if is_banned:
            return True, ban_reason

        # Получаем настройки модерации для комнаты
        try:
            settings = ModerationSettings.objects.get(room=room)
        except ModerationSettings.DoesNotExist:
            # Если настройки не найдены, создаем с настройками по умолчанию
            settings = ModerationSettings.objects.create(
                room=room,
                enabled=True,
                blocked_words="",
                max_messages_per_minute=10,
                enable_toxicity_filter=False
            )

        # Если модерация отключена, пропускаем проверки
        if not settings.enabled:
            return False, ""

        # Проверяем заблокированные слова
        is_blocked, reason = check_blocked_words(content, settings.blocked_words_list)
        if is_blocked:
            return True, reason

        # Проверяем заранее определенные запрещенные слова
        is_prohibited, prohibited_reason = check_prohibited_words(content)
        if is_prohibited:
            return True, "Будьте вежливы"

        # Проверяем частоту сообщений
        is_rate_limited, rate_reason = check_message_rate(user, room, settings.max_messages_per_minute)
        if is_rate_limited:
            return True, rate_reason

        # Проверяем токсичность (если включено)
        if settings.enable_toxicity_filter:
            is_toxic, toxic_reason = check_toxicity(content)
            if is_toxic:
                return True, toxic_reason

        # Все проверки пройдены, сообщение разрешено
        return False, ""

    except Exception as e:
        # В случае ошибки модерации, лучше разрешить сообщение, чем блокировать
        # Но логируем ошибку для анализа
        print(f"Ошибка при модерации сообщения: {e}")
        return False, ""


def record_user_message(user, room):
    """
    Записывает факт отправки сообщения пользователем для отслеживания частоты
    """
    UserMessageRate.objects.create(user=user, room=room)


def cleanup_old_message_rates():
    """
    Очищает старые записи о частоте сообщений (старше 2 минут)
    """
    time_threshold = timezone.now() - timedelta(minutes=2)
    UserMessageRate.objects.filter(timestamp__lt=time_threshold).delete()


def cleanup_expired_bans():
    """
    Очищает истекшие баны (деактивирует их)
    """
    expired_bans = UserBan.objects.filter(
        is_active=True,
        is_permanent=False,
        expires_at__isnull=False,
        expires_at__lt=timezone.now()
    )

    for ban in expired_bans:
        ban.deactivate_if_expired()