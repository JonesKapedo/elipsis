"""Telegram bot — a separate transport from the deployable web platform.

The bot shares only `constants` (brand strings) with the FastAPI app. Its
entry point, handlers and scoring live here so that nothing aiogram-related
sits at the repository root, which is the directory Vercel scans when it
looks for a FastAPI entrypoint.

Run it with:

    python -m telegram_bot.bot
"""
import os
import sys

# Put the repository root on sys.path so `constants` resolves when this
# package is run directly as `python telegram_bot/bot.py` as well as via -m.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)