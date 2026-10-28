"""Security and production-safety regression tests."""

import uuid
from datetime import UTC

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def app_client():
    from elipsis_api.main import app
    with TestClient(app) as c:
        yield c


def _login(client, email="admin@elipsis.local", password="elipsis"):
    return client.post("/login", data={"email": email, "password": password},
                       follow_redirects=False)


def test_csrf_rejects_cross_site_post(app_client):
    r = app_client.post("/login", data={"email": "a@b.com", "password": "x"},
                        headers={"Origin": "https://evil.example"},
                        follow_redirects=False)
    assert r.status_code == 403
    assert r.json()["detail"] == "csrf_rejected"


def test_csrf_allows_same_origin(app_client):
    r = app_client.post("/login", data={"email": "nobody@example.com", "password": "wrong"},
                        headers={"Origin": "http://testserver"},
                        follow_redirects=False)
    assert r.status_code in (401, 429)


def test_security_headers_present(app_client):
    r = app_client.get("/")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"


def test_assessment_requires_auth(app_client):
    assert app_client.get("/api/v1/assessments/1").status_code == 401


def test_cross_tenant_assessment_hidden(app_client):
    admin = TestClient(app_client.app)
    _login(admin)
    created = admin.post("/api/v1/assessments", json={
        "organization": {"name": f"Tenant {uuid.uuid4().hex[:8]}", "employee_count": 10},
        "department": "Operations"})
    assert created.status_code == 201
    assessment_id = created.json()["id"]

    email = f"user-{uuid.uuid4().hex[:10]}@example.com"
    stranger = TestClient(app_client.app)
    registered = stranger.post("/api/v1/auth/register", json={
        "email": email, "password": "correct-horse-battery", "name": "Stranger"})
    assert registered.status_code == 200, registered.text
    assert stranger.get(f"/api/v1/assessments/{assessment_id}").status_code == 404


def test_logout_revokes_session(app_client):
    client = TestClient(app_client.app)
    assert _login(client).status_code == 303
    cookie = client.cookies.get("elipsis_session")
    assert cookie
    client.get("/logout")
    replay = TestClient(app_client.app)
    replay.cookies.set("elipsis_session", cookie)
    assert replay.get("/dashboard", follow_redirects=False).status_code == 303


def test_password_reset_revokes_sessions(app_client):
    from sqlalchemy import select

    from elipsis_api import models
    from elipsis_api.database import SessionLocal

    email = f"reset-{uuid.uuid4().hex[:10]}@example.com"
    client = TestClient(app_client.app)
    assert client.post("/api/v1/auth/register", json={
        "email": email, "password": "old-password-123", "name": "Reset"}).status_code == 200
    old_cookie = client.cookies.get("elipsis_session")

    with SessionLocal() as db:
        user = db.scalar(select(models.User).where(models.User.email == email))
        user.reset_token = "test-reset-token"
        from datetime import datetime, timedelta
        user.reset_expires_at = (
            datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1)
        ).isoformat(timespec="seconds")
        db.commit()

    reset = client.post("/reset-password", data={
        "token": "test-reset-token", "password": "new-password-456",
        "password2": "new-password-456"}, follow_redirects=False)
    assert reset.status_code == 303

    replay = TestClient(app_client.app)
    replay.cookies.set("elipsis_session", old_cookie)
    assert replay.get("/dashboard", follow_redirects=False).status_code == 303
    assert _login(TestClient(app_client.app), email, "new-password-456").status_code == 303


def test_marketplace_is_locked_while_coming_soon(app_client, monkeypatch):
    from elipsis_api.routers import marketplace as marketplace_api
    from elipsis_api.routers import marketplace_ui

    monkeypatch.setattr(marketplace_api, "MARKETPLACE_ENABLED", False)
    monkeypatch.setattr(marketplace_ui, "MARKETPLACE_ENABLED", False)
    email = f"poster-{uuid.uuid4().hex[:10]}@example.com"
    client = TestClient(app_client.app)
    assert client.post("/api/v1/auth/register", json={
        "email": email, "password": "poster-password", "name": "Poster"}).status_code == 200
    r = client.post("/api/v1/marketplace/requests", json={
        "title": "Automate finance close"})
    assert r.status_code == 503
    page = client.get("/marketplace")
    assert page.status_code == 200
    assert "private pilot" in page.text.lower()
    assert "closed" in page.text.lower()


def test_production_requires_a_durable_database_and_secret(monkeypatch):
    from elipsis_api import config, security

    monkeypatch.setenv("VERCEL", "1")
    for name in (
        "ELIPSIS_DATABASE_URL",
        "NEON_DATABASE_URL",
        "POSTGRES_URL",
        "POSTGRES_PRISMA_URL",
        "DATABASE_URL",
        "TURBINEZ_DATABASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(config, "CONFIG_ERRORS", [])
    with pytest.raises(config.DatabaseConfigurationError, match="No database"):
        config.resolve_database_url()

    monkeypatch.delenv("ELIPSIS_SECRET_KEY", raising=False)
    monkeypatch.delenv("TURBINEZ_SECRET_KEY", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setattr(security, "_DEV_SECRET", None)
    assert len(security._session_secret()) >= 32
    assert any("SECRET_KEY" in e for e in config.CONFIG_ERRORS)


def test_production_rejects_dummy_paystack(monkeypatch):
    from elipsis_api import paystack
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("PAYSTACK_SECRET_KEY", raising=False)
    monkeypatch.delenv("PAYSTACK_PUBLIC_KEY", raising=False)
    with pytest.raises(RuntimeError):
        paystack.ensure_configured()
