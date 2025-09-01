from django.db import models
from django.core.exceptions import ValidationError
import json


def validate_scenario_data(value):
    """Валидатор для поля data сценария"""
    if not value:
        return  # Пустое значение допустимо

    if not isinstance(value, dict):
        raise ValidationError("Данные сценария должны быть в формате JSON объекта")


class Scenario(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")
    bot = models.ForeignKey(
        "bots.Bot",
        on_delete=models.CASCADE,
        related_name="scenarios",
        verbose_name="Бот",
    )
    data = models.JSONField(
        default=dict,  # Изменено: теперь по умолчанию пустой словарь
        blank=True,  # Добавлено: поле может быть пустым в формах
        validators=[validate_scenario_data],
        verbose_name="Данные сценария",
        help_text="JSON данные сценария. Можно оставить пустым для базового сценария.",
    )
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Сценарий"
        verbose_name_plural = "Сценарии"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Устанавливаем базовую структуру если data пустое
        if not self.data:
            self.data = {
                "version": "1.0",
                "description": self.description or "Базовый сценарий",
                "metadata": {
                    "created_at": (
                        self.created_at.isoformat() if self.created_at else None
                    )
                },
            }
        super().save(*args, **kwargs)


class Step(models.Model):
    STEP_TYPES = [
        ("message", "Сообщение"),
        ("gpt_request", "GPT запрос"),
        ("input", "Ввод пользователя"),
        ("condition", "Условие"),
        ("keyboard", "Клавиатура"),
        ("delay", "Задержка"),
        ("api_call", "API вызов"),
        ("jump", "Переход"),
        ("end", "Завершение"),
    ]

    scenario = models.ForeignKey(
        Scenario,
        on_delete=models.CASCADE,
        related_name="steps",
        verbose_name="Сценарий",
    )
    name = models.CharField(max_length=200, verbose_name="Название шага")
    step_type = models.CharField(
        max_length=20, choices=STEP_TYPES, verbose_name="Тип шага"
    )
    data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Данные шага",
        help_text="JSON конфигурация шага",
    )
    order = models.PositiveIntegerField(verbose_name="Порядок")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Шаг"
        verbose_name_plural = "Шаги"
        ordering = ["scenario", "order"]
        unique_together = ["scenario", "order"]

    def __str__(self):
        return f"{self.scenario.name} - {self.name} (#{self.order})"
