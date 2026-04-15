from telegram.loader import bot
import telegram.handlers

if __name__ == "__main__":
    import asyncio
    try:
        print("Starting bot...")
        asyncio.run(bot.infinity_polling(skip_pending=True))
    except KeyboardInterrupt:
        print("Stopping bot...")