from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AgentConfigViewSet, AgentExecutionLogViewSet

router = DefaultRouter()
router.register(r"configs", AgentConfigViewSet, basename="agent-config")
router.register(r"logs", AgentExecutionLogViewSet, basename="agent-log")

urlpatterns = router.urls
