from django.db import models


class Bot(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название бота")
    description = models.TextField(blank=True, verbose_name="Описание")
    telegram_token = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Telegram токен",
        help_text="API токен Telegram бота",
    )
    gpt_api_key = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="OpenAI API ключ",
        help_text=("API ключ для OpenAI " "(если пустой, используется глобальный)"),
    )
    gpt_model = models.CharField(
        max_length=50,
        default="gpt-3.5-turbo",
        verbose_name="GPT модель",
        help_text="Модель GPT для использования",
    )
    max_tokens = models.IntegerField(
        default=1000,
        verbose_name="Максимум токенов",
        help_text="Максимальное количество токенов в ответе",
    )
    temperature = models.FloatField(
        default=0.7,
        verbose_name="Температура",
        help_text="Креативность ответов (0.0-1.0)",
    )
    system_prompt = models.TextField(
        default=(
            "Ты полезный AI-ассистент. " "Отвечай дружелюбно и помогай пользователям."
        ),
        verbose_name="Системный промпт",
        help_text="Инструкция для GPT о том, как себя вести",
    )
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Бот"
        verbose_name_plural = "Боты"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class TelegramUser(models.Model):
    telegram_id = models.BigIntegerField(
        unique=True,
        verbose_name="Telegram ID",
        help_text="Уникальный ID пользователя в Telegram",
    )
    username = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Username",
    )
    first_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Имя",
    )
    last_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Фамилия",
    )
    is_bot = models.BooleanField(default=False, verbose_name="Это бот")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Пользователь Telegram"
        verbose_name_plural = "Пользователи Telegram"
        ordering = ["-created_at"]

    def __str__(self):
        if self.username:
            return f"@{self.username}"
        return f"{self.first_name} ({self.telegram_id})"


class Conversation(models.Model):
    bot = models.ForeignKey(
        Bot,
        on_delete=models.CASCADE,
        related_name="conversations",
        verbose_name="Бот",
    )
    telegram_user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name="conversations",
        verbose_name="Пользователь",
    )
    messages = models.JSONField(
        default=list,
        verbose_name="Сообщения",
        help_text="История сообщений в формате OpenAI",
    )
    total_tokens = models.IntegerField(
        default=0,
        verbose_name="Всего токенов",
        help_text="Общее количество использованных токенов",
    )
    last_activity = models.DateTimeField(
        auto_now=True,
        verbose_name="Последняя активность",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Диалог"
        verbose_name_plural = "Диалоги"
        ordering = ["-last_activity"]
        unique_together = ["bot", "telegram_user"]

    def __str__(self):
        return f"{self.bot.name} - {self.telegram_user}"

    def add_message(self, role, content):
        """Добавить сообщение в диалог"""
        from django.utils import timezone

        message = {
            "role": role,
            "content": content,
            "timestamp": timezone.now().isoformat(),
        }
        self.messages.append(message)
        self.save()

    def get_openai_messages(self, max_messages=20):
        """Получить сообщения в формате OpenAI API"""
        # Системный промпт всегда первый
        messages = [{"role": "system", "content": self.bot.system_prompt}]

        # Добавляем последние сообщения пользователя
        recent_messages = self.messages[-max_messages:] if self.messages else []
        for msg in recent_messages:
            messages.append({"role": msg["role"], "content": msg["content"]})

        return messages

    def clear_history(self):
        """Очистить историю сообщений"""
        self.messages = []
        self.total_tokens = 0
        self.save()


# Модель для отслеживания сессий сценариев пользователей
class UserScenarioSession(models.Model):
    """Модель для отслеживания текущего состояния пользователя в сценарии"""

    bot = models.ForeignKey(
        Bot,
        on_delete=models.CASCADE,
        related_name="scenario_sessions",
        verbose_name="Бот",
    )
    telegram_user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name="scenario_sessions",
        verbose_name="Пользователь",
    )
    scenario = models.ForeignKey(
        "scenarios.Scenario",
        on_delete=models.CASCADE,
        related_name="user_sessions",
        verbose_name="Сценарий",
    )
    current_step = models.ForeignKey(
        "scenarios.Step",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Текущий шаг",
    )
    context_data = models.JSONField(
        default=dict,
        verbose_name="Контекстные данные",
        help_text="Данные для передачи между шагами",
    )
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="Время начала")
    last_activity = models.DateTimeField(
        auto_now=True, verbose_name="Последняя активность"
    )

    class Meta:
        verbose_name = "Сессия сценария"
        verbose_name_plural = "Сессии сценариев"
        ordering = ["-last_activity"]
        unique_together = ["bot", "telegram_user"]

    def __str__(self):
        return f"{self.bot.name} - {self.telegram_user} - {self.scenario.name}"

    def update_step(self, new_step, context_update=None):
        """Обновить текущий шаг сессии"""
        self.current_step = new_step
        if context_update:
            self.context_data.update(context_update)
        self.save()

    def end_session(self):
        """Завершить сессию"""
        self.is_active = False
        self.save()
