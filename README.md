# Django-приложение с API для создания и управления ботами.

### Основные компоненты
**Модели:**
   - `Bot` - настройки бота и GPT параметры
   - `TelegramUser` - пользователи Telegram
   - `Conversation` - история диалогов с токенами

## Пошаговый запуск

### 1. Настройка виртуального окружения
```powershell
# Удаляем старое окружение (если есть проблемы)
Remove-Item -Recurse -Force env -ErrorAction SilentlyContinue

# Создаем новое виртуальное окружение
python -m venv env

# Активируем окружение
.\env\Scripts\Activate.ps1

# Обновляем pip
python -m pip install --upgrade pip
```

### 2. Установка зависимостей
```powershell
# Устанавливаем pip-tools
pip install pip-tools

# Компилируем requirements
pip-compile requirements.in

# Устанавливаем зависимости
pip install -r requirements.txt
```

### 3. Настройка базы данных
```powershell
# Создаем миграции
python manage.py makemigrations bots

# Применяем миграции
python manage.py migrate

# Создаем суперпользователя
python manage.py createsuperuser --username admin --email admin@example.com
# Пароль: любой (можно простой для тестирования)
```

### 4. Настройка переменных окружения
Создайте файл `.env` или установите переменные:
```powershell
# OpenAI API ключ (глобальный fallback)
$env:OPENAI_API_KEY="sk-your-openai-api-key-here"

# Или создайте файл .env в корне проекта:
# OPENAI_API_KEY=sk-your-openai-api-key-here
```

### 5. Создание Telegram бота
1. Напишите @BotFather в Telegram
2. Создайте нового бота: `/newbot`
3. Получите токен вида: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`

### 6. Запуск проекта

**Проверка работы:**
- Откройте http://127.0.0.1:8000/ - должен показать JSON с информацией об API
- Откройте http://127.0.0.1:8000/admin/ - админка Django
- Откройте http://127.0.0.1:8000/api/bots/ - API для ботов


## Настройка через Django Admin

1. Откройте: http://127.0.0.1:8000/admin/
2. Войдите под суперпользователем (admin / ваш пароль)
3. Создайте нового бота в разделе "Боты":
   - **Название**: "Мой GPT Помощник"
   - **Описание**: "Умный помощник на базе GPT"
   - **Telegram токен**: ваш токен от BotFather
   - **GPT API ключ**: ваш OpenAI ключ (или оставьте пустым)
   - **GPT модель**: gpt-3.5-turbo
   - **Максимум токенов**: 1000
   - **Температура**: 0.7
   - **Системный промпт**: настройте поведение бота
   - **Активен**: ✅

## Мониторинг

### Логи
- `django.log` - логи Django

### Админка Django
- Просмотр всех ботов и их настроек
- Список пользователей Telegram
- История диалогов с подсчетом токенов

### API Endpoints для мониторинга
- `GET /api/bots/` - список ботов
- `GET /api/bots/{id}/conversations/` - диалоги бота
- `GET /api/bots/{id}/stats/` - статистика использования
- `GET /api/conversations/` - все диалоги
- `GET /api/telegram-users/` - пользователи
