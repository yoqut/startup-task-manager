from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import telegram_webhook, crm_webhook, ExternalIntegrationViewSet

router = DefaultRouter()
router.register("crm", ExternalIntegrationViewSet, basename="integrations-crm")

urlpatterns = [
    path("telegram/webhook/",                 telegram_webhook, name="telegram-webhook"),
    path("crm/<uuid:integration_id>/webhook/", crm_webhook,      name="crm-webhook"),
    path("",                                   include(router.urls)),
]
