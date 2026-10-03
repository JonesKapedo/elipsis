"""Configuration for the Elipsis API."""

import os
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = PACKAGE_DIR / "templates"
STATIC_DIR = PACKAGE_DIR / "static"


def _writable_dir(path: Path) -> bool:
    """True when `path` exists (or can be created) and accepts writes."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False
    return os.access(path, os.W_OK)


def _sqlite_url() -> str:
    """SQLite beside the project, or under /tmp when that is read-only.

    Vercel mounts the deployment bundle read-only, so a database file cannot
    live beside the source there. Falling back to /tmp keeps the function
    bootable, but that storage is ephemeral and is discarded when the
    instance is recycled -- configure a real PostgreSQL URL for durability.
    """
    if _writable_dir(BASE_DIR):
        return f"sqlite:///{BASE_DIR / 'turbinez.db'}"
    tmp_dir = Path(tempfile.gettempdir()) / "elipsis"
    try:
        tmp_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    print("[elipsis] project directory is read-only (serverless deployment) "
          f"-> using ephemeral SQLite at {tmp_dir / 'turbinez.db'}. Data will "
          "NOT survive a cold start. Set ELIPSIS_DATABASE_URL to a PostgreSQL "
          "URL for durable storage.", flush=True)
    return f"sqlite:///{tmp_dir / 'turbinez.db'}"


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
            import psycopg  # noqa: F401  # type: ignore[import-not-found]
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