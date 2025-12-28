"""
Настройки логирования для отслеживания производительности
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'performance': {
            'format': '[PERFORMANCE] {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'performance_file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'performance.log',
            'formatter': 'performance',
        },
        'django_file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
    },
    'loggers': {
        'django': {
            'handlers': ['django_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['django_file'],
            'level': 'WARNING',  # Уменьшаем уровень логирования SQL-запросов
            'propagate': False,
        },
        'blog.performance': {
            'handlers': ['performance_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Создаем директорию для логов, если она не существует
log_dir = BASE_DIR / 'logs'
if not log_dir.exists():
    log_dir.mkdir(parents=True, exist_ok=True)