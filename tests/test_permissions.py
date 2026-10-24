"""Core authorization helpers in the dedicated permissions module."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from elipsis_api import models, permissions
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


def _user(db, email: str, **values) -> models.User:
    user = models.User(email=email, name=email.split("@")[0],
                       password_hash="x", **values)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _org(db, name: str = "Acme Logistics") -> models.Organization:
    org = models.Organization(name=name)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def test_admin_detection_covers_role_flag_and_env_email(db, monkeypatch):
    monkeypatch.setenv("ELIPSIS_ADMIN_EMAIL", "owner@example.com")

    assert permissions.is_admin(None) is False
    assert permissions.is_admin(_user(db, "role@example.com", role="admin")) is True
    assert permissions.is_admin(_user(db, "flag@example.com", is_admin=True)) is True
    assert permissions.is_admin(_user(db, "owner@example.com")) is True
    assert permissions.is_admin(_user(db, "member@example.com")) is False
    assert permissions.is_super_admin(_user(db, "super@example.com", role="super_admin")) is True


def test_org_roles_and_membership_control_management(db):
    user = _user(db, "manager@example.com")
    org = _org(db)
    db.add(models.OrgOwner(user_id=user.id, organization_id=org.id,
                           role="manager", status="active"))
    db.commit()

    assert permissions.org_role(db, user, org.id) == "manager"
    assert permissions.can_manage_org(db, user, org.id) is True
    assert permissions.can_contribute_org(db, user, org.id) is True
    assert permissions.owned_org_ids(db, user) == [org.id]
    assert permissions.visible_org_ids(db, user) == [org.id]
    assert permissions.can_access_org(db, user, org.id) is True

    membership = db.query(models.OrgOwner).filter_by(user_id=user.id).one()
    membership.role = "viewer"
    db.commit()
    assert permissions.org_role(db, user, org.id) == "viewer"
    assert permissions.can_manage_org(db, user, org.id) is False
    assert permissions.can_contribute_org(db, user, org.id) is False


def test_inactive_membership_grants_nothing(db):
    user = _user(db, "suspended@example.com")
    org = _org(db)
    db.add(models.OrgOwner(user_id=user.id, organization_id=org.id,
                           role="owner", status="suspended"))
    db.commit()

    assert permissions.org_membership(db, user, org.id) is None
    assert permissions.org_role(db, user, org.id) == ""
    assert permissions.owned_org_ids(db, user) == []
    assert permissions.visible_org_ids(db, user) == []
    assert permissions.can_access_org(db, user, org.id) is False


def test_pro_access_comes_from_active_or_future_preference(db):
    user = _user(db, "pro@example.com")
    future = (datetime.now(UTC).replace(tzinfo=None) + timedelta(days=10)).isoformat(
        timespec="seconds")
    db.add(models.UserPref(user_id=user.id, pro_until=future))
    db.commit()
    assert permissions.is_pro_user(db, user) is True

    prefs = db.get(models.UserPref, user.id)
    prefs.pro_until = "active"
    db.commit()
    assert permissions.is_pro_user(db, user) is True

    prefs.pro_until = "2000-01-01 00:00:00"
    db.commit()
    assert permissions.is_pro_user(db, user) is False
