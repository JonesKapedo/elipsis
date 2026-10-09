"""Session issue / resolve using signed cookies (Vercel-safe)."""

from __future__ import annotations

import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from elipsis_api import models, security

DEFAULT_ADMIN_EMAIL = "admin@elipsis.local"


def issue_session(db: Session, user_id: int) -> str:
    """Return a signed session cookie value; best-effort DB row for audits."""
    token = security.sign_session(user_id)
    try:
        db.add(models.Session(user_id=user_id, token=token))
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        print(f"[elipsis] session row not stored (non-fatal): {exc}", flush=True)
    return token


def resolve_user(db: Session, token: str | None):
    if not token:
        return None

    user_id = security.verify_signed_session(token)
    if user_id is not None:
        user = db.get(models.User, user_id)
        if user is not None:
            return user
        # Ephemeral SQLite cold start may have wiped users — reseed admin once.
        if db.scalar(select(models.User)) is None:
            try:
                from elipsis_api.services import _seed_admin
                _seed_admin(db)
                db.commit()
            except Exception as exc:  # noqa: BLE001
                print(f"[elipsis] session reseed failed: {exc}", flush=True)
                return None
            user = db.get(models.User, user_id)
            if user is not None:
                return user
            email = (os.getenv("ELIPSIS_ADMIN_EMAIL") or DEFAULT_ADMIN_EMAIL).lower()
            return db.scalar(select(models.User).where(models.User.email == email))
        return None

    # Legacy opaque token stored in sessions table
    sess = db.scalar(select(models.Session).where(models.Session.token == token))
    if sess is None:
        return None
    return db.get(models.User, sess.user_id)


def revoke_session(db: Session, token: str | None) -> None:
    if not token:
        return
    try:
        sess = db.scalar(select(models.Session).where(models.Session.token == token))
        if sess:
            db.delete(sess)
            db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
