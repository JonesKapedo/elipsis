"""Telegram bot entry point (aiogram).

Run with:

    python -m telegram_bot.bot

Lives inside the telegram_bot package rather than the repository root because
Vercel scans the root for app.py/index.py/server.py/main.py/wsgi.py/asgi.py
when detecting a FastAPI entrypoint -- a bot module at the root competes with
the web platform for that name.
"""
import os
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from telegram_bot.handlers import start_handler, answer_handler
from dotenv import load_dotenv

load_dotenv()
# ELIPSIS_* is the current name; TURBINEZ_* is still honoured so existing .env
# files keep working through the rebrand.
TOKEN = os.getenv("ELIPSIS_TELEGRAM_TOKEN") or os.getenv("TURBINEZ_TELEGRAM_TOKEN")
if not TOKEN:
    raise RuntimeError(
        "ELIPSIS_TELEGRAM_TOKEN is not set. Copy .env.example to .env "
        "and fill in your Telegram bot token."
    )
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

dp.message.register(start_handler, Command(commands=["start"]))
dp.message.register(answer_handler)

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
