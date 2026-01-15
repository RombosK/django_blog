from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView

# ✅ Импортируем все view напрямую - БЕЗ from . import views!
from .views import (
    HomeView,
    LoginView,
    RegisterView,
    logout_view,
    CustomPasswordResetView,
    PostCreateView,
    PostUpdateView,
    PostDeleteView,
    PostDetailView,
    ToggleReactionView,
    chat_room,
)

app_name = 'blog'

urlpatterns = [
    # Главная и посты
    path('posts/', HomeView.as_view(), name='post_list'),
    path('', HomeView.as_view(), name='home'),

    # Редирект профиля
    path('accounts/profile/', RedirectView.as_view(url='/', permanent=False)),

    # Аутентификация
    path('accounts/login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', logout_view, name='logout'),

    # PASSWORD RESET
    path('accounts/password_reset/',
         CustomPasswordResetView.as_view(),
         name='password_reset'),

    path('accounts/password_reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='registration/password_reset_done.html'
         ),
         name='password_reset_done'),

    path('accounts/reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='registration/password_reset_confirm.html',
             success_url='/accounts/password_reset/complete/'  # ✅ Явный URL!
         ),
         name='password_reset_confirm'),

    path('accounts/password_reset/complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='registration/password_reset_complete.html'
         ),
         name='password_reset_complete'),

    # Посты
    path('post/create/', PostCreateView.as_view(), name='post_create'),
    path('post/<int:pk>/edit/', PostUpdateView.as_view(), name='post_edit'),
    path('post/<int:pk>/delete/', PostDeleteView.as_view(), name='post_delete'),
    path('post/<int:pk>/', PostDetailView.as_view(), name='post_detail'),
    path('post/<int:pk>/reaction/', ToggleReactionView.as_view(), name='toggle_reaction'),
    path('toggle-reaction/<int:pk>/', ToggleReactionView.as_view(), name='toggle_reaction_ajax'),

    # Чат
    path('chat/<str:room_name>/', chat_room, name='chat_room'),
]
