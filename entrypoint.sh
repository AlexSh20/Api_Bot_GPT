#!/bin/bash
set -e

echo "Starting Django application..."

# Выполнение миграций
echo "Running migrations..."
python manage.py migrate --noinput || echo "Migration failed, continuing..."

# Сбор статических файлов
echo "Collecting static files..."
python manage.py collectstatic --noinput || echo "Collectstatic failed, continuing..."

echo "Starting server..."
exec "$@"

# Сбор статических файлов
echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting server..."
exec "$@"