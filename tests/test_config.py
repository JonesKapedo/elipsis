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


def test_generic_database_url_is_trusted_in_production(monkeypatch):
    _clear_db_env(monkeypatch)
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://nobody:nobody@127.0.0.1:5432/neondb",
    )
    assert config.resolve_database_url().startswith("postgresql://")


def _clear_plan_env(monkeypatch):
    for name in (
        "PAYSTACK_PLAN_PREMIUM_MONTHLY",
        "PAYSTACK_PLAN_PREMIUM_ANNUAL",
        "PAYSTACK_PLAN_BIDDER_MONTHLY",
        "PAYSTACK_PLAN_BIDDER_SIX_MONTHS",
        "PAYSTACK_PLAN_BIDDER_YEARLY",
    ):
        monkeypatch.delenv(name, raising=False)


def test_marketplace_readiness_reports_launch_gaps(monkeypatch):
    from elipsis_api import paystack

    monkeypatch.setattr(config, "MARKETPLACE_ENABLED", True)
    monkeypatch.setattr(config, "BILLING_ENABLED", True)
    monkeypatch.setattr(config, "VERIFICATION_ENABLED", True)
    monkeypatch.setattr(paystack, "is_dummy", lambda: True)
    _clear_plan_env(monkeypatch)

    readiness = config.marketplace_readiness()
    assert readiness["enabled"] is True
    assert readiness["payments_configured"] is False
    assert readiness["bidder_plans_configured"] is False
    assert readiness["launch_ready"] is False


def test_marketplace_readiness_true_when_payments_and_plans_exist(monkeypatch):
    from elipsis_api import paystack

    monkeypatch.setattr(config, "MARKETPLACE_ENABLED", True)
    monkeypatch.setattr(config, "BILLING_ENABLED", True)
    monkeypatch.setattr(config, "VERIFICATION_ENABLED", True)
    monkeypatch.setattr(paystack, "is_dummy", lambda: False)
    _clear_plan_env(monkeypatch)
    monkeypatch.setenv("PAYSTACK_PLAN_BIDDER_MONTHLY", "PLN_bidder_monthly")

    readiness = config.marketplace_readiness()
    assert readiness["payments_configured"] is True
    assert readiness["bidder_plans_configured"] is True
    assert readiness["launch_ready"] is True


def test_broken_driver_does_not_propagate(monkeypatch):
    """A driver that imports but misbehaves reports unusable instead of raising."""
    stub = types.ModuleType("psycopg")  # no paramstyle / no real driver
    monkeypatch.setitem(sys.modules, "psycopg", stub)
    assert config._postgres_usable("postgresql://nobody@127.0.0.1:59999/none") is False
