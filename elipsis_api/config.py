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
    """True when psycopg is installed and the database answers quickly."""
    try:
        import psycopg  # noqa: F401  # type: ignore[import-not-found]
    except ImportError:
        print(
            "[elipsis] PostgreSQL configured but psycopg is not installed",
            flush=True,
        )
        return False
    try:
        from sqlalchemy import create_engine, text

        timeout = int(os.getenv("ELIPSIS_DB_PROBE_TIMEOUT", "10"))
        probe = create_engine(
            url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": timeout},
        )
        try:
            with probe.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        finally:
            probe.dispose()
    except Exception as exc:  # noqa: BLE001
        detail = (
            str(exc).strip().splitlines()[0]
            if str(exc).strip()
            else exc.__class__.__name__
        )
        print(
            f"[elipsis] PostgreSQL configured but unreachable ({detail})",
            flush=True,
        )
        return False


def is_production() -> bool:
    return bool(os.getenv("VERCEL")) or os.getenv("ELIPSIS_ENV", "").lower() == "production"


class DatabaseConfigurationError(RuntimeError):
    """Raised when production has no durable database configured."""


CONFIG_ERRORS: list[str] = []


def _database_url_from_env() -> str:
    """First configured database URL, including common Vercel/Neon names."""
    names = [
        "ELIPSIS_DATABASE_URL",
        "NEON_DATABASE_URL",
        "POSTGRES_URL",
        "POSTGRES_PRISMA_URL",
        "TURBINEZ_DATABASE_URL",
    ]
    # Generic DATABASE_URL is common on Vercel/Neon but often stale in local
    # .env files, so only trust it in production.
    if is_production():
        names.insert(4, "DATABASE_URL")
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value
    return ""


def _sqlite_allowed_in_production() -> bool:
    return os.getenv("ELIPSIS_ALLOW_SQLITE_IN_PRODUCTION", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def resolve_database_url() -> str:
    """Resolve a durable database URL, failing closed in production.

    A serverless deployment must never write accounts into an ephemeral SQLite
    file. If production is missing a Postgres URL, raise so the operator sees a
    real deployment error instead of silently losing every sign-up on the next
    cold start.
    """
    url = _database_url_from_env().strip().strip('"').strip("'")
    if not url:
        if is_production() and not _sqlite_allowed_in_production():
            raise DatabaseConfigurationError(
                "No database configured. Set ELIPSIS_DATABASE_URL (or "
                "DATABASE_URL / POSTGRES_URL / NEON_DATABASE_URL) to a Neon "
                "PostgreSQL connection string."
            )
        return _sqlite_url()

    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]

    if url.startswith(("postgresql://", "postgresql+psycopg://")):
        return url

    if is_production() and not _sqlite_allowed_in_production():
        raise DatabaseConfigurationError(
            f"Production database URL must be PostgreSQL, got scheme "
            f"{url.split('://', 1)[0]!r}."
        )
    return url


def _setting(new_name: str, old_name: str, default: str = "") -> str:
    return os.getenv(new_name) or os.getenv(old_name) or default


DATABASE_URL = resolve_database_url()
HOST = _setting("ELIPSIS_HOST", "TURBINEZ_HOST", "127.0.0.1")
PORT = int(_setting("ELIPSIS_PORT", "TURBINEZ_PORT", "8001"))
SESSION_COOKIE = "elipsis_session"


def _upload_dir() -> Path:
    """Durable local upload directory, or a temp fallback on read-only hosts."""
    configured = (os.getenv("ELIPSIS_UPLOAD_DIR") or "").strip()
    if configured:
        return Path(configured).expanduser()
    base = BASE_DIR / "data" / "uploads"
    if _writable_dir(base):
        return base
    fallback = Path(tempfile.gettempdir()) / "elipsis" / "uploads"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


UPLOAD_DIR = _upload_dir()
MARKETPLACE_ENABLED = os.getenv("ELIPSIS_MARKETPLACE_ENABLED", "0").strip().lower() in {"1", "true", "yes"}

SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
SUPABASE_ANON_KEY = (os.getenv("SUPABASE_ANON_KEY") or "").strip()
SUPABASE_SERVICE_ROLE_KEY = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
SUPABASE_AUTH_CONFIGURED = bool(
    SUPABASE_URL and SUPABASE_ANON_KEY and SUPABASE_SERVICE_ROLE_KEY)
SUPABASE_AUTH_REQUIRED = is_production()
if SUPABASE_AUTH_REQUIRED and not SUPABASE_AUTH_CONFIGURED:
    CONFIG_ERRORS.append(
        "Supabase Auth is required in production. Set SUPABASE_URL, "
        "SUPABASE_ANON_KEY, and SUPABASE_SERVICE_ROLE_KEY."
    )


def _flag(name: str, default: str = "1") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


MESSAGING_ENABLED = _flag("ELIPSIS_MESSAGING_ENABLED")
BILLING_ENABLED = _flag("ELIPSIS_BILLING_ENABLED")
HANDOFF_ENABLED = _flag("ELIPSIS_HANDOFF_ENABLED")
VERIFICATION_ENABLED = _flag("ELIPSIS_VERIFICATION_ENABLED")
