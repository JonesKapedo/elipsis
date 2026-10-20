"""Session issue / resolve using signed cookies backed by the sessions table."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from elipsis_api import models, security

SESSION_TTL = timedelta(days=14)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def issue_session(db: Session, user_id: int) -> str:
    """Create a server-side session row and return its signed cookie value."""
    expires = (_utcnow() + SESSION_TTL).isoformat(timespec="seconds")
    token = security.sign_session(user_id)
    db.execute(delete(models.Session).where(
        models.Session.expires_at.is_not(None),
        models.Session.expires_at < _utcnow().isoformat(timespec="seconds"),
    ))
    db.add(models.Session(user_id=user_id, token=token, expires_at=expires))
    db.commit()
    return token


def resolve_user(db: Session, token: str | None):
    if not token:
        return None

    sess = db.scalar(select(models.Session).where(models.Session.token == token))
    if sess is None or sess.is_expired:
        if sess is not None:
            db.delete(sess)
            db.commit()
        return None

    user_id = security.verify_signed_session(token)
    if user_id is not None and user_id != sess.user_id:
        return None
    if user_id is None:
        user_id = sess.user_id
    return db.get(models.User, user_id)


def revoke_session(db: Session, token: str | None) -> None:
    if not token:
        return
    db.execute(delete(models.Session).where(models.Session.token == token))
    db.commit()


def revoke_user_sessions(db: Session, user_id: int, keep: str | None = None) -> None:
    stmt = delete(models.Session).where(models.Session.user_id == user_id)
    if keep:
        stmt = stmt.where(models.Session.token != keep)
    db.execute(stmt)
    db.commit()
