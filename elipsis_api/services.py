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
