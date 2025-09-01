from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BotViewSet,
    TelegramUserViewSet,
    ConversationViewSet,
    UserScenarioSessionViewSet,
)

router = DefaultRouter()
router.register(r"bots", BotViewSet)
router.register(r"telegram-users", TelegramUserViewSet)
router.register(r"conversations", ConversationViewSet)
router.register(r"scenario-sessions", UserScenarioSessionViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
