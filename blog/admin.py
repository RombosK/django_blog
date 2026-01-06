import csv
from django.http import HttpResponse
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Post, ChatRoom, Message, ModerationSettings, UserMessageRate, UserBan

def export_users_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users.csv"'

    writer = csv.writer(response)
    # Заголовки
    writer.writerow([
        'ID', 'Email', 'Username', 'First Name', 'Last Name',
        'Is Active', 'Is Staff', 'Is Superuser', 'Date Joined',
        'Last Login'
    ])

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

admin.site.register(CustomUser, CustomUserAdmin)

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'created_at', 'is_published']
    list_filter = ['is_published', 'created_at', 'author']
    list_editable = ['is_published']
    search_fields = ['title', 'content']
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

@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'topic', 'created_at', 'is_private']
    list_filter = ['is_private', 'created_at']
    search_fields = ['name', 'topic']

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['user', 'room', 'content_preview', 'created_at', 'is_moderated', 'is_blocked']
    list_filter = ['is_moderated', 'is_blocked', 'created_at', 'room']
    search_fields = ['content', 'user__username', 'user__email']
    readonly_fields = ['created_at']

    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Содержание (превью)'

@admin.register(ModerationSettings)
class ModerationSettingsAdmin(admin.ModelAdmin):
    list_display = ['room', 'enabled', 'max_messages_per_minute', 'enable_toxicity_filter']
    list_filter = ['enabled', 'enable_toxicity_filter']
    search_fields = ['room__name']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "room":
            kwargs["queryset"] = ChatRoom.objects.all().order_by('name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(UserMessageRate)
class UserMessageRateAdmin(admin.ModelAdmin):
    list_display = ['user', 'room', 'timestamp']
    list_filter = ['timestamp', 'room']
    search_fields = ['user__username', 'user__email', 'room__name']
    readonly_fields = ['timestamp']


@admin.register(UserBan)
class UserBanAdmin(admin.ModelAdmin):
    list_display = ['user', 'room', 'moderator', 'reason', 'created_at', 'expires_at', 'is_permanent_display', 'is_active']
    list_filter = ['is_permanent', 'is_active', 'created_at', 'room']
    search_fields = ['user__username', 'user__email', 'moderator__username', 'reason']
    readonly_fields = ['created_at']
    list_editable = ['is_active']

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

    def is_permanent_display(self, obj):
        return "Да" if obj.is_permanent else "Нет"
    is_permanent_display.short_description = "Постоянный бан"
    is_permanent_display.admin_order_field = 'is_permanent'

    def save_model(self, request, obj, form, change):
        # Если это новый бан и не указано время окончания для временного бана
        if not obj.pk and not obj.is_permanent and not obj.expires_at:
            from django.utils import timezone
            from datetime import timedelta
            # Устанавливаем время окончания по умолчанию - 7 дней
            obj.expires_at = timezone.now() + timedelta(days=7)

        super().save_model(request, obj, form, change)