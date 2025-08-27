from rest_framework import serializers
from .models import Scenario, Step


class StepSerializer(serializers.ModelSerializer):
    class Meta:
        model = Step
        fields = [
            "id",
            "name",
            "step_type",
            "data",
            "order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ScenarioSerializer(serializers.ModelSerializer):
    steps = StepSerializer(many=True, read_only=True)
    steps_count = serializers.SerializerMethodField()

    class Meta:
        model = Scenario
        fields = [
            "id",
            "name",
            "description",
            "data",
            "is_active",
            "created_at",
            "updated_at",
            "steps",
            "steps_count",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "steps", "steps_count"]

    def get_steps_count(self, obj):
        return obj.steps.count()


class ScenarioListSerializer(serializers.ModelSerializer):

    steps_count = serializers.SerializerMethodField()

    class Meta:
        model = Scenario
        fields = [
            "id",
            "name",
            "description",
            "is_active",
            "created_at",
            "updated_at",
            "steps_count",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "steps_count"]

    def get_steps_count(self, obj):
        return obj.steps.count()


class StepCreateUpdateSerializer(serializers.ModelSerializer):

    scenario = serializers.PrimaryKeyRelatedField(queryset=Scenario.objects.all())

    class Meta:
        model = Step
        fields = [
            "id",
            "scenario",
            "name",
            "step_type",
            "data",
            "order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
