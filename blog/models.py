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

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['-created_at']  # Изменяем порядок на обратный для улучшения производительности
        # Добавляем составной индекс для ускорения запросов
        indexes = [
            models.Index(fields=['room', '-created_at']),
            models.Index(fields=['room', 'user', '-created_at']),
        ]
        # Ограничиваем количество сообщений, хранящихся в БД
        # (это можно реализовать через сигналы или периодическую очистку)

    def __str__(self):
        return f'{self.user.email}: {self.content[:50]}'