from django.contrib import admin
from .models import Bot, TelegramUser, Conversation, UserScenarioSession


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = [
        "telegram_id",
        "username",
        "first_name",
        "last_name",
        "is_bot",
        "created_at",
    ]
    list_filter = ["is_bot", "created_at"]
    search_fields = ["telegram_id", "username", "first_name", "last_name"]

    # Убираем telegram_id из readonly_fields если он там есть
    readonly_fields = ["created_at", "updated_at"]

    # Явно указываем поля для редактирования
    fields = [
        "telegram_id",  # Это поле должно быть редактируемым
        "username",
        "first_name",
        "last_name",
        "is_bot",
        "created_at",
        "updated_at",
    ]

    def get_readonly_fields(self, request, obj=None):
        # При создании нового объекта (obj=None) все поля редактируемы
        if obj is None:
            return ["created_at", "updated_at"]
        # При редактировании существующего объекта telegram_id становится readonly
        return ["telegram_id", "created_at", "updated_at"]


@admin.register(Bot)
class BotAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("Основная информация", {"fields": ("name", "description", "is_active")}),
        ("Telegram настройки", {"fields": ("telegram_token",)}),
        (
            "GPT настройки",
            {
                "fields": (
                    "gpt_api_key",
                    "gpt_model",
                    "max_tokens",
                    "temperature",
                    "system_prompt",
                )
            },
        ),
        (
            "Системная информация",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = [
        "bot",
        "telegram_user",
        "total_tokens",
        "is_active",
        "last_activity",
    ]
    list_filter = ["is_active", "last_activity", "bot"]
    search_fields = [
        "bot__name",
        "telegram_user__username",
        "telegram_user__first_name",
    ]
    readonly_fields = ["created_at", "last_activity", "total_tokens"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("bot", "telegram_user")


@admin.register(UserScenarioSession)
class UserScenarioSessionAdmin(admin.ModelAdmin):
    list_display = [
        "bot",
        "telegram_user",
        "scenario",
        "current_step",
        "is_active",
        "last_activity",
    ]
    list_filter = ["is_active", "last_activity", "bot", "scenario"]
    search_fields = ["bot__name", "telegram_user__username", "scenario__name"]
    readonly_fields = ["started_at", "last_activity"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("bot", "telegram_user", "scenario", "current_step")
        )
