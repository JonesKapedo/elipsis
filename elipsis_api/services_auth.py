"""Auth sessions, segments, live scoring, answer save."""

from __future__ import annotations

from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

from constants import SUBDOMAIN_PILLAR
from readiness import compute_live as _compute_live
from elipsis_api import models, security
from elipsis_api.services_core import answers_map, get_questions


def authenticate(db: Session, email: str, password: str):
    user = db.scalar(select(models.User).where(models.User.email == email.strip().lower()))
    if user and security.verify_password(password, user.password_hash):
        return user
    return None


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
        email=email, name=name, role="client",
        password_hash=security.hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_session(db: Session, user_id: int) -> str:
    from elipsis_api import session_auth
    return session_auth.issue_session(db, user_id)


def user_for_token(db: Session, token: str | None):
    from elipsis_api import session_auth
    return session_auth.resolve_user(db, token)


def delete_session(db: Session, token: str | None):
    from elipsis_api import session_auth
    session_auth.revoke_session(db, token)


def question_dicts(db: Session, assessment_id: int) -> list[dict[str, Any]]:
    assessment = db.get(models.Assessment, assessment_id)
    if assessment is None:
        return []
    questions = get_questions(db, assessment.questionnaire_id)
    return [dict(id=q.id, code=q.code, subdomain=q.subdomain, pillar=q.pillar,
                 weight=q.weight, evidence_required=bool(q.evidence_required))
            for q in questions]


def build_segments(db: Session, assessment_id: int) -> list[dict[str, Any]]:
    assessment = db.get(models.Assessment, assessment_id)
    if assessment is None:
        return []
    questions = get_questions(db, assessment.questionnaire_id)
    answers = answers_map(db, assessment_id)

    order, buckets = [], {}
    for q in questions:
        code = q.subdomain
        if code not in buckets:
            buckets[code] = []
            order.append(code)
        buckets[code].append(q)

    steps = []
    for index, code in enumerate(order, start=1):
        items = buckets[code]
        done = sum(1 for q in items
                   if answers.get(q.id) and answers[q.id].get("score") is not None)
        steps.append(dict(
            number=index,
            subdomain=code,
            pillar=SUBDOMAIN_PILLAR.get(code, ""),
            questions=items,
            answered=done,
            total=len(items),
            complete=done >= len(items) and len(items) > 0,
        ))
    return steps


def live_scores(db: Session, assessment_id: int, segment_code: str = ""):
    assessment = db.get(models.Assessment, assessment_id)
    if assessment is None:
        return None
    questions = question_dicts(db, assessment_id)
    answers = answers_map(db, assessment_id)
    return _compute_live(questions, answers, segment_code=segment_code or "")


def save_answers(db: Session, assessment_id: int, items):
    assessment = db.get(models.Assessment, assessment_id)
    if assessment is None:
        return
    for item in items:
        existing = db.scalar(select(models.Answer).where(
            models.Answer.assessment_id == assessment_id,
            models.Answer.question_id == item["question_id"]))
        if existing is None:
            db.add(models.Answer(
                assessment_id=assessment_id,
                question_id=item["question_id"],
                score=item["score"],
                evidence=item.get("evidence") or "none",
            ))
        else:
            existing.score = item["score"]
            existing.evidence = item.get("evidence") or existing.evidence or "none"
    db.commit()
