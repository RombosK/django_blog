from django.core.management.base import BaseCommand
from blog.moderation_utils import cleanup_old_message_rates


class Command(BaseCommand):
    help = 'Очистка старых записей о частоте сообщений пользователей'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.NOTICE('Начинаем очистку старых записей о частоте сообщений...')
        )
        
        deleted_count = cleanup_old_message_rates()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Очистка завершена. Удалено записей: {deleted_count}'
            )
        )