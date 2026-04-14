from telegram.loader import bot
import telegram.handlers

if __name__ == "__main__":
    import asyncio
    asyncio.run(bot.infinity_polling(skip_pending=True))