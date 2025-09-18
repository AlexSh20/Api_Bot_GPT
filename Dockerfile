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

# Явно копируем файл зависимостей в /tmp и проверяем его наличие
COPY requirements.txt /tmp/requirements.txt

# Проверяем наличие файла requirements.txt
RUN ls -la /tmp/requirements.txt

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

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
# Копируем код приложения
COPY . .

# Создаем директории для статических файлов и медиа
RUN mkdir -p /app/staticfiles /app/media

# Копируем и настраиваем entrypoint скрипт
COPY entrypoint.sh /entrypoint.sh

# Устанавливаем права доступа (пока еще root)
RUN chmod +x /entrypoint.sh && \
    chown -R django:django /app && \
    chown django:django /entrypoint.sh

# Переключаемся на непривилегированного пользователя
USER django

# Устанавливаем права доступа
RUN chown -R django:django /app && chown django:django /entrypoint.sh

# Переключаемся на непривилегированного пользователя
USER django

# Открываем порт
EXPOSE 8000

# Устанавливаем entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Команда по умолчанию
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "ApiBotGpt.wsgi:application"]