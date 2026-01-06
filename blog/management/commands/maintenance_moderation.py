from django.core.management.base import BaseCommand
from blog.moderation_utils import cleanup_expired_bans, cleanup_old_message_rates


class Command(BaseCommand):
    help = 'Выполняет периодическое обслуживание системы модерации: очистка истекших банов и старых записей о частоте сообщений'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.NOTICE('Начинаем периодическое обслуживание системы модерации...')
        )
        
        # Очистка истекших банов
        self.stdout.write(
            self.style.NOTICE('Проверяем и деактивируем истекшие баны...')
        )
        cleanup_expired_bans()
        self.stdout.write(
            self.style.SUCCESS('Проверка истекших банов завершена')
        )
        
        # Очистка старых записей о частоте сообщений
        self.stdout.write(
            self.style.NOTICE('Очищаем старые записи о частоте сообщений...')
        )
        cleanup_old_message_rates()
        self.stdout.write(
            self.style.SUCCESS('Очистка старых записей завершена')
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                'Периодическое обслуживание системы модерации завершено'
            )
        )