#!/bin/bash

# Запуск Daphne
daphne -p 8000 blog_project.asgi:application &
DAPHNE_PID=$!

# Запуск Celery
celery -A blog_project worker -l info &
CELERY_PID=$!

echo "Daphne PID: $DAPHNE_PID"
echo "Celery PID: $CELERY_PID"
echo "Для остановки нажмите Ctrl+C"

# Ожидание
wait
