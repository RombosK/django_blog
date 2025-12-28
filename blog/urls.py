from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView, RedirectView
from . import views

app_name = 'blog'

urlpatterns = [
    path('posts/', views.HomeView.as_view(), name='post_list'),
    path('accounts/profile/', RedirectView.as_view(url='/', permanent=False)),
    path('', views.HomeView.as_view(), name='home'),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # URL для управления постами
    path('post/create/', views.PostCreateView.as_view(), name='post_create'),
    path('post/<int:pk>/edit/', views.PostUpdateView.as_view(), name='post_edit'),
    path('post/<int:pk>/delete/', views.PostDeleteView.as_view(), name='post_delete'),
    path('post/<int:pk>/', views.PostDetailView.as_view(), name='post_detail'),
    path('post/<int:pk>/reaction/', views.ToggleReactionView.as_view(), name='toggle_reaction'),
    
    # URL для чат-рума
    path('chat/<str:room_name>/', views.chat_room, name='chat_room'),
]