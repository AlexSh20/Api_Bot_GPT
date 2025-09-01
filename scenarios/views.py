from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Scenario, Step
from .serializers import (
    ScenarioSerializer,
    ScenarioListSerializer,
    StepSerializer,
    StepCreateUpdateSerializer,
    ScenarioExecutionSerializer,
    StepTemplateSerializer,
)
from .services.execution_service import ScenarioExecutionService
from bots.models import Bot, TelegramUser


class ScenarioViewSet(viewsets.ModelViewSet):
    """
    CRUD операции:
    - GET /api/scenarios/ - список всех сценариев
    - POST /api/scenarios/ - создание нового сценария
    - GET /api/scenarios/{id}/ - получение сценария по ID
    - PUT /api/scenarios/{id}/ - обновление сценария
    - DELETE /api/scenarios/{id}/ - удаление сценария

    Дополнительные endpoints:
    - GET /api/scenarios/{id}/steps/ - получение шагов сценария
    - POST /api/scenarios/{id}/execute/ - запуск сценария
    - GET /api/scenarios/{id}/sessions/ - активные сессии сценария
    """

    queryset = Scenario.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return ScenarioListSerializer
        return ScenarioSerializer

    @action(detail=True, methods=["get"])
    def steps(self, request, pk=None):
        """Получение шагов сценария"""
        scenario = self.get_object()
        steps = scenario.steps.all().order_by("order")
        serializer = StepSerializer(steps, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def execute(self, request, pk=None):
        """
        Запуск сценария для пользователя
        POST /api/scenarios/{id}/execute/
        """
        scenario = self.get_object()

        # Добавляем scenario_id в данные запроса
        request_data = request.data.copy()
        request_data["scenario_id"] = scenario.id

        serializer = ScenarioExecutionSerializer(data=request_data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Получаем объекты
            bot = Bot.objects.get(id=serializer.validated_data["bot_id"])
            telegram_user = TelegramUser.objects.get(
                telegram_id=serializer.validated_data["telegram_user_id"]
            )
            context_data = serializer.validated_data.get("context_data", {})

            # Запускаем сценарий
            execution_service = ScenarioExecutionService()
            session = execution_service.start_scenario(
                bot=bot,
                telegram_user=telegram_user,
                scenario=scenario,
                context_data=context_data,
            )

            return Response(
                {
                    "success": True,
                    "message": "Сценарий запущен",
                    "session_id": session.id,
                    "current_step": (
                        session.current_step.name if session.current_step else None
                    ),
                }
            )

        except (Bot.DoesNotExist, TelegramUser.DoesNotExist) as e:
            return Response(
                {"error": "Объект не найден"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Ошибка при запуске сценария: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get"])
    def sessions(self, request, pk=None):
        """
        Получение активных сессий сценария
        GET /api/scenarios/{id}/sessions/
        """
        scenario = self.get_object()

        # Импортируем здесь, чтобы избежать циклических импортов
        from bots.models import UserScenarioSession
        from bots.serializers import UserScenarioSessionSerializer

        sessions = UserScenarioSession.objects.filter(
            scenario=scenario, is_active=True
        ).order_by("-last_activity")

        serializer = UserScenarioSessionSerializer(sessions, many=True)
        return Response(serializer.data)


class StepViewSet(viewsets.ModelViewSet):
    """
    CRUD операции:
    - GET /api/steps/ - список всех шагов
    - POST /api/steps/ - создание нового шага
    - GET /api/steps/{id}/ - получение шага по ID
    - PUT /api/steps/{id}/ - обновление шага
    - DELETE /api/steps/{id}/ - удаление шага

    Фильтрация по scenario_id через query параметр:
    - GET /api/steps/?scenario_id=1 - шаги конкретного сценария

    Дополнительные endpoints:
    - GET /api/steps/templates/ - шаблоны для разных типов шагов
    """

    queryset = Step.objects.all()

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return StepCreateUpdateSerializer
        return StepSerializer

    def get_queryset(self):
        queryset = Step.objects.all().order_by("scenario", "order")
        scenario_id = self.request.query_params.get("scenario_id", None)
        if scenario_id is not None:
            queryset = queryset.filter(scenario_id=scenario_id)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Если порядок не указан, ставим в конец
        if "order" not in request.data or request.data["order"] is None:
            scenario = serializer.validated_data["scenario"]
            last_step = scenario.steps.order_by("-order").first()
            next_order = (last_step.order + 1) if last_step else 1
            serializer.validated_data["order"] = next_order

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    @action(detail=False, methods=["get"])
    def templates(self, request):
        """
        Получение шаблонов для разных типов шагов
        GET /api/steps/templates/
        """
        step_types = [choice[0] for choice in Step.STEP_TYPES]
        templates = []

        for step_type in step_types:
            serializer = StepTemplateSerializer(step_type)
            templates.append(serializer.data)

        return Response(templates)
