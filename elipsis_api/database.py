"""SQLAlchemy engine, session factory and declarative base."""

from __future__ import annotations

import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from elipsis_api.config import DATABASE_URL


def _build_engine(url: str):
    """Create an engine; only development may fall back to SQLite.

    Production must keep the configured Postgres engine even when the first
    connection fails. Falling back would send the next sign-up to an ephemeral
    file while the operator thinks the real database is in use.
    """
    from elipsis_api.config import (
        _postgres_usable,
        _sqlite_url,
        is_production,
    )

    is_sqlite = url.startswith("sqlite")
    connect_args: dict = {}
    engine_kwargs: dict = {"future": True, "pool_pre_ping": True}

    if is_sqlite:
        connect_args["check_same_thread"] = False
        connect_args["timeout"] = 15
    else:
        # Neon can need a few seconds to wake from scale-to-zero.
        connect_args["connect_timeout"] = int(
            os.getenv("ELIPSIS_DB_CONNECT_TIMEOUT", "10")
        )
        engine_kwargs["pool_recycle"] = 280
        engine_kwargs["pool_size"] = int(os.getenv("ELIPSIS_DB_POOL_SIZE", "5"))
        engine_kwargs["max_overflow"] = int(os.getenv("ELIPSIS_DB_MAX_OVERFLOW", "10"))
        engine_kwargs["pool_timeout"] = 10

    eng = create_engine(url, connect_args=connect_args, **engine_kwargs)
    if is_sqlite or is_production():
        return eng, url

    if _postgres_usable(url):
        return eng, url

    from elipsis_api.config import CONFIG_ERRORS

    message = (
        "PostgreSQL is unreachable in development; falling back to SQLite. "
        "Production will refuse this fallback."
    )
    CONFIG_ERRORS.append(message)
    print(f"[elipsis] {message}", flush=True)
    fallback = _sqlite_url()
    eng.dispose()
    fallback_engine = create_engine(
        fallback,
        connect_args={"check_same_thread": False, "timeout": 15},
        future=True,
        pool_pre_ping=True,
    )
    return fallback_engine, fallback


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
