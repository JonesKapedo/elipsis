"""Service layer: seeding and the assessment lifecycle (SQLAlchemy + shared engine)."""

import os
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from constants import PILLAR_WEIGHTS, SUBDOMAIN_PILLAR
from elipsis_questions import QUESTIONS, QUESTIONNAIRE
from readiness import compute as _compute
from readiness import compute_live as _compute_live
from elipsis_api import models, security


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


DEFAULT_ADMIN_EMAIL = "admin@elipsis.local"
DEFAULT_ADMIN_PASSWORD = "elipsis"

DEMO_DEPARTMENTS = [
    ("Operations", 3),
    ("Finance", 2),
    ("Customer Service", 4),
]


def _seed_admin(db: Session):
    email = os.getenv("ELIPSIS_ADMIN_EMAIL") or DEFAULT_ADMIN_EMAIL
    password = os.getenv("ELIPSIS_ADMIN_PASSWORD") or DEFAULT_ADMIN_PASSWORD
    if password == DEFAULT_ADMIN_PASSWORD:
        print("[elipsis] WARNING: no ELIPSIS_ADMIN_PASSWORD set, so the first "
              "administrator uses the default password. Set ELIPSIS_ADMIN_EMAIL "
              "and ELIPSIS_ADMIN_PASSWORD before exposing this instance.",
              flush=True)
    db.add(models.User(email=email, name="Elipsis Admin", role="admin",
                       password_hash=security.hash_password(password)))


def seed(db: Session):
    bank = db.scalar(select(models.Questionnaire).where(
        models.Questionnaire.code == QUESTIONNAIRE["code"]))
    if bank is None:
        bank = models.Questionnaire(
            code=QUESTIONNAIRE["code"], name=QUESTIONNAIRE["name"],
            version=QUESTIONNAIRE["version"], department=QUESTIONNAIRE["department"],
            estimated_minutes=QUESTIONNAIRE["estimated_minutes"], active=1)
        db.add(bank)
        db.flush()
        for q in QUESTIONS:
            db.add(models.Question(
                questionnaire_id=bank.id, code=q["code"], text=q["text"],
                why=q.get("why"), pillar=q["pillar"], subdomain=q["subdomain"],
                position=q.get("position") or 0, weight=q.get("weight") or 1.0,
                evidence_required=1 if q.get("evidence_required") else 0))
        db.commit()
    if db.scalar(select(models.User)) is None:
        _seed_admin(db)
        db.commit()
    return bank


def get_bank(db: Session):
    return db.scalar(select(models.Questionnaire).where(
        models.Questionnaire.active == 1).order_by(models.Questionnaire.id))


def authenticate(db: Session, email: str, password: str):
    user = db.scalar(select(models.User).where(models.User.email == email.strip().lower()))
    if user and security.verify_password(password, user.password_hash):
        return user
    return None


def create_session(db: Session, user_id: int) -> str:
    token = security.new_token()
    db.add(models.Session(user_id=user_id, token=token))
    db.commit()
    return token


def delete_session(db: Session, token: str | None):
    if not token:
        return
    sess = db.scalar(select(models.Session).where(models.Session.token == token))
    if sess:
        db.delete(sess)
        db.commit()
