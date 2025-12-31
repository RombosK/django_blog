import os
import random
from django.core.management.base import BaseCommand
from django.conf import settings
from blog.models import Post, CustomUser
from PIL import Image
from io import BytesIO
from django.core.files import File


class Command(BaseCommand):
    help = 'Создает 10 тестовых постов с рандомными изображениями'

    def handle(self, *args, **options):
        # Получаем случайного пользователя или создаем тестового
        user = CustomUser.objects.first()
        if not user:
            user = CustomUser.objects.create_user(
                username='testuser',
                email='test@example.com',
                password='testpass123'
            )

        # Тексты для генерации постов
        titles = [
            'Новый пост о программировании',
            'Как я изучал Python',
            'Django для начинающих',
            'Оптимизация производительности',
            'Секреты веб-разработки',
            'Искусственный интеллект',
            'Машинное обучение',
            'Разработка чат-приложения',
            'Оптимизация чата с 39 до 5 запросов',
            'Работа с WebSocket в Django'
        ]

        contents = [
            'Это тестовый пост с интересным содержанием. Здесь описываются различные аспекты разработки и оптимизации.',
            'В этом посте мы рассмотрим важные аспекты веб-разработки и лучшие практики.',
            'Интересные наблюдения о современных технологиях и их применении в реальных проектах.',
            'Подробный разбор проблемы и способы её решения с практическими примерами.',
            'Анализ производительности и пути оптимизации веб-приложений на Django.',
            'Обзор современных инструментов и библиотек для улучшения производительности.',
            'Практические советы по оптимизации запросов к базе данных и кешированию.',
            'Разбор архитектурных решений для масштабируемых веб-приложений.',
            'Сравнение различных подходов к реализации чат-функционала в Django.',
            'Оптимизация чата: уменьшение количества запросов к БД с 39 до 3-5.'
        ]

        # Создаем 10 тестовых постов
        for i in range(10):
            title = f"{random.choice(titles)} #{i+1}"
            content = f"{random.choice(contents)}\n\n{i+1}. Первый пункт.\n{i+1}. Второй пункт.\n{i+1}. Третий пункт.\n\nЗаключение: этот пост был создан автоматически для тестирования производительности."

            # Создаем простое изображение программно
            try:
                # Создаем простое цветное изображение
                img = Image.new('RGB', (600, 400), color=(
                    random.randint(0, 255),
                    random.randint(0, 255),
                    random.randint(0, 255)
                ))

                # Сохраняем изображение в буфер
                img_io = BytesIO()
                img.save(img_io, format='JPEG')
                img_io.seek(0)

                # Создаем пост
                post = Post.objects.create(
                    title=title,
                    content=content,
                    author=user,
                    is_published=True
                )

                # Сохраняем изображение
                post.image.save(f'test_image_{i+1}.jpg', File(img_io), save=True)

                self.stdout.write(
                    self.style.SUCCESS(f'Создан пост "{title}" с изображением')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Ошибка при создании поста "{title}": {str(e)}')
                )

        self.stdout.write(
            self.style.SUCCESS('Создание тестовых постов завершено!')
        )