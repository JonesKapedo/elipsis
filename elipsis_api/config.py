"""Configuration for the Elipsis API."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = PACKAGE_DIR / "templates"
STATIC_DIR = PACKAGE_DIR / "static"


def _sqlite_url():
    return f"sqlite:///{BASE_DIR / 'turbinez.db'}"


def resolve_database_url():
    """Prefer PostgreSQL when configured and its driver is present; else SQLite.

    The SQLite path points at the same file used by the offline stdlib server,
    so both transports read and write the same data.

    ELIPSIS_* is the current variable name; TURBINEZ_* remains accepted so an
    existing .env keeps working through the rebrand.
    """
    url = os.getenv("ELIPSIS_DATABASE_URL") or os.getenv("TURBINEZ_DATABASE_URL")
    url = url or _sqlite_url()
    if url.startswith("postgres"):
        try:
            import psycopg  # noqa: F401
        except ImportError:
            print("[elipsis] PostgreSQL configured but psycopg is not installed "
                  "-> falling back to SQLite", flush=True)
            return _sqlite_url()
    return url


def _setting(new_name: str, old_name: str, default: str = "") -> str:
    return os.getenv(new_name) or os.getenv(old_name) or default


DATABASE_URL = resolve_database_url()
HOST = _setting("ELIPSIS_HOST", "TURBINEZ_HOST", "127.0.0.1")
PORT = int(_setting("ELIPSIS_PORT", "TURBINEZ_PORT", "8001"))
SESSION_COOKIE = "elipsis_session"