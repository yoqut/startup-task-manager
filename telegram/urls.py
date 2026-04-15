from django.urls import path

from .views import set_webhook
from .views import telegram_webhook

urlpatterns = [
    path('webhook/', telegram_webhook, name='telegram_webhook'),
    path("set/", set_webhook, name="set_webhook"),
]