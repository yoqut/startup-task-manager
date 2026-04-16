from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskViewSet, WorkflowViewSet

router = DefaultRouter()
router.register(r"tasks", TaskViewSet, basename="task")
router.register(r"workflows", WorkflowViewSet, basename="workflow")

urlpatterns = router.urls
