"""Telegram bot entry point (aiogram).

Deliberately NOT named main.py: Vercel scans the repository root for
`app.py / index.py / server.py / main.py / wsgi.py / asgi.py` when detecting a
FastAPI entrypoint, and a root main.py that defines no `app` makes the web
deployment fail with "Found main.py but it does not define a top-level app
FastAPI instance". The FastAPI app lives in elipsis_api/main.py and is
declared via [tool.vercel] in pyproject.toml.
"""
import os
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from handlers import start_handler, answer_handler
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
