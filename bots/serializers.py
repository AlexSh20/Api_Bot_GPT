from rest_framework import serializers
from .models import Bot, TelegramUser, Conversation, UserScenarioSession


class BotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bot
        fields = [
            "id",
            "name",
            "description",
            "telegram_token",
            "gpt_api_key",
            "gpt_model",
            "max_tokens",
            "temperature",
            "system_prompt",
            "is_active",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "telegram_token": {"write_only": True},
            "gpt_api_key": {"write_only": True},
        }


class TelegramUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramUser
        fields = [
            "id",
            "telegram_id",
            "username",
            "first_name",
            "last_name",
            "is_bot",
            "created_at",
            "updated_at",
        ]


class ConversationSerializer(serializers.ModelSerializer):
    bot_name = serializers.CharField(source="bot.name", read_only=True)
    user_display = serializers.CharField(source="telegram_user.__str__", read_only=True)
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "bot",
            "bot_name",
            "telegram_user",
            "user_display",
            "message_count",
            "total_tokens",
            "last_activity",
            "is_active",
            "created_at",
        ]

    def get_message_count(self, obj):
        return len(obj.messages)


class ConversationDetailSerializer(ConversationSerializer):
    messages = serializers.JSONField(read_only=True)

    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields + ["messages"]


class TestMessageSerializer(serializers.Serializer):
    message = serializers.CharField(
        max_length=4000, help_text="Сообщение для тестирования бота"
    )
    telegram_user_id = serializers.IntegerField(
        required=False, help_text="ID пользователя Telegram (для тестирования)"
    )


# Сериализаторы для работы с сессиями сценариев


class UserScenarioSessionSerializer(serializers.ModelSerializer):
    """Сериализатор для модели UserScenarioSession"""

    bot_name = serializers.CharField(source="bot.name", read_only=True)
    user_display = serializers.CharField(source="telegram_user.__str__", read_only=True)
    scenario_name = serializers.CharField(source="scenario.name", read_only=True)
    current_step_name = serializers.CharField(
        source="current_step.name", read_only=True
    )

    class Meta:
        model = UserScenarioSession
        fields = [
            "id",
            "bot",
            "bot_name",
            "telegram_user",
            "user_display",
            "scenario",
            "scenario_name",
            "current_step",
            "current_step_name",
            "context_data",
            "is_active",
            "started_at",
            "last_activity",
        ]


class ScenarioExecutionSerializer(serializers.Serializer):
    """Сериализатор для запуска сценария"""

    scenario_id = serializers.IntegerField(help_text="ID сценария для запуска")
    telegram_user_id = serializers.IntegerField(help_text="ID пользователя Telegram")
    context_data = serializers.JSONField(
        required=False, default=dict, help_text="Начальные контекстные данные"
    )
