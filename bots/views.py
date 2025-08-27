from rest_framework import viewsets
from .models import Bot
from .serializers import BotSerializer


class BotViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления ботами.
    Предоставляет CRUD операции:
    - GET /api/bots/ - список всех ботов
    - POST /api/bots/ - создание нового бота
    - GET /api/bots/{id}/ - получение бота по ID
    - PUT /api/bots/{id}/ - обновление бота
    - DELETE /api/bots/{id}/ - удаление бота
    """

    queryset = Bot.objects.all()
    serializer_class = BotSerializer
