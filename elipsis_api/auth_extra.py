"""Compatibility wrappers for registration and resilient login."""

from sqlalchemy.orm import Session

from elipsis_api import services_auth


def register_user(db: Session, email: str, password: str, name: str | None = None,
                  user_type: str = "client"):
    return services_auth.register_user(db, email, password, name=name, user_type=user_type)


def authenticate_resilient(db: Session, email: str, password: str):
    return services_auth.authenticate_resilient(db, email, password)
