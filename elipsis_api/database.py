"""SQLAlchemy engine, session factory and declarative base."""

from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from elipsis_api.config import DATABASE_URL


def _build_engine(url: str):
    """Create an engine; never raise — fall back to ephemeral SQLite."""
    is_sqlite = url.startswith("sqlite")
    connect_args: dict = {}
    engine_kwargs: dict = {"future": True, "pool_pre_ping": True}

    if is_sqlite:
        connect_args["check_same_thread"] = False
        connect_args["timeout"] = 15
    else:
        # Fail fast on serverless — never hang cold start waiting for Neon.
        connect_args["connect_timeout"] = 5
        engine_kwargs["pool_recycle"] = 280
        engine_kwargs["pool_size"] = 1
        engine_kwargs["max_overflow"] = 0
        engine_kwargs["pool_timeout"] = 5

    try:
        eng = create_engine(url, connect_args=connect_args, **engine_kwargs)
        # Quick connectivity check for non-sqlite so we fall back early.
        if not is_sqlite:
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
        return eng, url
    except Exception as exc:  # noqa: BLE001
        print(
            f"[elipsis] engine init failed ({exc.__class__.__name__}: {exc}) "
            "-> falling back to ephemeral SQLite",
            flush=True,
        )
        from elipsis_api.config import _sqlite_url

        fallback = _sqlite_url()
        eng = create_engine(
            fallback,
            connect_args={"check_same_thread": False, "timeout": 15},
            future=True,
            pool_pre_ping=True,
        )
        return eng, fallback


engine, ACTIVE_DATABASE_URL = _build_engine(DATABASE_URL)
# Keep config.DATABASE_URL aligned for health endpoints
try:
    import elipsis_api.config as _cfg

    _cfg.DATABASE_URL = ACTIVE_DATABASE_URL
except Exception:
    pass

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """Declarative base for all Elipsis ORM models."""


def get_db():
    """FastAPI dependency yielding a database session with safe cleanup."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def ping_db() -> bool:
    """True when the database accepts a simple query."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001
        return False
