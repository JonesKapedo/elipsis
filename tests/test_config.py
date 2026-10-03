"""Database URL resolution: SQLite default and PostgreSQL fallbacks.

The web platform must never fail to start because a stale database URL is
sitting in .env, so these cover the fallbacks rather than the happy path.
"""
import sys
import types

from elipsis_api import config


def test_sqlite_url_lives_beside_the_project():
    url = config._sqlite_url()
    assert url.startswith("sqlite:///")
    # Either the project directory or the /tmp fallback, never an empty path.
    assert url.endswith("turbinez.db")


def test_no_database_url_uses_sqlite(monkeypatch):
    monkeypatch.delenv("ELIPSIS_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURBINEZ_DATABASE_URL", raising=False)
    assert config.resolve_database_url().startswith("sqlite:///")


def test_unreachable_postgres_falls_back_instead_of_raising(monkeypatch):
    """A dead server must degrade to SQLite, not take the app down."""
    monkeypatch.setenv(
        "ELIPSIS_DATABASE_URL",
        "postgresql://nobody:nobody@127.0.0.1:59999/does_not_exist",
    )
    assert config.resolve_database_url().startswith("sqlite:///")


def test_missing_psycopg_falls_back(monkeypatch):
    """No driver installed must fall back rather than raise."""
    monkeypatch.setenv(
        "ELIPSIS_DATABASE_URL",
        "postgresql://nobody:nobody@127.0.0.1:5432/does_not_exist",
    )
    # Make `import psycopg` fail even if the driver is present in the env.
    monkeypatch.setitem(sys.modules, "psycopg", None)
    assert config.resolve_database_url().startswith("sqlite:///")


def test_broken_driver_does_not_propagate(monkeypatch):
    """A driver that imports but misbehaves must still fall back."""
    stub = types.ModuleType("psycopg")  # no paramstyle / no real driver
    monkeypatch.setitem(sys.modules, "psycopg", stub)
    assert config._postgres_usable("postgresql://nobody@127.0.0.1:59999/none") is False