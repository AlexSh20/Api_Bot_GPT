from django import forms
from django.core.exceptions import ValidationError
import json
from .models import Scenario, Step


class ScenarioForm(forms.ModelForm):
    """Форма для редактирования сценариев"""

    class Meta:
        model = Scenario
        fields = "__all__"
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "data": forms.Textarea(
                attrs={
                    "rows": 10,
                    "class": "vLargeTextField",
                    "placeholder": "Введите JSON данные (необязательно)",
                }
            ),
        }
        help_texts = {
            "name": "Краткое название сценария",
            "description": "Подробное описание назначения сценария",
            "bot": "Выберите бота, к которому привязан сценарий",
            "data": "Дополнительные JSON данные для конфигурации сценария",
            "is_active": "Снимите галочку, чтобы временно отключить сценарий",
        }

    def clean_data(self):
        """Валидация JSON данных"""
        data = self.cleaned_data.get("data")
        if data:
            try:
                if isinstance(data, str):
                    json.loads(data)
            except json.JSONDecodeError as e:
                raise ValidationError(f"Некорректный JSON: {e}")
        return data


class StepForm(forms.ModelForm):
    """Форма для редактирования шагов"""

    # Шаблоны для разных типов шагов
    STEP_TEMPLATES = {
        "message": {
            "text": "Введите текст сообщения",
            "transitions": [{"condition": "always", "next_step_order": None}],
        },
        "gpt_request": {
            "prompt": "Введите промпт для GPT. Доступные переменные: {user_name}, {last_user_message}",
            "transitions": [{"condition": "user_responded", "next_step_order": None}],
        },
        "input": {
            "text": "Что вы хотите ввести?",
            "save_as": "user_input",
            "response": "Спасибо за ввод: {user_input}",
            "transitions": [{"condition": "user_responded", "next_step_order": None}],
        },
        "condition": {
            "conditions": [
                {
                    "field": "user_input",
                    "operator": "equals",
                    "value": "да",
                    "next_step_order": None,
                }
            ]
        },
        "end": {"message": "Сценарий завершен. Спасибо!"},
    }

    class Meta:
        model = Step
        fields = "__all__"
        widgets = {
            "data": forms.Textarea(
                attrs={
                    "rows": 15,
                    "class": "vLargeTextField",
                    "placeholder": "JSON данные шага будут заполнены автоматически при выборе типа",
                }
            ),
            "order": forms.NumberInput(attrs={"min": 1}),
        }
        help_texts = {
            "scenario": "Выберите сценарий, к которому относится этот шаг",
            "name": "Краткое название шага для удобства",
            "step_type": "Тип шага определяет его поведение",
            "data": "JSON данные с конфигурацией шага",
            "order": "Порядок выполнения шага в сценарии (начиная с 1)",
            "is_active": "Снимите галочку, чтобы временно отключить шаг",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Добавляем CSS классы для улучшения внешнего вида
        self.fields["step_type"].widget.attrs.update(
            {"onchange": "updateStepData(this.value)"}
        )

        # Если это новый шаг, устанавливаем порядок автоматически
        if not self.instance.pk and "scenario" in self.data:
            try:
                scenario_id = self.data["scenario"]
                scenario = Scenario.objects.get(id=scenario_id)
                last_step = scenario.steps.order_by("-order").first()
                next_order = (last_step.order + 1) if last_step else 1
                self.fields["order"].initial = next_order
            except (Scenario.DoesNotExist, ValueError):
                pass

    def clean_data(self):
        """Валидация данных шага"""
        data = self.cleaned_data.get("data")
        step_type = self.cleaned_data.get("step_type")

        if not data:
            # Если данные пустые, используем шаблон
            if step_type in self.STEP_TEMPLATES:
                return self.STEP_TEMPLATES[step_type]
            else:
                return {}

        # Валидируем JSON
        try:
            if isinstance(data, str):
                parsed_data = json.loads(data)
            else:
                parsed_data = data
        except json.JSONDecodeError as e:
            raise ValidationError(f"Некорректный JSON: {e}")

        # Валидируем структуру в зависимости от типа шага
        if step_type == "gpt_request":
            if "prompt" not in parsed_data:
                raise ValidationError(
                    'Для шага типа "gpt_request" обязательно поле "prompt"'
                )

        elif step_type == "message":
            if "text" not in parsed_data:
                raise ValidationError('Для шага типа "message" обязательно поле "text"')

        elif step_type == "input":
            if "text" not in parsed_data:
                raise ValidationError('Для шага типа "input" обязательно поле "text"')
            if "save_as" not in parsed_data:
                parsed_data["save_as"] = "user_input"

        return parsed_data

    def clean(self):
        """Общая валидация формы"""
        cleaned_data = super().clean()
        scenario = cleaned_data.get("scenario")
        order = cleaned_data.get("order")

        if scenario and order:
            # Проверяем уникальность порядка в рамках сценария
            existing_step = Step.objects.filter(scenario=scenario, order=order).exclude(
                pk=self.instance.pk if self.instance else None
            )

            if existing_step.exists():
                raise ValidationError(
                    {"order": f"Шаг с порядком {order} уже существует в этом сценарии"}
                )

        return cleaned_data


class StepInlineForm(forms.ModelForm):
    """Упрощенная форма для inline редактирования шагов"""

    class Meta:
        model = Step
        fields = ["order", "name", "step_type", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"size": 30}),
            "order": forms.NumberInput(attrs={"min": 1, "style": "width: 60px"}),
        }


class ScenarioAdminForm(forms.ModelForm):
    """Кастомная форма для сценария в админке"""

    class Meta:
        model = Scenario
        fields = "__all__"
        widgets = {
            "data": forms.Textarea(
                attrs={
                    "rows": 10,
                    "cols": 80,
                    "placeholder": 'Оставьте пустым для автоматического заполнения или введите JSON:\n{\n  "version": "1.0",\n  "description": "Описание сценария"\n}',
                }
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Делаем поле data необязательным в форме
        self.fields["data"].required = False
        self.fields["data"].help_text = (
            "JSON данные сценария. Можно оставить пустым - "
            "система автоматически создаст базовую структуру."
        )

    def clean_data(self):
        """Валидация поля data"""
        data = self.cleaned_data.get("data")

        # Если поле пустое, возвращаем пустой словарь
        if not data:
            return {}

        # Если это строка, пытаемся распарсить как JSON
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                raise forms.ValidationError(
                    "Некорректный JSON формат. Проверьте синтаксис."
                )

        # Проверяем, что это словарь
        if not isinstance(data, dict):
            raise forms.ValidationError(
                "Данные сценария должны быть JSON объектом (словарем)."
            )

        return data
