"""
URL configuration for ApiBotGpt project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse


@api_view(["GET"])
def api_root(request, format=None):
    """
    Telegram GPT Bots API

    Добро пожаловать в API для управления Telegram ботами с GPT интеграцией!

    Основные возможности:
    - Создание и управление Telegram ботами
    - Интеграция с OpenAI GPT API
    - Управление пользователями Telegram
    - Создание сценариев для ботов
    """
    return Response(
        {
            "message": "Telegram GPT Bots API",
            "version": "1.0.0",
            "endpoints": {
                "admin": reverse("admin:index", request=request, format=format),
                "bots": request.build_absolute_uri("/api/bots/"),
                "telegram_users": request.build_absolute_uri("/api/telegram-users/"),
                "conversations": request.build_absolute_uri("/api/conversations/"),
                "scenarios": request.build_absolute_uri("/scenarios/scenarios/"),
                "steps": request.build_absolute_uri("/scenarios/steps/"),
            },
        }
    )


urlpatterns = [
    path("", api_root, name="api_root"),
    path("admin/", admin.site.urls),
    path("api/", include("bots.urls")),
    path("api/", include("scenarios.urls")),
]
