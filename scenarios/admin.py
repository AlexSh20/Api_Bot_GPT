from django.contrib import admin
from .models import Scenario, Step
from .forms import ScenarioAdminForm


class StepInline(admin.TabularInline):
    model = Step
    extra = 0
    fields = ["name", "step_type", "order", "is_active"]
    readonly_fields = []


@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    form = ScenarioAdminForm
    list_display = ["name", "bot", "is_active", "created_at"]
    list_filter = ["is_active", "bot", "created_at"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [StepInline]

    fieldsets = (
        (
            "Основная информация",
            {"fields": ("name", "description", "bot", "is_active")},
        ),
        (
            "Данные сценария",
            {
                "fields": ("data",),
                "description": "JSON конфигурация сценария. Можно оставить пустым для автоматического заполнения.",
            },
        ),
        (
            "Системная информация",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def save_model(self, request, obj, form, change):
        """Переопределяем сохранение для установки базовых данных"""
        if not obj.data:
            obj.data = {
                "version": "1.0",
                "description": obj.description or "Базовый сценарий",
                "metadata": {"author": request.user.username, "created_via": "admin"},
            }
        super().save_model(request, obj, form, change)


@admin.register(Step)
class StepAdmin(admin.ModelAdmin):
    list_display = ["name", "scenario", "step_type", "order", "is_active"]
    list_filter = ["step_type", "is_active", "scenario"]
    search_fields = ["name", "scenario__name"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            "Основная информация",
            {"fields": ("scenario", "name", "step_type", "order", "is_active")},
        ),
        ("Данные шага", {"fields": ("data",), "description": "JSON конфигурация шага"}),
        (
            "Системная информация",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
