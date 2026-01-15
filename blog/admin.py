import csv
from django.http import HttpResponse
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Post, ChatRoom, Message, ModerationSettings, UserMessageRate, UserBan

def export_users_csv(modeladmin, request, queryset):
    """Экспорт пользователей в CSV с оптимизацией"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users.csv"'

    writer = csv.writer(response)

    # Заголовки
    writer.writerow([
        'ID', 'Email', 'Username', 'First Name', 'Last Name',
        'Is Active', 'Is Staff', 'Is Superuser', 'Date Joined',
        'Last Login'
    ])

    # ✅ ОПТИМИЗАЦИЯ: только нужные поля
    queryset = queryset.only(
        'id', 'email', 'username', 'first_name', 'last_name',
        'is_active', 'is_staff', 'is_superuser', 'date_joined', 'last_login'
    )

    # Данные
    for user in queryset:
        writer.writerow([
            user.id, user.email, user.username, user.first_name, user.last_name,
            user.is_active, user.is_staff, user.is_superuser,
            user.date_joined, user.last_login
        ])

    return response

export_users_csv.short_description = "Экспорт выбранных пользователей в CSV"


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['email', 'username', 'first_name', 'last_name', 'is_active', 'is_staff']
    list_filter = ['is_active', 'is_staff', 'is_superuser']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Персональная информация', {'fields': ('username', 'first_name', 'last_name')}),
        ('Разрешения', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2'),
        }),
    )

    search_fields = ['email', 'username']
    ordering = ['email']
    actions = [export_users_csv]

    # ✅ ПАГИНАЦИЯ
    list_per_page = 25

    # ✅ ОПТИМИЗАЦИЯ M2M полей
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Предзагружаем groups и permissions для админки
        return qs.prefetch_related('groups', 'user_permissions')


admin.site.register(CustomUser, CustomUserAdmin)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['title', 'author_username', 'created_at', 'is_published']
    list_filter = ['is_published', 'created_at']  # ✅ Убрал 'author' - он вызывал N+1!
    list_editable = ['is_published']
    search_fields = ['title', 'content', 'author__username']  # ✅ Поиск через __
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'content', 'image', 'author')
        }),
        ('Статус', {
            'fields': ('is_published',)
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # ✅ ПАГИНАЦИЯ
    list_per_page = 25

    # ✅ КАСТОМНЫЙ МЕТОД вместо прямого 'author'
    def author_username(self, obj):
        return obj.author.username
    author_username.short_description = 'Автор'
    author_username.admin_order_field = 'author__username'  # ✅ Сортировка

    # ✅ ОПТИМИЗАЦИЯ - ГЛАВНОЕ ИСПРАВЛЕНИЕ!
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('author')  # ✅ Убираем N+1 для author!


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'topic', 'created_at', 'is_private']
    list_filter = ['is_private', 'created_at']
    search_fields = ['name', 'topic']

    # ✅ ПАГИНАЦИЯ
    list_per_page = 25


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['user_username', 'room_name', 'content_preview', 'created_at', 'is_moderated', 'is_blocked']
    list_filter = ['is_moderated', 'is_blocked', 'created_at']  # ✅ Убрал 'room'
    search_fields = ['content', 'user__username', 'user__email', 'room__name']
    readonly_fields = ['created_at']

    # ✅ ПАГИНАЦИЯ
    list_per_page = 50

    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Содержание (превью)'

    # ✅ КАСТОМНЫЕ МЕТОДЫ
    def user_username(self, obj):
        return obj.user.username
    user_username.short_description = 'Пользователь'
    user_username.admin_order_field = 'user__username'

    def room_name(self, obj):
        return obj.room.name
    room_name.short_description = 'Комната'
    room_name.admin_order_field = 'room__name'

    # ✅ ОПТИМИЗАЦИЯ - УБИРАЕМ N+1!
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'room')  # ✅ 2 ForeignKey сразу!


@admin.register(ModerationSettings)
class ModerationSettingsAdmin(admin.ModelAdmin):
    list_display = ['room_name', 'enabled', 'max_messages_per_minute', 'enable_toxicity_filter']
    list_filter = ['enabled', 'enable_toxicity_filter']
    search_fields = ['room__name']

    # ✅ ПАГИНАЦИЯ
    list_per_page = 25

    # ✅ КАСТОМНЫЙ МЕТОД
    def room_name(self, obj):
        return obj.room.name
    room_name.short_description = 'Комната'
    room_name.admin_order_field = 'room__name'

    # ✅ ОПТИМИЗАЦИЯ
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('room')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "room":
            kwargs["queryset"] = ChatRoom.objects.all().order_by('name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(UserMessageRate)
class UserMessageRateAdmin(admin.ModelAdmin):
    list_display = ['user_username', 'room_name', 'timestamp']
    list_filter = ['timestamp']
    search_fields = ['user__username', 'user__email', 'room__name']
    readonly_fields = ['timestamp']

    # ✅ ПАГИНАЦИЯ
    list_per_page = 50

    # ✅ КАСТОМНЫЕ МЕТОДЫ
    def user_username(self, obj):
        return obj.user.username
    user_username.short_description = 'Пользователь'
    user_username.admin_order_field = 'user__username'

    def room_name(self, obj):
        return obj.room.name
    room_name.short_description = 'Комната'
    room_name.admin_order_field = 'room__name'

    # ✅ ОПТИМИЗАЦИЯ
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'room')


@admin.register(UserBan)
class UserBanAdmin(admin.ModelAdmin):
    list_display = [
        'user_username', 'room_name', 'moderator_username', 
        'reason', 'created_at', 'expires_at', 
        'is_permanent_display', 'is_active'
    ]
    list_filter = ['is_permanent', 'is_active', 'created_at']  # ✅ Убрал 'room'
    search_fields = ['user__username', 'user__email', 'moderator__username', 'reason']
    readonly_fields = ['created_at']
    list_editable = ['is_active']

    # ✅ ПАГИНАЦИЯ
    list_per_page = 25

    fieldsets = (
        ('Информация о бане', {
            'fields': ('user', 'room', 'moderator', 'reason', 'is_permanent'),
            'description': 'Основная информация о бане пользователя'
        }),
        ('Временные параметры', {
            'fields': ('created_at', 'expires_at', 'is_active'),
            'classes': ('collapse',),
            'description': 'Временные параметры бана'
        }),
    )

    # ✅ КАСТОМНЫЕ МЕТОДЫ
    def user_username(self, obj):
        return obj.user.username
    user_username.short_description = 'Пользователь'
    user_username.admin_order_field = 'user__username'

    def room_name(self, obj):
        return obj.room.name if obj.room else '-'
    room_name.short_description = 'Комната'
    room_name.admin_order_field = 'room__name'

    def moderator_username(self, obj):
        return obj.moderator.username if obj.moderator else '-'
    moderator_username.short_description = 'Модератор'
    moderator_username.admin_order_field = 'moderator__username'

    def is_permanent_display(self, obj):
        return "Да" if obj.is_permanent else "Нет"
    is_permanent_display.short_description = "Постоянный бан"
    is_permanent_display.admin_order_field = 'is_permanent'

    # ✅ ОПТИМИЗАЦИЯ - ГЛАВНОЕ!
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'room', 'moderator')  # ✅ 3 ForeignKey!

    def save_model(self, request, obj, form, change):
        # Если это новый бан и не указано время окончания для временного бана
        if not obj.pk and not obj.is_permanent and not obj.expires_at:
            from django.utils import timezone
            from datetime import timedelta
            # Устанавливаем время окончания по умолчанию - 7 дней
            obj.expires_at = timezone.now() + timedelta(days=7)

        super().save_model(request, obj, form, change)
