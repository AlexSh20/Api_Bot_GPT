from rest_framework import serializers
from .models import Bot


class BotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bot
        fields = ["id", "name", "description", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
