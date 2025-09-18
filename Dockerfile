# Многоэтапная сборка для оптимизации размера образа
FROM python:3.13-slim as builder

# Устанавливаем системные зависимости для сборки
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Создаем виртуальное окружение
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Финальный образ
FROM python:3.13-slim

# Устанавливаем только runtime зависимости
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Копируем виртуальное окружение из builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Создаем пользователя для безопасности
RUN groupadd -r django && useradd -r -g django django

# Создаем рабочую директорию
WORKDIR /app

# Копируем код приложения
COPY . .

# Создаем директории для статических файлов и медиа
RUN mkdir -p /app/staticfiles /app/media

# Устанавливаем права доступа
RUN chown -R django:django /app

# Переключаемся на непривилегированного пользователя
USER django

# Собираем статические файлы
RUN python manage.py collectstatic --noinput --settings=ApiBotGpt.settings

# Открываем порт
EXPOSE 8000

# Команда по умолчанию
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "ApiBotGpt.wsgi:application"]