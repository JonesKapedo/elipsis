"""Database URL resolution: local SQLite default and Neon/Postgres aliases."""
import sys
import types

import pytest

from elipsis_api import config

_DB_ENV = (
    "ELIPSIS_DATABASE_URL",
    "NEON_DATABASE_URL",
    "POSTGRES_URL",
    "POSTGRES_PRISMA_URL",
    "DATABASE_URL",
    "TURBINEZ_DATABASE_URL",
)


def _clear_db_env(monkeypatch):
    for name in _DB_ENV:
        monkeypatch.delenv(name, raising=False)


def test_sqlite_url_lives_beside_the_project():
    url = config._sqlite_url()
    assert url.startswith("sqlite:///")
    # Either the project directory or the /tmp fallback, never an empty path.
    assert url.endswith("turbinez.db")


def test_no_database_url_uses_sqlite_in_development(monkeypatch):
    _clear_db_env(monkeypatch)
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setenv("ELIPSIS_ENV", "development")
    assert config.resolve_database_url().startswith("sqlite:///")


def test_production_without_database_fails_closed(monkeypatch):
    _clear_db_env(monkeypatch)
    monkeypatch.setenv("VERCEL", "1")
    with pytest.raises(config.DatabaseConfigurationError, match="No database"):
        config.resolve_database_url()


def test_production_rejects_sqlite(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("ELIPSIS_DATABASE_URL", "sqlite:///tmp/account.db")
    with pytest.raises(config.DatabaseConfigurationError, match="PostgreSQL"):
        config.resolve_database_url()


def test_unreachable_postgres_is_not_probed_at_import(monkeypatch):
    """Resolution must not turn a waking Neon compute into ephemeral SQLite."""
    monkeypatch.setenv(
        "ELIPSIS_DATABASE_URL",
        "postgresql://nobody:nobody@127.0.0.1:59999/does_not_exist",
    )
    assert config.resolve_database_url().startswith("postgresql://")


def test_common_platform_database_aliases(monkeypatch):
    _clear_db_env(monkeypatch)
    monkeypatch.setenv(
        "NEON_DATABASE_URL",
        "postgres://nobody:nobody@127.0.0.1:5432/neondb",
    )
    assert config.resolve_database_url() == (
        "postgresql://nobody:nobody@127.0.0.1:5432/neondb"
    )


def test_broken_driver_does_not_propagate(monkeypatch):
    """A driver that imports but misbehaves reports unusable instead of raising."""
    stub = types.ModuleType("psycopg")  # no paramstyle / no real driver
    monkeypatch.setitem(sys.modules, "psycopg", stub)
    assert config._postgres_usable("postgresql://nobody@127.0.0.1:59999/none") is False
