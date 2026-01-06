from django.db import models
from django.contrib.auth.models import AbstractUser
from django.urls import reverse
from django.utils import timezone

class CustomUser(AbstractUser):
    email = models.EmailField('email address', unique=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.email


class Post(models.Model):
    title = models.CharField('Заголовок', max_length=200, db_index=True)
    content = models.TextField('Содержание')
    image = models.ImageField('Изображение', upload_to='post_images/', blank=True, null=True)
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name='Автор', db_index=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    is_published = models.BooleanField('Опубликовано', default=True, db_index=True)

    class Meta:
        verbose_name = 'Пост'
        verbose_name_plural = 'Посты'
        ordering = ['-created_at']
        # Добавляем индекс для ускорения фильтрации
        indexes = [
            models.Index(fields=['is_published', '-created_at']),
            models.Index(fields=['author', '-created_at']),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('blog:post_detail', kwargs={'pk': self.pk})

    def get_preview(self):
        # Возвращаем первые 300 символов или до первого абзаца
        if self.content:
            if len(self.content) <= 300:
                return self.content
            else:
                # Попробуем найти конец абзаца
                end = self.content.find('.', 200)
                if end == -1 or end > 300:
                    end = 300
                return self.content[:end+1]
        return ''

    @property
    def is_premium_content(self):
        return True  # Всегда премиум-контент для демонстрации функционала подписки

    @property
    def slug(self):
        # Создаем slug из заголовка
        import re
        # Заменяем все не-буквы и не-цифры на дефисы
        slug = re.sub(r'[^\w\s-]', '', self.title).strip().lower()
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug or 'post'

class PostReaction(models.Model):
    REACTION_CHOICES = [
        ('like', '👍'),
        ('dislike', '👎'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name='Пользователь', db_index=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, verbose_name='Пост', db_index=True)
    reaction_type = models.CharField('Тип реакции', max_length=10, choices=REACTION_CHOICES)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True, db_index=True)
    
    class Meta:
        verbose_name = 'Реакция на пост'
        verbose_name_plural = 'Реакции на посты'
        unique_together = ['user', 'post']  # Один пользователь может поставить только одну реакцию на пост
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.user.email} - {self.get_reaction_type_display()} - {self.post.title}'

class ChatRoom(models.Model):
    name = models.CharField(max_length=100, unique=True)
    topic = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_private = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'Чат-комната'
        verbose_name_plural = 'Чат-комнаты'
        
    def __str__(self):
        return self.name

class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages', db_index=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, db_index=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    is_moderated = models.BooleanField(default=False)  # Сообщение прошло модерацию
    is_blocked = models.BooleanField(default=False)    # Сообщение заблокировано автоматической модерацией
    moderation_reason = models.CharField(max_length=200, blank=True, null=True)  # Причина модерации

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['-created_at']  # Изменяем порядок на обратный для улучшения производительности
        # Добавляем составной индекс для ускорения запросов
        indexes = [
            models.Index(fields=['room', '-created_at']),
            models.Index(fields=['room', 'user', '-created_at']),
            models.Index(fields=['is_moderated', '-created_at']),
            models.Index(fields=['is_blocked', '-created_at']),
        ]
        # Ограничиваем количество сообщений, хранящихся в БД
        # (это можно реализовать через сигналы или периодическую очистку)

    def __str__(self):
        return f'{self.user.email}: {self.content[:50]}'


class ModerationSettings(models.Model):
    """Настройки автоматической модерации"""
    room = models.OneToOneField(ChatRoom, on_delete=models.CASCADE, related_name='moderation_settings')
    enabled = models.BooleanField(default=True)  # Включена ли автоматическая модерация
    blocked_words = models.TextField(blank=True, help_text="Слова для блокировки, каждое с новой строки")
    max_messages_per_minute = models.PositiveIntegerField(default=10, help_text="Максимальное количество сообщений в минуту от одного пользователя")
    enable_toxicity_filter = models.BooleanField(default=False, help_text="Включить фильтр токсичности")

    class Meta:
        verbose_name = 'Настройка модерации'
        verbose_name_plural = 'Настройки модерации'

    def __str__(self):
        return f'Модерация для {self.room.name}'

    @property
    def blocked_words_list(self):
        """Возвращает список заблокированных слов"""
        if self.blocked_words:
            return [word.strip().lower() for word in self.blocked_words.split('\n') if word.strip()]
        return []


class UserMessageRate(models.Model):
    """Отслеживание частоты сообщений пользователей"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Частота сообщений пользователя'
        verbose_name_plural = 'Частоты сообщений пользователей'
        indexes = [
            models.Index(fields=['user', 'room', '-timestamp']),
        ]


class UserBan(models.Model):
    """Модель для отслеживания банов пользователей"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='bans', verbose_name="Пользователь")
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='bans', null=True, blank=True, verbose_name="Комната")
    moderator = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='issued_bans', verbose_name="Модератор")
    reason = models.CharField(max_length=500, help_text="Причина бана", verbose_name="Причина")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Время окончания бана (если null - бан постоянный)", verbose_name="Окончание бана")
    is_permanent = models.BooleanField(default=False, verbose_name="Постоянный бан")
    is_active = models.BooleanField(default=True, verbose_name="Активен")  # Активен ли бан в данный момент

    class Meta:
        verbose_name = 'Бан пользователя'
        verbose_name_plural = 'Баны пользователей'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        if self.is_permanent:
            return f"Постоянный бан {self.user.username} - {self.reason}"
        elif self.expires_at:
            return f"Бан {self.user.username} до {self.expires_at.strftime('%d.%m.%Y %H:%M')} - {self.reason}"
        else:
            return f"Бан {self.user.username} - {self.reason}"

    @property
    def is_expired(self):
        """Проверяет, истек ли срок бана"""
        if self.is_permanent or not self.expires_at or not self.is_active:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at

    def deactivate_if_expired(self):
        """Деактивирует бан, если срок истек"""
        if self.is_expired and self.is_active:
            self.is_active = False
            self.save()
            return True
        return False