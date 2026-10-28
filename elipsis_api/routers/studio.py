"""Company workspace, Pro features, settings, letters, physical bids, Paystack."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from elipsis_api import (
    departments,
    models,
    paystack,
    premium,
    services,
    services_auth,
    services_success,
    services_webhooks,
    supabase_auth,
)
from elipsis_api.config import BILLING_ENABLED
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user, login_redirect, templates
from elipsis_api.narrative import company_portrait

router = APIRouter()


def _prefs(db: Session, user) -> models.UserPref:
    row = db.get(models.UserPref, user.id)
    if row is None:
        row = models.UserPref(user_id=user.id, symbol=(user.name or user.email or "E")[:1].upper())
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _is_admin(user) -> bool:
    return services.is_admin(user)


def _owned_orgs(db: Session, user):
    return services.owned_orgs(db, user)


def _claim(db: Session, user_id: int, organization_id: int):
    services.claim_org(db, user_id, organization_id)


def _parse_staff(raw: str):
    raw = (raw or "").strip()
    return int(raw) if raw.isdigit() and int(raw) > 0 else None
