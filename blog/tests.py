from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import CustomUser

class UserAuthenticationTestCase(TestCase):
    
    def setUp(self):
        self.client = Client()
        self.register_url = '/register/'
        self.login_url = '/accounts/login/'
        self.home_url = '/'
        self.home_url = '/'
        self.logout_url = '/logout/'
        self.home_url = '/'
        self.profile_url = '/accounts/profile/'
        self.password_reset_url = '/accounts/password_reset/'
        self.password_reset_done_url = '/accounts/password_reset/done/'
        self.password_reset_confirm_url = '/accounts/reset/<uidb64>/<token>/'
        self.password_reset_complete_url = '/accounts/reset/done/'
        self.password_reset_done_url = '/accounts/password_reset/done/'
        self.password_reset_confirm_url = '/accounts/reset/<uidb64>/<token>/'
        self.password_reset_complete_url = '/accounts/reset/done/'
        
        # Создаем тестового пользователя
        self.user_data = {
            'email': 'testuser@example.com',
            'username': 'testuser',
            'password1': 'testpass123',
            'password2': 'testpass123'
        }
        
        self.user = CustomUser.objects.create_user(
            email='existing@example.com',
            username='existing',
            password='existingpass123'
        )
    
    def test_register_page_status_code(self):
        """Тест: страница регистрации доступна"""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/register.html')
    
    def test_register_user_success(self):
        """Тест: успешная регистрация нового пользователя"""
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, 302)  # Редирект после успешной регистрации
        self.assertRedirects(response, self.home_url)
        
        # Проверяем, что пользователь создан
        self.assertTrue(CustomUser.objects.filter(email=self.user_data['email']).exists())
        
        # Проверяем, что пользователь залогинен
        response = self.client.get(self.home_url)
        self.assertTrue(response.context['user'].is_authenticated)
    
    def test_register_user_password_mismatch(self):
        """Тест: ошибка при несовпадении паролей"""
        data = self.user_data.copy()
        data['password2'] = 'differentpass'
        
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'password2', 'Пароли не совпадают.')
    
    def test_register_user_duplicate_email(self):
        """Тест: ошибка при регистрации с существующим email"""
        data = self.user_data.copy()
        data['email'] = 'existing@example.com'
        data['username'] = 'newuser'
        
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'email', 'Пользователь с таким email уже существует.')
    
    def test_login_page_status_code(self):
        """Тест: страница входа доступна"""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login.html')
    
    def test_login_success(self):
        """Тест: успешный вход в систему"""
        login_data = {
            'username': 'existing@example.com',
            'password': 'existingpass123'
        }
        
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.home_url)
        
        # Проверяем, что пользователь залогинен
        response = self.client.get(self.home_url)
        self.assertTrue(response.context['user'].is_authenticated)
    
    def test_login_invalid_credentials(self):
        """Тест: ошибка при неверных учетных данных"""
        login_data = {
            'username': 'existing@example.com',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Пожалуйста, введите правильные email и пароль.')
    
    def test_logout_functionality(self):
        """Тест: функциональность выхода из системы"""
        # Сначала логинимся
        self.client.login(email='existing@example.com', password='existingpass123')
        
        # Проверяем, что пользователь залогинен
        response = self.client.get(self.home_url)
        self.assertTrue(response.context['user'].is_authenticated)
        
        # Выходим из системы
        response = self.client.get(self.logout_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.home_url)
        
        # Проверяем, что пользователь разлогинен
        response = self.client.get(self.home_url)
        self.assertFalse(response.context['user'].is_authenticated)
    
    def test_home_page_requires_no_login(self):
        """Тест: главная страница доступна без аутентификации"""
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'blog/home.html')
    
    def test_password_reset_functionality(self):
        """Тест: функциональность восстановления пароля"""
        
        # Проверка доступности страницы восстановления пароля
        response = self.client.get(self.password_reset_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/password_reset_form.html')
        
        # Проверка отправки формы восстановления пароля
        reset_data = {'email': 'existing@example.com'}
        response = self.client.post(self.password_reset_url, reset_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.password_reset_done_url)
    
    def test_unauthenticated_user_redirect(self):
        """Тест: неаутентифицированный пользователь может просматривать сайт"""
        # Создаем несколько постов для тестирования
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что нет перенаправления на страницу входа
        self.assertNotEqual(response.status_code, 302)