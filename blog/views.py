from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import Http404
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import login
from .models import Post, PostReaction, ChatRoom, Message
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, FormView
from django.urls import reverse_lazy
from django.views import View
from .performance_utils import get_recent_messages_optimized, invalidate_posts_cache


User = get_user_model()

@login_required
def chat_room(request, room_name):
    # Получаем или создаем комнату с оптимизированным запросом
    room, created = ChatRoom.objects.get_or_create(name=room_name)

    # Используем кеширование для уменьшения количества запросов к БД
    from django.core.cache import cache
    cache_key = f'chat_latest_messages_{room_name}'

    # Попробуем получить последние сообщения из кеша
    messages_list = cache.get(cache_key)

    if messages_list is None:
        # Если в кеше нет данных, получаем из БД
        # Используем values() для получения только необходимых данных, чтобы избежать дополнительных запросов в шаблоне
        messages_raw = Message.objects.filter(room=room).select_related('user').values(
            'content', 'created_at', 'user__username'
        ).order_by('-created_at')[:50]  # Ограничиваем до 50 последних сообщений

        # Преобразуем в список словарей, чтобы избежать дополнительных запросов в шаблоне
        messages_list = []
        for msg in messages_raw:
            messages_list.append({
                'content': msg['content'],
                'created_at': msg['created_at'],
                'user_username': msg['user__username']
            })

        # Кешируем на 5 минут
        cache.set(cache_key, messages_list, 300)

    # Пагинация: 50 сообщений на страницу
    paginator = Paginator(messages_list, 50)
    page_number = request.GET.get('page')
    messages = paginator.get_page(page_number)

    # Отображаемое имя комнаты
    display_name = room_name
    if room_name == 'general':
        display_name = 'Светлый чат'

    return render(request, 'chat/room.html', {
        'room_name': room_name,
        'display_name': display_name,
        'messages': messages
    })


class HomeView(ListView):
    """Главная страница с постами"""
    model = Post
    template_name = 'home.html'
    context_object_name = 'page_obj'
    paginate_by = 5

    def get_queryset(self):
        """Возвращаем только опубликованные посты с оптимизированными связями"""
        return Post.objects.filter(is_published=True).select_related('author').only(
            'title', 'content', 'created_at', 'author__username'
        ).order_by('-created_at')

class LoginView(LoginView):
    """Представление для входа в системе"""
    form_class = CustomAuthenticationForm
    template_name = 'registration/login.html'
    
    def form_valid(self, form):
        """Установка срока действия сессии"""
        remember_me = form.cleaned_data.get('remember_me')
        if not remember_me:
            # Установка срока действия сессии 0, что означает до закрытия браузера
            self.request.session.set_expiry(0)
        return super().form_valid(form)
        

class RegisterView(FormView):
    """Представление для регистрации"""
    template_name = 'registration/register.html'
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('blog:home')
    
    def form_valid(self, form):
        """Обработка успешной регистрации"""
        user = form.save()
        login(self.request, user)
        messages.success(self.request, 'Регистрация прошла успешно!')
        return super().form_valid(form)

@login_required
def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    messages.info(request, 'Вы успешно вышли из системы.')
    return redirect('blog:home')

class PostCreateView(CreateView):
    """Создание нового поста"""
    model = Post
    fields = ['title', 'content', 'image', 'is_published']
    template_name = 'post_form.html'
    success_url = reverse_lazy('blog:home')
    
    def dispatch(self, request, *args, **kwargs):
        """Проверка прав доступа"""
        if not request.user.is_staff and not request.user.is_superuser:
            messages.error(request, 'У вас нет прав для создания постов.')
            return redirect('blog:home')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        """Установка автора поста"""
        form.instance.author = self.request.user
        messages.success(self.request, 'Пост успешно создан.')
        return super().form_valid(form)
        

class PostUpdateView(UpdateView):
    """Редактирование поста"""
    model = Post
    fields = ['title', 'content', 'image', 'is_published']
    template_name = 'post_form.html'
    success_url = reverse_lazy('blog:home')
    
    def dispatch(self, request, *args, **kwargs):
        """Проверка прав доступа"""
        if not request.user.is_staff and not request.user.is_superuser:
            messages.error(request, 'У вас нет прав для редактирования постов.')
            return redirect('blog:home')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        """Обработка успешного сохранения"""
        messages.success(self.request, 'Пост успешно обновлен.')
        return super().form_valid(form)
        

class PostDeleteView(DeleteView):
    """Удаление поста"""
    model = Post
    template_name = 'post_confirm_delete.html'
    success_url = reverse_lazy('blog:home')
    
    def dispatch(self, request, *args, **kwargs):
        """Проверка прав доступа"""
        if not request.user.is_staff and not request.user.is_superuser:
            messages.error(request, 'У вас нет прав для удаления постов.')
            return redirect('blog:home')
        return super().dispatch(request, *args, **kwargs)
    
    def delete(self, request, *args, **kwargs):
        """Обработка успешного удаления"""
        messages.success(request, 'Пост успешно удален.')
        return super().delete(request, *args, **kwargs)
        

class PostDetailView(DetailView):
    """Детальная страница поста"""
    model = Post
    template_name = 'post_detail.html'
    context_object_name = 'post'

    def dispatch(self, request, *args, **kwargs):
        """Проверка прав доступа и аутентификации"""
        if not request.user.is_authenticated:
            messages.info(request, 'Для просмотра полного содержания поста необходимо войти в систему или зарегистрироваться.')
            return redirect('blog:login')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """Оптимизированный запрос с предзагрузкой связанных данных"""
        return Post.objects.select_related('author')

    def get_context_data(self, **kwargs):
        """Добавляем данные о реакциях с оптимизированными запросами"""
        context = super().get_context_data(**kwargs)
        post = self.get_object()

        # Используем агрегацию для получения количества реакций (один запрос вместо двух)
        reaction_stats = PostReaction.objects.filter(post=post).values('reaction_type').annotate(
            count=Count('reaction_type')
        )

        # Преобразуем в удобный формат
        reaction_counts = {item['reaction_type']: item['count'] for item in reaction_stats}
        context['like_count'] = reaction_counts.get('like', 0)
        context['dislike_count'] = reaction_counts.get('dislike', 0)

        # Проверяем, поставил ли текущий пользователь реакцию (оптимизированный запрос)
        if self.request.user.is_authenticated:
            user_reaction = PostReaction.objects.filter(
                post=post,
                user=self.request.user
            ).select_related('user').first()
            context['user_reaction'] = user_reaction.reaction_type if user_reaction else None
        else:
            context['user_reaction'] = None

        return context
        

class ToggleReactionView(View):
    """Переключение реакции на пост"""
    http_method_names = ['post']
    
    def post(self, request, pk):
        """Обработка POST запроса для переключения реакции"""
        post = get_object_or_404(Post, pk=pk)
        
        if not request.user.is_authenticated:
            messages.error(request, 'Для установки реакции необходимо войти в систему.')
            return redirect('blog:login')
        
        reaction_type = request.POST.get('reaction_type')
        
        if reaction_type not in ['like', 'dislike']:
            messages.error(request, 'Недопустимый тип реакции.')
            return redirect('blog:post_detail', pk=pk)
        
        # Проверяем, существует ли уже реакция
        reaction, created = PostReaction.objects.get_or_create(
            user=request.user,
            post=post,
            defaults={'reaction_type': reaction_type}
        )
        
        if not created:
            if reaction.reaction_type == reaction_type:
                # Если реакция такая же, удаляем ее (отмена)
                reaction.delete()
                messages.success(request, 'Реакция удалена.')
            else:
                # Меняем тип реакции
                reaction.reaction_type = reaction_type
                reaction.save()
                messages.success(request, 'Реакция изменена.')
        else:
            messages.success(request, 'Реакция добавлена.')
        
        return redirect('blog:post_detail', pk=pk)