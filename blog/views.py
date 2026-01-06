from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count, Prefetch
from django.http import Http404
from django.contrib.auth.views import LoginView as DjangoLoginView, LogoutView
from django.contrib.auth import login
from django.core.cache import cache
from .models import Post, PostReaction, ChatRoom, Message
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, FormView
from django.urls import reverse_lazy
from django.views import View
from .performance_utils import get_recent_messages_optimized, invalidate_posts_cache


User = get_user_model()


@login_required
def chat_room(request, room_name):
    """Чат комната с кешированием и оптимизацией запросов"""
    # Получаем или создаем комнату
    room, created = ChatRoom.objects.get_or_create(name=room_name)

    search_query = request.GET.get('q')
    cache_key = f'chat_messages_{room_name}'

    # ✅ КЕШИРОВАНИЕ: используем кеш только без поиска
    if not search_query:
        messages_qs = cache.get(cache_key)

        if messages_qs is None:
            # Кеша нет - запрашиваем БД с оптимизацией
            messages_qs = Message.objects.filter(
                room=room,
                is_blocked=False
            ).select_related('user').order_by('-created_at')

            # Сохраняем в кеш на 5 минут
            cache.set(cache_key, list(messages_qs), 300)
            messages_qs = list(messages_qs)
    else:
        # Поиск - всегда из БД
        messages_qs = Message.objects.filter(
            room=room,
            is_blocked=False
        ).select_related('user').filter(
            Q(content__icontains=search_query) |
            Q(user__username__icontains=search_query)
        ).order_by('-created_at')

    # Пагинация: 50 сообщений на страницу
    paginator = Paginator(messages_qs, 50)
    page_number = request.GET.get('page')
    messages = paginator.get_page(page_number)

    # Отображаемое имя комнаты
    display_name = 'Светлый чат' if room_name == 'general' else room_name

    return render(request, 'chat/room.html', {
        'room_name': room_name,
        'display_name': display_name,
        'messages': messages,
        'search_query': search_query or ''
    })


class HomeView(ListView):
    """Главная страница с постами, оптимизацией и кешированием"""
    model = Post
    template_name = 'home.html'
    context_object_name = 'posts'
    paginate_by = 5

    def get_queryset(self):
        """✅ ОПТИМИЗАЦИЯ: select_related для author (1 запрос вместо N+1)"""
        queryset = Post.objects.filter(
            is_published=True
        ).select_related('author').order_by('-created_at')

        # Добавляем поиск
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(content__icontains=search_query)
            )

        return queryset

    def get_context_data(self, **kwargs):
        """✅ КЕШИРОВАНИЕ: кешируем общее количество постов"""
        context = super().get_context_data(**kwargs)

        # ✅ Кешируем общее количество постов на 10 минут
        total_posts = cache.get('total_published_posts')
        if total_posts is None:
            total_posts = Post.objects.filter(is_published=True).count()
            cache.set('total_published_posts', total_posts, 600)

        context['total_posts'] = total_posts
        context['search_query'] = self.request.GET.get('q', '')

        return context


class LoginView(DjangoLoginView):
    """Представление для входа в системе"""
    form_class = CustomAuthenticationForm
    template_name = 'registration/login.html'

    def form_valid(self, form):
        """Установка срока действия сессии"""
        remember_me = form.cleaned_data.get('remember_me')
        if not remember_me:
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
    """Выход из системы"""
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
        """Установка автора поста и сброс кеша"""
        form.instance.author = self.request.user
        response = super().form_valid(form)

        # ✅ Сбрасываем кеш после создания поста
        cache.delete('total_published_posts')

        messages.success(self.request, 'Пост успешно создан.')
        return response


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
        """Обработка успешного сохранения и сброс кеша"""
        response = super().form_valid(form)

        # ✅ Сбрасываем кеш поста
        cache.delete(f'post_{self.object.pk}')
        cache.delete(f'post_reactions_{self.object.pk}')

        messages.success(self.request, 'Пост успешно обновлен.')
        return response


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
        """Обработка успешного удаления и сброс кеша"""
        post_id = self.get_object().pk
        response = super().delete(request, *args, **kwargs)

        # ✅ Сбрасываем кеш
        cache.delete('total_published_posts')
        cache.delete(f'post_{post_id}')
        cache.delete(f'post_reactions_{post_id}')

        messages.success(request, 'Пост успешно удален.')
        return response


class PostDetailView(DetailView):
    """Детальная страница поста с кешированием"""
    model = Post
    template_name = 'post_detail.html'
    context_object_name = 'post'

    def dispatch(self, request, *args, **kwargs):
        """Проверка прав доступа"""
        if not request.user.is_authenticated:
            messages.info(
                request,
                'Для просмотра полного содержания поста необходимо войти в систему или зарегистрироваться.'
            )
            return redirect('blog:login')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """✅ ОПТИМИЗАЦИЯ: select_related для author"""
        return Post.objects.select_related('author')

    def get_context_data(self, **kwargs):
        """✅ ОПТИМИЗАЦИЯ + КЕШИРОВАНИЕ: кешируем реакции"""
        context = super().get_context_data(**kwargs)
        post = self.get_object()

        # ✅ Кешируем статистику реакций на 5 минут
        cache_key = f'post_reactions_{post.pk}'
        reaction_data = cache.get(cache_key)

        if reaction_data is None:
            # Один агрегированный запрос для подсчета реакций
            reaction_stats = PostReaction.objects.filter(
                post=post
            ).values('reaction_type').annotate(count=Count('reaction_type'))

            reaction_counts = {
                item['reaction_type']: item['count']
                for item in reaction_stats
            }

            reaction_data = {
                'like_count': reaction_counts.get('like', 0),
                'dislike_count': reaction_counts.get('dislike', 0)
            }

            # Сохраняем в кеш
            cache.set(cache_key, reaction_data, 300)

        context['like_count'] = reaction_data['like_count']
        context['dislike_count'] = reaction_data['dislike_count']

        # ✅ Проверяем реакцию пользователя (оптимизированный запрос)
        if self.request.user.is_authenticated:
            user_reaction = PostReaction.objects.filter(
                post=post,
                user=self.request.user
            ).values('reaction_type').first()

            context['user_reaction'] = (
                user_reaction['reaction_type']
                if user_reaction else None
            )
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
            messages.error(
                request,
                'Для установки реакции необходимо войти в систему.'
            )
            return redirect('blog:login')

        reaction_type = request.POST.get('reaction_type')

        if reaction_type not in ['like', 'dislike']:
            messages.error(request, 'Недопустимый тип реакции.')
            return redirect('blog:post_detail', pk=pk)

        # ✅ ОПТИМИЗАЦИЯ: get_or_create без дополнительных запросов
        reaction, created = PostReaction.objects.get_or_create(
            user=request.user,
            post=post,
            defaults={'reaction_type': reaction_type}
        )

        if not created:
            if reaction.reaction_type == reaction_type:
                # Отмена реакции
                reaction.delete()
                messages.success(request, 'Реакция удалена.')
            else:
                # Изменение реакции
                reaction.reaction_type = reaction_type
                reaction.save()
                messages.success(request, 'Реакция изменена.')
        else:
            messages.success(request, 'Реакция добавлена.')

        # ✅ Сбрасываем кеш реакций
        cache.delete(f'post_reactions_{pk}')

        return redirect('blog:post_detail', pk=pk)
