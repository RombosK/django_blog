from django.core.management.base import BaseCommand
from blog.moderation_utils import cleanup_expired_bans


class Command(BaseCommand):
    help = 'Очистка истекших банов пользователей (деактивация банов по истечении срока)'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.NOTICE('Начинаем очистку истекших банов...')
        )
        
        cleanup_expired_bans()
        
        self.stdout.write(
            self.style.SUCCESS(
                'Очистка истекших банов завершена'
            )
        )