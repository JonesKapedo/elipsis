"""Configuration for the Elipsis API."""

import os
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = PACKAGE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# The web platform used to ignore .env entirely -- only the Telegram bot loaded
# it -- so the documented `cp .env.example .env` step silently did nothing here.
# load_dotenv never overrides variables already exported in the real
# environment, which is what Vercel and `env VAR=... run_api.py` rely on.
try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:  # pragma: no cover - python-dotenv is an optional extra
    pass


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


def _postgres_usable(url: str) -> bool:
    """True when psycopg is installed *and* the database actually answers.

    Checking only the import was not enough. With the driver present but no
    server listening, the first query would raise and take the whole app down
    at startup. Probing here turns a stale URL in .env into a warning and a
    SQLite fallback instead of an outage.
    """
    try:
        import psycopg  # noqa: F401  # type: ignore[import-not-found]
    except ImportError:
        print("[elipsis] PostgreSQL configured but psycopg is not installed "
              "-> falling back to SQLite", flush=True)
        return False
    try:
        from sqlalchemy import create_engine

        probe = create_engine(url, pool_pre_ping=True,
                              connect_args={"connect_timeout": 5})
        with probe.connect():
            return True
    except Exception as exc:  # noqa: BLE001 - any failure means "unusable"
        detail = str(exc).strip().splitlines()[0] if str(exc).strip() else exc.__class__.__name__
        print(f"[elipsis] PostgreSQL configured but unreachable ({detail}) "
              "-> falling back to SQLite", flush=True)
        return False


def resolve_database_url() -> str:
    """Prefer PostgreSQL when configured and reachable; else SQLite.

    The SQLite path points at the same file used by the offline stdlib server,
    so both transports read and write the same data.

    ELIPSIS_* is the current variable name; TURBINEZ_* remains accepted so an
    existing .env keeps working through the rebrand.
    """
    url = os.getenv("ELIPSIS_DATABASE_URL") or os.getenv("TURBINEZ_DATABASE_URL")
    url = url or _sqlite_url()
    if url.startswith("postgres") and not _postgres_usable(url):
        return _sqlite_url()
    return url


def _setting(new_name: str, old_name: str, default: str = "") -> str:
    return os.getenv(new_name) or os.getenv(old_name) or default


DATABASE_URL = resolve_database_url()
HOST = _setting("ELIPSIS_HOST", "TURBINEZ_HOST", "127.0.0.1")
PORT = int(_setting("ELIPSIS_PORT", "TURBINEZ_PORT", "8001"))
SESSION_COOKIE = "elipsis_session"
