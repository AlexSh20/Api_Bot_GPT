from rest_framework import serializers
from .models import Scenario, Step


class ScenarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scenario
        fields = "__all__"

    def validate_data(self, value):
        """Валидация поля data"""
        if value is None:
            return {}

        if not isinstance(value, dict):
            raise serializers.ValidationError(
                "Данные сценария должны быть JSON объектом"
            )

        return value

    def create(self, validated_data):
        """Создание сценария с базовыми данными"""
        if not validated_data.get("data"):
            validated_data["data"] = {
                "version": "1.0",
                "description": validated_data.get("description", "Базовый сценарий"),
            }
        return super().create(validated_data)


class ScenarioListSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор для списка сценариев"""

    bot_name = serializers.CharField(source="bot.name", read_only=True)
    steps_count = serializers.SerializerMethodField()

    class Meta:
        model = Scenario
        fields = [
            "id",
            "name",
            "description",
            "bot",
            "bot_name",
            "is_active",
            "steps_count",
            "created_at",
        ]

    def get_steps_count(self, obj):
        return obj.steps.count()


class StepSerializer(serializers.ModelSerializer):
    scenario_name = serializers.CharField(source="scenario.name", read_only=True)

    class Meta:
        model = Step
        fields = "__all__"


class StepCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Step
        fields = "__all__"

    def validate_data(self, value):
        """Валидация данных шага"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Данные шага должны быть JSON объектом")
        return value


class ScenarioExecutionSerializer(serializers.Serializer):
    """Сериализатор для запуска сценария"""

    bot_id = serializers.IntegerField()
    telegram_user_id = serializers.IntegerField()
    scenario_id = serializers.IntegerField(required=False)
    context_data = serializers.DictField(required=False, default=dict)


class StepTemplateSerializer(serializers.Serializer):
    """Сериализатор для шаблонов шагов"""

    step_type = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    template_data = serializers.DictField()
