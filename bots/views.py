from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Bot, TelegramUser, Conversation, UserScenarioSession
from .serializers import (
    BotSerializer,
    TelegramUserSerializer,
    ConversationSerializer,
    ConversationDetailSerializer,
    TestMessageSerializer,
    UserScenarioSessionSerializer,
    ScenarioExecutionSerializer,
)
from .services.gpt_service import GPTService


class BotViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления ботами.
    Предоставляет CRUD операции:
    - GET /api/bots/ - список всех ботов
    - POST /api/bots/ - создание нового бота
    - GET /api/bots/{id}/ - получение бота по ID
    - PUT /api/bots/{id}/ - обновление бота
    - DELETE /api/bots/{id}/ - удаление бота

    Дополнительные endpoints:
    - POST /api/bots/{id}/test-message/ - тестирование бота
    - GET /api/bots/{id}/conversations/ - диалоги бота
    - GET /api/bots/{id}/stats/ - статистика бота
    """

    queryset = Bot.objects.all()
    serializer_class = BotSerializer

    @action(detail=True, methods=["post"])
    def test_message(self, request, pk=None):
        """
        Тестирование бота с сообщением
        POST /api/bots/{id}/test-message/
        """
        bot = self.get_object()
        serializer = TestMessageSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        message = serializer.validated_data["message"]
        telegram_user_id = serializer.validated_data.get("telegram_user_id", 123456789)

        try:
            # Создаем или получаем тестового пользователя
            telegram_user, _ = TelegramUser.objects.get_or_create(
                telegram_id=telegram_user_id,
                defaults={
                    "username": "test_user",
                    "first_name": "Test",
                    "last_name": "User",
                    "is_bot": False,
                },
            )

            # Создаем или получаем диалог
            conversation, _ = Conversation.objects.get_or_create(
                bot=bot,
                telegram_user=telegram_user,
            )

            # Добавляем сообщение пользователя
            conversation.add_message("user", message)

            # Получаем сообщения для GPT
            messages = conversation.get_openai_messages()

            # Инициализируем GPT сервис
            gpt_service = GPTService(api_key=bot.gpt_api_key)

            # Генерируем ответ
            gpt_response = gpt_service.generate_response(
                messages=messages,
                model=bot.gpt_model,
                max_tokens=bot.max_tokens,
                temperature=bot.temperature,
            )

            if gpt_response["success"]:
                # Добавляем ответ бота в диалог
                bot_message = gpt_response["content"]
                conversation.add_message("assistant", bot_message)

                # Обновляем счетчик токенов
                conversation.total_tokens += gpt_response["usage"]["total_tokens"]
                conversation.save()

                return Response(
                    {
                        "success": True,
                        "user_message": message,
                        "bot_response": bot_message,
                        "usage": gpt_response["usage"],
                        "conversation_id": conversation.id,
                    }
                )
            else:
                return Response(
                    {
                        "success": False,
                        "error": gpt_response["error"],
                        "message": gpt_response["message"],
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": "unexpected_error",
                    "message": f"Произошла ошибка: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get"])
    def conversations(self, request, pk=None):
        """
        Получение диалогов бота
        GET /api/bots/{id}/conversations/
        """
        bot = self.get_object()
        conversations = Conversation.objects.filter(bot=bot).order_by("-last_activity")

        # Пагинация
        page = self.paginate_queryset(conversations)
        if page is not None:
            serializer = ConversationSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ConversationSerializer(conversations, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def stats(self, request, pk=None):
        """
        Статистика бота
        GET /api/bots/{id}/stats/
        """
        bot = self.get_object()
        conversations = Conversation.objects.filter(bot=bot)

        stats = {
            "bot_name": bot.name,
            "total_conversations": conversations.count(),
            "active_conversations": conversations.filter(is_active=True).count(),
            "total_tokens_used": sum(conv.total_tokens for conv in conversations),
            "total_messages": sum(len(conv.messages) for conv in conversations),
            "settings": {
                "gpt_model": bot.gpt_model,
                "max_tokens": bot.max_tokens,
                "temperature": bot.temperature,
            },
        }

        return Response(stats)


class TelegramUserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для просмотра пользователей Telegram
    - GET /api/telegram-users/ - список пользователей
    - GET /api/telegram-users/{id}/ - пользователь по ID
    """

    queryset = TelegramUser.objects.all()
    serializer_class = TelegramUserSerializer


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для просмотра диалогов
    - GET /api/conversations/ - список диалогов
    - GET /api/conversations/{id}/ - диалог по ID с сообщениями
    """

    queryset = Conversation.objects.all()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ConversationDetailSerializer
        return ConversationSerializer

    @action(detail=True, methods=["post"])
    def clear(self, request, pk=None):
        """
        Очистка истории диалога
        POST /api/conversations/{id}/clear/
        """
        conversation = self.get_object()
        conversation.clear_history()

        return Response(
            {
                "success": True,
                "message": "История диалога очищена",
                "conversation_id": conversation.id,
            }
        )


# ViewSet для работы с сессиями сценариев


class UserScenarioSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для просмотра сессий сценариев
    - GET /api/scenario-sessions/ - список сессий
    - GET /api/scenario-sessions/{id}/ - сессия по ID

    Дополнительные endpoints:
    - POST /api/scenario-sessions/{id}/end/ - завершение сессии
    """

    queryset = UserScenarioSession.objects.all()
    serializer_class = UserScenarioSessionSerializer

    @action(detail=True, methods=["post"])
    def end(self, request, pk=None):
        """
        Завершение сессии сценария
        POST /api/scenario-sessions/{id}/end/
        """
        session = self.get_object()

        if not session.is_active:
            return Response(
                {"error": "Сессия уже завершена"}, status=status.HTTP_400_BAD_REQUEST
            )

        session.end_session()

        return Response(
            {"success": True, "message": "Сессия завершена", "session_id": session.id}
        )
