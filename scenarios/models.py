from django.db import models


class Scenario(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название сценария")
    description = models.TextField(blank=True, verbose_name="Описание")
    bot = models.ForeignKey(
        "bots.Bot",
        on_delete=models.CASCADE,
        related_name="scenarios",
        verbose_name="Бот",
        null=True,
        blank=True,
        help_text="Бот, к которому привязан сценарий",
    )
    data = models.JSONField(default=dict, verbose_name="Данные сценария")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Сценарий"
        verbose_name_plural = "Сценарии"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def steps_count(self):
        return self.steps.count()


class Step(models.Model):
    STEP_TYPES = [
        ("message", "Сообщение"),
        ("input", "Ввод данных"),
        ("condition", "Условие"),
        ("action", "Действие"),
        ("keyboard", "Клавиатура"),
        ("delay", "Задержка"),
        ("api_call", "API вызов"),
        ("jump", "Переход"),
        ("end", "Завершение"),
    ]

    scenario = models.ForeignKey(
        Scenario,
        related_name="steps",
        on_delete=models.CASCADE,
        verbose_name="Сценарий",
    )
    name = models.CharField(max_length=100, verbose_name="Название шага")
    step_type = models.CharField(
        max_length=50, choices=STEP_TYPES, verbose_name="Тип шага"
    )
    data = models.JSONField(default=dict, verbose_name="Данные шага")
    order = models.PositiveIntegerField(verbose_name="Порядок выполнения")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Шаг сценария"
        verbose_name_plural = "Шаги сценариев"
        ordering = ["scenario", "order"]
        unique_together = ["scenario", "order"]

    def __str__(self):
        return f"{self.scenario.name} - {self.name} (#{self.order})"
