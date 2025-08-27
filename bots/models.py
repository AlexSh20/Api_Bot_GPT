from django.db import models


class Bot(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название бота")
    description = models.TextField(blank=True, verbose_name="Описание")
    token = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Токен бота",
        help_text="API токен для подключения к мессенджеру",
    )
    platform = models.CharField(
        max_length=50,
        choices=[("telegram", "Telegram"), ("vk", "VKontakte")],
        default="telegram",
        verbose_name="Платформа",
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
