import json
import logging

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from telebot.types import Update

from core.config import settings
from .loader import bot


logger = logging.getLogger(__name__)

@csrf_exempt
async def telegram_webhook(request):
    from . import handlers
    try:
        if request.method == "POST":
            update = Update.de_json(json.loads(request.body))
            print(update.callback_query.data if update.callback_query else update.message.text)
            await bot.process_new_updates([update])

        return HttpResponse("ok", status=200)

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return HttpResponse(status=500)

    finally:
        try:
            await bot.close_session()
        except Exception as ex:
            logger.error(f"Webhook close error: {ex}")

@csrf_exempt
async def set_webhook(request):
    try:
        if request.method == "GET":
            await bot.delete_webhook()
            await bot.set_webhook(url="https://" + settings.webhook_url + "/bots/webhook/")
            info = await bot.get_webhook_info()
            return JsonResponse(vars(info), status=200)

    except Exception as ex:
        logger.error(f"Webhook error: {ex}")
        return HttpResponse(status=500)

    finally:
        await bot.close_session()

