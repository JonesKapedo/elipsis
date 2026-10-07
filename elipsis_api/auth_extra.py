"""Self-service registration and login resilience helpers."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from elipsis_api import models, security
from elipsis_api.services import _seed_admin


def register_user(db: Session, email: str, password: str, name: str | None = None):
    email = (email or "").strip().lower()
    name = (name or "").strip()[:120] or None
    if not email or "@" not in email:
        raise ValueError("Enter a valid work email address.")
    if len(password or "") < 8:
        raise ValueError("Password must be at least 8 characters.")
    existing = db.scalar(select(models.User).where(models.User.email == email))
    if existing is not None:
        raise ValueError("An account with this email already exists. Sign in instead.")
    user = models.User(
        email=email,
        name=name,
        role="client",
        password_hash=security.hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_resilient(db: Session, email: str, password: str):
    """Authenticate; if the user table is empty, seed the admin once and retry."""
    email = (email or "").strip().lower()
    user = db.scalar(select(models.User).where(models.User.email == email))
    if user and security.verify_password(password, user.password_hash):
        return user
    if db.scalar(select(models.User)) is None:
        try:
            _seed_admin(db)
            db.commit()
            user = db.scalar(select(models.User).where(models.User.email == email))
            if user and security.verify_password(password, user.password_hash):
                return user
        except Exception as exc:  # noqa: BLE001
            print(f"[elipsis] emergency admin seed failed: {exc}", flush=True)
    return None
