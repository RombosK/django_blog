"""
Тестирование системы автоматической модерации
"""
from django.test import TestCase
from blog.models import CustomUser, ChatRoom, ModerationSettings
from blog.moderation_utils import moderate_message


class ModerationTestCase(TestCase):
    def setUp(self):
        # Создаем тестового пользователя
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Создаем тестовую комнату
        self.room = ChatRoom.objects.create(
            name='test_room',
            topic='Тестовая комната'
        )
        
        # Создаем настройки модерации
        self.moderation_settings = ModerationSettings.objects.create(
            room=self.room,
            enabled=True,
            blocked_words="дурак\nидиот",
            max_messages_per_minute=10,
            enable_toxicity_filter=True
        )

    def test_clean_message(self):
        """Тест: чистое сообщение должно пройти модерацию"""
        result = moderate_message(self.user, self.room, "Это нормальное сообщение")
        self.assertEqual(result, (False, ""))

    def test_blocked_word(self):
        """Тест: сообщение с заблокированным словом должно быть отклонено"""
        result = moderate_message(self.user, self.room, "Ты дурак")
        self.assertEqual(result, (True, "Содержит запрещенное слово: дурак"))

    def test_multiple_blocked_words(self):
        """Тест: проверка нескольких заблокированных слов"""
        result = moderate_message(self.user, self.room, "Ты идиот и дурак")
        # Проверяем, что сообщение заблокировано (первое найденное слово)
        self.assertTrue(result[0])
        self.assertIn("запрещенное слово", result[1])

    def test_blocked_message(self):
        """Тест: сообщение с запрещенным словом должно быть отклонено"""
        result = moderate_message(self.user, self.room, "Ты отвратительный человек")
        self.assertTrue(result[0])
        self.assertIn("запрещённое слово", result[1])

    def test_prohibited_word(self):
        """Тест: запрещенное слово 'чёрт' должно быть отклонено"""
        result = moderate_message(self.user, self.room, "Чёрт возьми!")
        self.assertTrue(result[0])
        self.assertIn("запрещённое слово", result[1])

    def test_disabled_moderation(self):
        """Тест: при отключенной модерации все сообщения должны проходить"""
        self.moderation_settings.enabled = False
        self.moderation_settings.save()
        
        result = moderate_message(self.user, self.room, "Ты дурак")
        self.assertEqual(result, (False, ""))


if __name__ == '__main__':
    import os
    import django
    from django.conf import settings
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blog_project.settings')
    django.setup()
    
    import unittest
    unittest.main()