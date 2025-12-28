from locust import HttpUser, task, between
import random
import string


class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Выполняется при запуске каждого пользователя"""
        self.login()

    def generate_random_string(self, length=8):
        """Генерация случайной строки для тестовых данных"""
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(length))

    def login(self):
        """Попытка входа в систему"""
        # Попробуем войти с тестовыми учетными данными
        username = "testuser"
        password = "testpassword123"

        response = self.client.post("/accounts/login/", {
            "username": username,
            "password": password,
            "remember_me": "on"
        }, catch_response=True)

        if response.status_code != 200:
            # Если не получилось войти, попробуем зарегистрироваться
            self.register()

    def register(self):
        """Регистрация нового пользователя"""
        username = f"user_{self.generate_random_string()}"
        email = f"{username}@example.com"
        password = "testpassword123"

        self.client.post("/accounts/register/", {
            "username": username,
            "email": email,
            "password1": password,
            "password2": password,
            "agree_to_terms": "on"
        }, catch_response=True)

    @task(5)
    def view_homepage(self):
        """Просмотр главной страницы"""
        self.client.get("/")

    @task(3)
    def view_posts(self):
        """Просмотр постов"""
        self.client.get("/posts/")

    @task(2)
    def view_post_detail(self):
        """Просмотр деталей поста"""
        # Попробуем разные ID постов
        post_id = random.randint(1, 50)
        with self.client.get(f"/post/{post_id}/", catch_response=True) as response:
            if response.status_code == 404:
                # Если пост не найден, используем первый
                self.client.get("/post/1/", catch_response=True)

    @task(1)
    def create_post(self):
        """Создание нового поста (только для администраторов)"""
        title = f"Тестовый пост {self.generate_random_string()}"
        content = f"Это тестовый пост, созданный автоматически {self.generate_random_string(50)}"

        with self.client.post("/post/create/", {
            "title": title,
            "content": content,
            "is_published": True
        }, catch_response=True) as response:
            if response.status_code in [403, 404]:
                # Если нет прав или URL не найден, просто пропускаем
                response.success()

    @task(4)
    def view_chat(self):
        """Просмотр чата"""
        self.client.get("/chat/general/")

    @task(2)
    def websocket_chat(self):
        """Тестирование WebSocket чата (имитация)"""
        # Для тестирования WebSocket используем GET запрос к странице чата
        # так как Locust не поддерживает WebSocket напрямую
        self.client.get("/chat/general/", catch_response=True)