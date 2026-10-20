"""Configuration for the Elipsis API."""

import os
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = PACKAGE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:  # pragma: no cover
    pass


def _writable_dir(path: Path) -> bool:
    """True when `path` exists (or can be created) and accepts writes."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False
    return os.access(path, os.W_OK)


def _sqlite_url() -> str:
    """SQLite beside the project, or under /tmp when that is read-only."""
    if _writable_dir(BASE_DIR):
        return f"sqlite:///{BASE_DIR / 'turbinez.db'}"
    tmp_dir = Path(tempfile.gettempdir()) / "elipsis"
    try:
        tmp_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    print(
        "[elipsis] project directory is read-only (serverless deployment) "
        f"-> using ephemeral SQLite at {tmp_dir / 'turbinez.db'}. Data will "
        "NOT survive a cold start. Set ELIPSIS_DATABASE_URL to a PostgreSQL "
        "URL for durable storage.",
        flush=True,
    )
    return f"sqlite:///{tmp_dir / 'turbinez.db'}"


def _postgres_usable(url: str) -> bool:
    """True when psycopg is installed and the database answers within 3s."""
    try:
        import psycopg  # noqa: F401  # type: ignore[import-not-found]
    except ImportError:
        print(
            "[elipsis] PostgreSQL configured but psycopg is not installed "
            "-> falling back to SQLite",
            flush=True,
        )
        return False
    try:
        from sqlalchemy import create_engine, text

        probe = create_engine(
            url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 3},
        )
        with probe.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001
        detail = (
            str(exc).strip().splitlines()[0]
            if str(exc).strip()
            else exc.__class__.__name__
        )
        print(
            f"[elipsis] PostgreSQL configured but unreachable ({detail}) "
            "-> falling back to SQLite",
            flush=True,
        )
        return False


def is_production() -> bool:
    return bool(os.getenv("VERCEL")) or os.getenv("ELIPSIS_ENV", "").lower() == "production"


CONFIG_ERRORS: list[str] = []


def _degraded(reason: str) -> str:
    """Keep the public site online while making the misconfiguration loud.

    Production still refuses to *write* to a throwaway database silently: the
    health endpoint reports degraded, the server logs the error, and the
    operator must set a real PostgreSQL URL. We only fall back so a missing env
    var produces a readable site instead of an opaque FUNCTION_INVOCATION_FAILED.
    """
    message = (
        f"{reason} Running on ephemeral SQLite; data will NOT survive a cold "
        "start. Set ELIPSIS_DATABASE_URL to a reachable PostgreSQL URL."
    )
    if message not in CONFIG_ERRORS:
        CONFIG_ERRORS.append(message)
    print(f"[elipsis] DEGRADED: {message}", flush=True)
    return _sqlite_url()


def resolve_database_url() -> str:
    """Use Postgres when configured; degrade visibly instead of crashing."""
    url = os.getenv("ELIPSIS_DATABASE_URL") or os.getenv("TURBINEZ_DATABASE_URL")
    if not url:
        if is_production():
            return _degraded("ELIPSIS_DATABASE_URL is not set.")
        return _sqlite_url()
    url = url.strip().strip('"').strip("'")
    if url.startswith(("postgres://", "postgresql://")):
        if _postgres_usable(url):
            return url
        if is_production():
            return _degraded("ELIPSIS_DATABASE_URL is configured but unreachable.")
        print("[elipsis] development fallback: PostgreSQL unreachable -> SQLite",
              flush=True)
        return _sqlite_url()
    if is_production():
        return _degraded(
            "ELIPSIS_DATABASE_URL is not a PostgreSQL URL.")
    return url


def _setting(new_name: str, old_name: str, default: str = "") -> str:
    return os.getenv(new_name) or os.getenv(old_name) or default


DATABASE_URL = resolve_database_url()
HOST = _setting("ELIPSIS_HOST", "TURBINEZ_HOST", "127.0.0.1")
PORT = int(_setting("ELIPSIS_PORT", "TURBINEZ_PORT", "8001"))
SESSION_COOKIE = "elipsis_session"
MARKETPLACE_ENABLED = os.getenv("ELIPSIS_MARKETPLACE_ENABLED", "0").strip().lower() in {"1", "true", "yes"}
