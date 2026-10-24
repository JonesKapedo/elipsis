"""Authorization and entitlement checks shared across the application."""

from __future__ import annotations

import os
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from elipsis_api import models
from elipsis_api.services_core import DEFAULT_ADMIN_EMAIL

ADMIN_ROLES = {"admin", "super_admin"}

ROLE_LABELS = {
    "owner": "Owner",
    "manager": "Manager",
    "supervisor": "Supervisor",
    "analyst": "Analyst",
    "viewer": "Viewer",
}
ROLE_LEVELS = {"viewer": 1, "analyst": 2, "supervisor": 3, "manager": 4, "owner": 5}


def is_admin(user) -> bool:
    if user is None:
        return False
    if (getattr(user, "role", "") or "").lower() in ADMIN_ROLES:
        return True
    if getattr(user, "is_admin", False):
        return True
    admin_email = (os.getenv("ELIPSIS_ADMIN_EMAIL") or DEFAULT_ADMIN_EMAIL).lower()
    return (getattr(user, "email", "") or "").lower() == admin_email


def is_super_admin(user) -> bool:
    return bool(user is not None and
                (getattr(user, "role", "") or "").lower() == "super_admin")


def org_membership(db: Session, user, organization_id: int | None):
    if user is None or organization_id is None:
        return None
    row = db.scalar(select(models.OrgOwner).where(
        models.OrgOwner.user_id == user.id,
        models.OrgOwner.organization_id == organization_id))
    if row is None or (row.status or "active") != "active":
        return None
    return row


def org_role(db: Session, user, organization_id: int | None) -> str:
    if is_admin(user):
        return "owner"
    row = org_membership(db, user, organization_id)
    if row is None:
        return ""
    return row.role if row.role in ROLE_LABELS else "owner"


def can_manage_org(db: Session, user, organization_id: int | None) -> bool:
    return ROLE_LEVELS.get(org_role(db, user, organization_id), 0) >= 4


def can_contribute_org(db: Session, user, organization_id: int | None) -> bool:
    return ROLE_LEVELS.get(org_role(db, user, organization_id), 0) >= 2


def is_pro_user(db: Session, user) -> bool:
    if user is None:
        return False
    if is_admin(user):
        return True
    prefs = db.get(models.UserPref, user.id)
    if prefs is None or not prefs.pro_until:
        return False
    if prefs.pro_until == "active":
        return True
    try:
        return (datetime.fromisoformat(prefs.pro_until)
                >= datetime.now(UTC).replace(tzinfo=None))
    except ValueError:
        return False


def company_is_pro(db: Session, organization_id: int | None, actor=None) -> bool:
    if organization_id is None:
        return False
    if actor is not None and is_pro_user(db, actor):
        return True
    rows = db.scalars(select(models.OrgOwner).where(
        models.OrgOwner.organization_id == organization_id)).all()
    for row in rows:
        if (row.status or "active") != "active":
            continue
        member = db.get(models.User, row.user_id)
        if member is not None and is_pro_user(db, member):
            return True
    return False


def owned_org_ids(db: Session, user) -> list[int]:
    if user is None:
        return []
    rows = db.scalars(select(models.OrgOwner).where(
        models.OrgOwner.user_id == user.id)).all()
    return [row.organization_id for row in rows
            if (row.status or "active") == "active"]


def visible_org_ids(db: Session, user) -> list[int] | None:
    owned = owned_org_ids(db, user)
    if owned:
        return owned
    return None if is_admin(user) else []


def can_access_org(db: Session, user, organization_id: int | None) -> bool:
    if user is None or organization_id is None:
        return False
    if is_admin(user):
        return True
    return organization_id in owned_org_ids(db, user)
