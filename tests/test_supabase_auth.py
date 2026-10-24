"""Supabase Auth adapter and account-linking regressions."""

from __future__ import annotations

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from elipsis_api import models, security, services_auth, supabase_auth
from elipsis_api.database import Base


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def configured(monkeypatch):
    monkeypatch.setattr(supabase_auth, "is_configured", lambda: True)


def _response(status: int, payload: dict) -> httpx.Response:
    return httpx.Response(
        status,
        json=payload,
        request=httpx.Request("POST", "https://example.supabase.co/auth/v1/token"),
    )


def test_invalid_credentials_are_distinct(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.setattr(
        supabase_auth,
        "_request",
        lambda *args, **kwargs: _response(
            400, {"error_code": "invalid_credentials", "msg": "Invalid login credentials"}),
    )
    with pytest.raises(supabase_auth.InvalidCredentials):
        supabase_auth.sign_in("person@example.com", "wrong-password")


def test_signup_creates_supabase_user_then_local_link(db, configured, monkeypatch):
    monkeypatch.setattr(
        supabase_auth,
        "admin_create_user",
        lambda email, password, **kwargs: {"id": "supabase-1", "email": email},
    )
    user = services_auth.register_user(
        db, "new@example.com", "correct-horse", name="New Person")
    assert user.supabase_id == "supabase-1"
    assert user.email == "new@example.com"
    assert user.password_hash != "correct-horse"


def test_existing_local_password_migrates_on_login(db, configured, monkeypatch):
    user = models.User(
        email="legacy@example.com",
        name="Legacy",
        password_hash=security.hash_password("legacy-password"),
        user_type="client",
    )
    db.add(user)
    db.commit()
    calls = {}
    monkeypatch.setattr(
        supabase_auth,
        "create_or_link_user",
        lambda email, password, **kwargs: calls.update(email=email, password=password)
        or {"id": "supabase-2", "email": email},
    )
    signed_in = services_auth.authenticate(db, "legacy@example.com", "legacy-password")
    assert signed_in.id == user.id
    assert signed_in.supabase_id == "supabase-2"
    assert calls == {"email": "legacy@example.com", "password": "legacy-password"}


def test_remote_signin_links_existing_local_user(db, configured, monkeypatch):
    user = models.User(
        email="linked@example.com",
        password_hash=security.hash_password(security.new_token()),
        user_type="client",
    )
    db.add(user)
    db.commit()
    monkeypatch.setattr(
        supabase_auth,
        "sign_in",
        lambda email, password: {
            "user": {"id": "supabase-3", "email": email, "email_confirmed_at": "now"}
        },
    )
    signed_in = services_auth.authenticate(db, "linked@example.com", "correct-horse")
    assert signed_in.id == user.id
    assert signed_in.supabase_id == "supabase-3"


def test_wrong_password_does_not_link(db, configured, monkeypatch):
    user = models.User(
        email="wrong@example.com",
        password_hash=security.hash_password(security.new_token()),
        user_type="client",
    )
    db.add(user)
    db.commit()

    def rejected(email, password):
        raise supabase_auth.InvalidCredentials("no")

    monkeypatch.setattr(supabase_auth, "sign_in", rejected)
    assert services_auth.authenticate(db, "wrong@example.com", "bad") is None
    db.refresh(user)
    assert user.supabase_id is None


def test_production_refuses_local_password_fallback(db, monkeypatch):
    user = models.User(
        email="fallback@example.com",
        password_hash=security.hash_password("local-password"),
        user_type="client",
    )
    db.add(user)
    db.commit()
    monkeypatch.setattr(supabase_auth, "is_configured", lambda: False)
    monkeypatch.setattr(services_auth, "is_production", lambda: True)
    with pytest.raises(supabase_auth.SupabaseConfigurationError):
        services_auth.authenticate(db, "fallback@example.com", "local-password")


def test_set_password_updates_supabase_and_local_hash(db, configured, monkeypatch):
    user = models.User(
        email="password@example.com",
        password_hash="old",
        user_type="client",
    )
    db.add(user)
    db.commit()
    monkeypatch.setattr(
        supabase_auth,
        "ensure_password",
        lambda email, password, **kwargs: {"id": "supabase-4", "email": email},
    )
    services_auth.set_password(db, user, "new-password")
    assert user.supabase_id == "supabase-4"
    assert security.verify_password("new-password", user.password_hash)
