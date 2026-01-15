from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blog_project.settings')

app = Celery('blog_project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
