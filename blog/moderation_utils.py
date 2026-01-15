import re
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from .models import ModerationSettings, UserMessageRate, Message, UserBan
from .lexicon import (
    PROHIBITED_WORDS,
    TOXIC_INDICATORS,
    SPAM_INDICATORS,
    MODERATION_SETTINGS,
    MODERATION_LEVELS,
    normalize_text,  # ✅ ИМПОРТИРУЕМ ФУНКЦИЮ НОРМАЛИЗАЦИИ
    contains_prohibited_word  # ✅ ИМПОРТИРУЕМ УМНУЮ ПРОВЕРКУ
)

def check_user_ban(user, room=None):
    """
    Проверяет, заблокирован ли пользователь
    Возвращает: (is_banned, reason)
    """
    cleanup_expired_bans()

    active_bans = UserBan.objects.filter(
        user=user,
        is_active=True
    )

    if room:
        active_bans = active_bans.filter(
            Q(room=room) | Q(room=None)
        )

    for ban in active_bans:
        if ban.is_permanent:
            return True, f"Пользователь заблокирован навсегда. Причина: {ban.reason}"
        elif ban.expires_at:
            return True, f"Пользователь заблокирован до {ban.expires_at.strftime('%d.%m.%Y %H:%M')}. Причина: {ban.reason}"
        else:
            return True, f"Пользователь заблокирован. Причина: {ban.reason}"

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
            pattern = r'\b' + re.escape(word) + r'\b'
            if re.search(pattern, content_lower):
                return True, "Будьте вежливы"

    return False, ""

def check_prohibited_words(content):
    """
    ✅ УЛУЧШЕНО: Проверяет содержимое сообщения на СТРОГО ЗАПРЕЩЕННЫЕ слова
    Использует PROHIBITED_WORDS из lexicon.py (~155 слов)
    Применяет нормализацию текста для обхода обфускации
    """
    # Проверяем каждое запрещенное слово
    for word in PROHIBITED_WORDS:
        if contains_prohibited_word(content, word):
            return True, "Сообщение содержит запрещенные слова"

    return False, ""

def check_toxicity(content):
    """
    ✅ УЛУЧШЕНО: Проверяет сообщение на токсичность
    Использует TOXIC_INDICATORS из lexicon.py (~150 слов)
    Блокирует, если найдено 2+ токсичных слова
    """
    toxic_count = 0

    for indicator in TOXIC_INDICATORS:
        if contains_prohibited_word(content, indicator):
            toxic_count += 1

            if toxic_count >= 2:
                return True, "Токсичное сообщение (множественные оскорбления)"

    return False, ""

def check_spam(content):
    """
    ✅ НОВОЕ: Проверяет сообщение на спам-индикаторы
    Использует SPAM_INDICATORS из lexicon.py (~95 слов)
    """
    content_lower = content.lower()

    for spam_word in SPAM_INDICATORS:
        if spam_word in content_lower:
            return True, f"Обнаружен спам"

    return False, ""

def check_suspicious_patterns(content):
    """
    ✅ УЛУЧШЕНО: Проверяет сообщение на подозрительные паттерны
    - Повторяющиеся символы (ааааааа)
    - Много заглавных букв (КРИЧИТ)
    - URL-адреса
    """
    # Проверка повторяющихся символов
    if re.search(r'(.)\1{4,}', content):
        return True, "Обнаружен спам (повторяющиеся символы)"

    # Проверка заглавных букв
    if len(content) > 10:
        caps_ratio = sum(1 for c in content if c.isupper()) / len(content)
        if caps_ratio > MODERATION_SETTINGS['max_caps_ratio']:
            return True, "Слишком много заглавных букв"

    # Проверка на URL
    if re.search(r'(http|https|ftp)://[^\s]+', content):
        return True, "Запрещены ссылки"

    if re.search(r'www\.[^\s]+', content):
        return True, "Запрещены ссылки"

    # Проверка на домены
    if re.search(r'\b[a-zA-Z0-9.-]+\.(com|ru|net|org|info|biz)\b', content):
        return True, "Запрещены ссылки на сайты"

    return False, ""

def check_message_rate(user, room, max_messages_per_minute):
    """
    Проверяет частоту сообщений пользователя
    """
    time_threshold = timezone.now() - timedelta(minutes=1)

    recent_messages_count = UserMessageRate.objects.filter(
        user=user,
        room=room,
        timestamp__gte=time_threshold
    ).count()

    if recent_messages_count >= max_messages_per_minute:
        return True, f"Превышено ограничение частоты сообщений: {max_messages_per_minute} в минуту"

    return False, ""

def check_message_length(content):
    """
    ✅ НОВОЕ: Проверяет длину сообщения
    Использует MODERATION_SETTINGS из lexicon.py
    """
    length = len(content)

    if length < MODERATION_SETTINGS['min_message_length']:
        return True, "Сообщение слишком короткое"

    if length > MODERATION_SETTINGS['max_message_length']:
        return True, f"Сообщение слишком длинное (макс. {MODERATION_SETTINGS['max_message_length']} символов)"

    return False, ""

def moderate_message(user, room, content, moderation_level='moderate'):
    """
    ✅ ОБНОВЛЕНО: Основная функция автоматической модерации

    Параметры:
    - user: пользователь
    - room: комната
    - content: содержимое сообщения
    - moderation_level: уровень строгости ('strict', 'moderate', 'relaxed')

    Возвращает: (is_blocked, reason)
    """
    try:
        # 1. Проверяем, не заблокирован ли пользователь
        is_banned, ban_reason = check_user_ban(user, room)
        if is_banned:
            return True, ban_reason

        # 2. Получаем настройки модерации для комнаты
        try:
            settings = ModerationSettings.objects.get(room=room)
        except ModerationSettings.DoesNotExist:
            settings = ModerationSettings.objects.create(
                room=room,
                enabled=True,
                blocked_words="",
                max_messages_per_minute=10,
                enable_toxicity_filter=True
            )

        if not settings.enabled:
            return False, ""

        # 3. Получаем уровень модерации
        level_settings = MODERATION_LEVELS.get(moderation_level, MODERATION_LEVELS['moderate'])

        # 4. Проверяем длину сообщения
        is_invalid_length, length_reason = check_message_length(content)
        if is_invalid_length:
            return True, length_reason

        # 5. ✅ ГЛАВНАЯ ПРОВЕРКА: СТРОГО ЗАПРЕЩЕННЫЕ слова (всегда проверяем)
        if level_settings['prohibited_words']:
            is_prohibited, prohibited_reason = check_prohibited_words(content)
            if is_prohibited:
                return True, "Сообщение содержит запрещенные слова"

        # 6. Проверяем пользовательские заблокированные слова
        is_blocked, reason = check_blocked_words(content, settings.blocked_words_list)
        if is_blocked:
            return True, reason

        # 7. Проверяем токсичность (если включено)
        if level_settings['toxic_indicators'] and settings.enable_toxicity_filter:
            is_toxic, toxic_reason = check_toxicity(content)
            if is_toxic:
                return True, toxic_reason

        # 8. Проверяем спам-индикаторы
        if level_settings['spam_indicators']:
            is_spam, spam_reason = check_spam(content)
            if is_spam:
                return True, spam_reason

        # 9. Проверяем подозрительные паттерны
        if level_settings['suspicious_patterns']:
            is_suspicious, suspicious_reason = check_suspicious_patterns(content)
            if is_suspicious:
                return True, suspicious_reason

        # 10. Проверяем частоту сообщений
        is_rate_limited, rate_reason = check_message_rate(user, room, settings.max_messages_per_minute)
        if is_rate_limited:
            return True, rate_reason

        # ✅ Все проверки пройдены
        return False, ""

    except Exception as e:
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

# ===================================================================
# ✅ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ===================================================================

def get_moderation_stats(room):
    """
    ✅ НОВОЕ: Получает статистику модерации для комнаты
    """
    time_threshold = timezone.now() - timedelta(days=7)

    total_messages = Message.objects.filter(room=room, created_at__gte=time_threshold).count()
    blocked_messages = Message.objects.filter(room=room, is_blocked=True, created_at__gte=time_threshold).count()

    return {
        'total_messages': total_messages,
        'blocked_messages': blocked_messages,
        'block_rate': (blocked_messages / total_messages * 100) if total_messages > 0 else 0
    }

def test_moderation(content, moderation_level='moderate'):
    """
    ✅ НОВОЕ: Тестирует модерацию сообщения без сохранения в БД
    """
    results = {
        'prohibited_words': check_prohibited_words(content),
        'toxicity': check_toxicity(content),
        'spam': check_spam(content),
        'suspicious_patterns': check_suspicious_patterns(content),
        'length': check_message_length(content),
        'normalized': normalize_text(content) if content else '',
        'normalized_length': len(normalize_text(content)) if content else ''
    }

    return results
