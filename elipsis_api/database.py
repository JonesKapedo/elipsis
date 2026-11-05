"""SQLAlchemy engine, session factory and declarative base."""

from __future__ import annotations

import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.schema import CreateIndex

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


def _default_sql(column) -> str | None:
    if column.server_default is None:
        return None
    arg = column.server_default.arg
    if isinstance(arg, str):
        return arg
    text_sql = getattr(arg, "text", None)
    return text_sql if text_sql is not None else str(arg)


def ensure_schema_compatibility(bind=None) -> list[str]:
    """Apply additive schema repairs for databases predating newer columns.

    The app creates new tables with ``create_all`` at startup, but that does not
    add columns to existing tables. Production deployments do not always run
    Alembic before the web process, so an older database would otherwise break
    login with ``no such column: users.supabase_id``. Only nullable or
    defaulted columns are added; destructive changes are left to migrations.
    """
    from elipsis_api import models  # noqa: F401  (populate Base.metadata)

    target = bind or engine
    inspector = inspect(target)
    preparer = target.dialect.identifier_preparer
    applied: list[str] = []

    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue
        existing = {col["name"] for col in inspector.get_columns(table.name)}
        table_sql = preparer.format_table(table)
        for column in table.columns:
            if column.name in existing:
                continue
            default_sql = _default_sql(column)
            if not column.nullable and default_sql is None:
                print(
                    f"[elipsis] schema repair skipped non-nullable "
                    f"{table.name}.{column.name}",
                    flush=True,
                )
                continue
            type_sql = column.type.compile(dialect=target.dialect)
            ddl = (
                f"ALTER TABLE {table_sql} ADD COLUMN "
                f"{preparer.quote(column.name)} {type_sql}"
            )
            if default_sql is not None:
                ddl += f" DEFAULT {default_sql}"
            try:
                with target.begin() as conn:
                    conn.execute(text(ddl))
            except Exception as exc:  # noqa: BLE001
                print(
                    f"[elipsis] schema repair failed for "
                    f"{table.name}.{column.name}: {exc}",
                    flush=True,
                )
                continue
            existing.add(column.name)
            applied.append(f"{table.name}.{column.name}")

        index_names = {
            index["name"] for index in inspector.get_indexes(table.name)
            if index.get("name")
        }
        for index in table.indexes:
            if not index.name or index.name in index_names:
                continue
            try:
                with target.begin() as conn:
                    conn.execute(CreateIndex(index))
            except Exception as exc:  # noqa: BLE001
                print(
                    f"[elipsis] schema repair failed for index "
                    f"{index.name}: {exc}",
                    flush=True,
                )
                continue
            applied.append(f"index:{index.name}")

    return applied


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
