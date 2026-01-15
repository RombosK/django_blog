# blog/tasks.py - ОПТИМАЛЬНАЯ ВЕРСИЯ ✅

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from smtplib import SMTPException
import logging

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(SMTPException,),  # ✅ Авто-retry для SMTP ошибок
    retry_backoff=True,              # ✅ Exponential backoff
    retry_jitter=True                # ✅ Добавляет случайность
)
def send_welcome_email(self, user_id):
    """
    Отправка приветственного письма после регистрации.

    ✅ 3 попытки с exponential backoff (60s, 120s, 240s)
    ✅ Автоматический retry при SMTP ошибках
    ✅ Логирование всех попыток
    """
    from blog.models import CustomUser

    try:
        user = CustomUser.objects.get(id=user_id)

        send_mail(
            subject='Добро пожаловать в наш блог!',
            message=f'''Привет, {user.username}!

Спасибо за регистрацию в нашем блоге.

Теперь вы можете:
- Читать все посты
- Оставлять реакции
- Участвовать в чате

С уважением,
Команда блога''',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,  # ✅ Поднимаем исключения для retry
        )

        logger.info(f"✅ Welcome email sent to {user.email}")
        return f"Welcome email sent to {user.email}"

    except CustomUser.DoesNotExist:
        # Пользователь удалён - не повторяем
        logger.error(f"❌ User {user_id} not found")
        return f"User {user_id} not found"

    except SMTPException as e:
        # ✅ SMTP ошибки - авто-retry (autoretry_for)
        logger.warning(
            f"⚠️  SMTP error for user {user_id} (attempt {self.request.retries + 1}/{self.max_retries}): {str(e)}"
        )
        raise  # Celery сам сделает retry

    except Exception as e:
        # Другие ошибки - логируем и повторяем вручную
        logger.error(f"❌ Failed to send welcome email to user {user_id}: {str(e)}")

        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            # После 3 попыток - сдаёмся
            logger.error(f"🔴 Max retries exceeded for welcome email to user {user_id}")
            return f"Failed after {self.max_retries} retries: {str(e)}"


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(SMTPException,),
    retry_backoff=True,
    retry_jitter=True
)
def send_password_reset_email(self, email, reset_url):
    """Отправка письма для сброса пароля с retry"""
    try:
        send_mail(
            subject='Восстановление пароля',
            message=f'''Здравствуйте!

Вы запросили восстановление пароля для вашего аккаунта.

Для сброса пароля перейдите по ссылке:
{reset_url}

Если вы не запрашивали восстановление пароля, просто проигнорируйте это письмо.

Ссылка действительна в течение 24 часов.

С уважением,
Команда блога''',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

        logger.info(f"✅ Password reset email sent to {email}")
        return f"Password reset email sent to {email}"

    except SMTPException as e:
        logger.warning(
            f"⚠️  SMTP error for password reset to {email} (attempt {self.request.retries + 1}/{self.max_retries})"
        )
        raise  # Авто-retry

    except Exception as e:
        logger.error(f"❌ Failed to send password reset email to {email}: {str(e)}")

        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"🔴 Max retries exceeded for password reset email to {email}")
            return f"Failed after {self.max_retries} retries"


# ═══════════════════════════════════════════════════════════════════════════
# ✅ BONUS: Универсальная функция с кастомными настройками
# ═══════════════════════════════════════════════════════════════════════════

@shared_task(
    bind=True,
    max_retries=5,           # ✅ Для критичных писем - больше попыток
    default_retry_delay=120,  # ✅ 2 минуты
    autoretry_for=(SMTPException,),
    retry_backoff=True,
    retry_jitter=True
)
def send_critical_email(self, user_id, subject, message):
    """
    Отправка критичных писем с увеличенным количеством попыток.
    Используй для важных уведомлений (payment, security).
    """
    from blog.models import CustomUser

    try:
        user = CustomUser.objects.get(id=user_id)

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        logger.info(f"✅ Critical email sent to {user.email}: {subject}")
        return f"Email sent to {user.email}"

    except CustomUser.DoesNotExist:
        logger.error(f"❌ User {user_id} not found")
        return f"User {user_id} not found"

    except Exception as e:
        logger.error(f"❌ Failed to send critical email to user {user_id}: {str(e)}")

        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.critical(f"🔴🔴🔴 CRITICAL: Max retries exceeded for user {user_id}")
            # Здесь можно отправить алерт админам
            return f"CRITICAL FAILURE after {self.max_retries} retries"
