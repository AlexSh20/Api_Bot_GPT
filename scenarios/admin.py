from django.contrib import admin
from .models import Scenario, Step


class StepInline(admin.TabularInline):
    model = Step
    extra = 0
    fields = ["name", "step_type", "order", "is_active"]
    ordering = ["order"]


@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "created_at", "updated_at", "steps_count"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [StepInline]

    def steps_count(self, obj):
        return obj.steps.count()

    steps_count.short_description = "Количество шагов"


@admin.register(Step)
class StepAdmin(admin.ModelAdmin):
    list_display = ["name", "scenario", "step_type", "order", "is_active", "created_at"]
    list_filter = ["scenario", "step_type", "is_active", "created_at"]
    search_fields = ["name", "scenario__name"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["scenario", "order"]
