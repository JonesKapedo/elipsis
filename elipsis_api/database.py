"""SQLAlchemy engine, session factory and declarative base."""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from elipsis_api.config import DATABASE_URL

_is_sqlite = DATABASE_URL.startswith("sqlite")
_connect_args: dict = {}
_engine_kwargs: dict = {"future": True, "pool_pre_ping": True}

if _is_sqlite:
    # check_same_thread is required for SQLite under concurrent ASGI workers.
    _connect_args["check_same_thread"] = False
    # timeout reduces "database is locked" noise on serverless cold starts.
    _connect_args["timeout"] = 15
else:
    # Recycle connections before most PaaS idle timeouts (Neon, Supabase, etc.).
    _engine_kwargs["pool_recycle"] = 280
    _engine_kwargs["pool_size"] = 2
    _engine_kwargs["max_overflow"] = 2

engine = create_engine(DATABASE_URL, connect_args=_connect_args, **_engine_kwargs)
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
