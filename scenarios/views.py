from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Scenario, Step
from .serializers import (
    ScenarioSerializer,
    ScenarioListSerializer,
    StepSerializer,
    StepCreateUpdateSerializer,
)


class ScenarioViewSet(viewsets.ModelViewSet):
    """
    CRUD операции:
    - GET /api/scenarios/ - список всех сценариев
    - POST /api/scenarios/ - создание нового сценария
    - GET /api/scenarios/{id}/ - получение сценария по ID
    - PUT /api/scenarios/{id}/ - обновление сценария
    - DELETE /api/scenarios/{id}/ - удаление сценария
    - GET /api/scenarios/{id}/steps/ - получение шагов сценария
    """

    queryset = Scenario.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return ScenarioListSerializer
        return ScenarioSerializer

    @action(detail=True, methods=["get"])
    def steps(self, request, pk=None):
        scenario = self.get_object()
        steps = scenario.steps.all()
        serializer = StepSerializer(steps, many=True)
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
    """

    queryset = Step.objects.all()

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return StepCreateUpdateSerializer
        return StepSerializer

    def get_queryset(self):
        queryset = Step.objects.all()
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
