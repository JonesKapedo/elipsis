"""Auth sessions, Supabase credential checks, segments, and answer save."""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from constants import SUBDOMAIN_PILLAR
from elipsis_api import models, security, supabase_auth
from elipsis_api.config import is_production
from elipsis_api.services_core import _now, answers_map, get_questions
from readiness import compute_live as _compute_live


def _normalise_email(email: str | None) -> str:
    return (email or "").strip().lower()


def _validate_identity(email: str, password: str) -> tuple[str, str]:
    address = _normalise_email(email)
    if not address or "@" not in address:
        raise ValueError("Please enter a valid email address.")
    if "." not in address.split("@", 1)[1]:
        raise ValueError("Please enter a valid email address with a domain.")
    if len(password or "") < 8:
        raise ValueError("Password must be at least 8 characters long.")
    return address, password


def _remote_id(remote: dict[str, Any]) -> str:
    value = str(remote.get("id") or "").strip()
    if not value:
        raise supabase_auth.SupabaseAuthError("Supabase Auth returned no user id.")
    return value


def _create_local_user(
    db: Session,
    email: str,
    *,
    password_hash: str,
    name: str | None = None,
    user_type: str = "client",
    supabase_id: str | None = None,
    email_verified: bool = True,
) -> models.User:
    user = models.User(
        email=email,
        name=name,
        role="client" if user_type == "client" else user_type,
        user_type=user_type,
        password_hash=password_hash,
        supabase_id=supabase_id,
        is_admin=user_type == "admin",
        email_verified=email_verified,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _legacy_authenticate(db: Session, email: str, password: str):
    user = db.scalar(select(models.User).where(models.User.email == email))
    if user and security.verify_password(password, user.password_hash):
        user.last_login = _now()
        db.commit()
        return user
    return None


def _link_supabase_user(
    db: Session,
    user: models.User,
    remote: dict[str, Any],
) -> None:
    user.supabase_id = _remote_id(remote)
    if not user.name:
        user.name = str((remote.get("user_metadata") or {}).get("name") or "")[:120] or None
    user.last_login = _now()
    db.commit()


def authenticate(db: Session, email: str, password: str):
    address = _normalise_email(email)
    if not address or "@" not in address:
        return None

    if not supabase_auth.is_configured():
        if is_production():
            raise supabase_auth.SupabaseConfigurationError(
                "Sign-in is not configured for production.")
        return _legacy_authenticate(db, address, password)

    user = db.scalar(select(models.User).where(models.User.email == address))
    if user is not None and not user.supabase_id and user.password_hash:
        if security.verify_password(password, user.password_hash):
            remote = supabase_auth.create_or_link_user(
                user.email,
                password,
                name=user.name,
                user_type=user.user_type or "client",
            )
            _link_supabase_user(db, user, remote)
            return user

    try:
        session = supabase_auth.sign_in(address, password)
    except supabase_auth.InvalidCredentials:
        return None

    remote = session["user"]
    remote_id = _remote_id(remote)
    if user is not None and user.supabase_id and user.supabase_id != remote_id:
        print(
            f"[elipsis] Supabase identity mismatch for {address}; refusing login",
            flush=True,
        )
        return None

    if user is None:
        metadata = remote.get("user_metadata") or {}
        user = _create_local_user(
            db,
            address,
            password_hash=security.hash_password(security.new_token()),
            name=str(metadata.get("name") or "")[:120] or None,
            supabase_id=remote_id,
            email_verified=bool(remote.get("email_confirmed_at")),
        )
    elif user.supabase_id is None:
        user.supabase_id = remote_id
    user.last_login = _now()
    db.commit()
    return user


def authenticate_resilient(db: Session, email: str, password: str):
    account = authenticate(db, email, password)
    if account is not None:
        return account
    if db.scalar(select(models.User)) is None:
        from elipsis_api.services import _seed_admin
        try:
            _seed_admin(db)
            db.commit()
        except Exception as exc:  # noqa: BLE001
            print(f"[elipsis] emergency admin seed failed: {exc}", flush=True)
            return None
        return authenticate(db, email, password)
    return None


def register_user(
    db: Session,
    email: str,
    password: str,
    name: str | None = None,
    user_type: str = "client",
    *,
    allow_bidder: bool = False,
):
    address, password = _validate_identity(email, password)
    display_name = (name or "").strip()[:120] or None
    if user_type not in ("client", "bidder"):
        user_type = "client"
    if user_type == "bidder" and not allow_bidder:
        raise ValueError(
            "Provider accounts are invitation-only while the marketplace is in closed pilot. "
            "Create a company account or contact us for an invitation."
        )

    existing = db.scalar(select(models.User).where(models.User.email == address))
    if existing is not None:
        raise ValueError("An account with this email already exists. Please sign in instead.")

    if not supabase_auth.is_configured():
        if is_production():
            raise supabase_auth.SupabaseConfigurationError(
                "Account creation is not configured for production.")
        return _create_local_user(
            db,
            address,
            password_hash=security.hash_password(password),
            name=display_name,
            user_type=user_type,
        )

    remote = supabase_auth.admin_create_user(
        address,
        password,
        name=display_name,
        user_type=user_type,
    )
    try:
        return _create_local_user(
            db,
            address,
            password_hash=security.hash_password(security.new_token()),
            name=display_name,
            user_type=user_type,
            supabase_id=_remote_id(remote),
        )
    except Exception:
        try:
            supabase_auth.admin_delete_user(_remote_id(remote))
        except supabase_auth.SupabaseAuthError as exc:
            print(f"[elipsis] could not roll back Supabase user: {exc}", flush=True)
        raise


def set_password(db: Session, user: models.User, password: str) -> None:
    if len(password or "") < 8:
        raise ValueError("Password must be at least 8 characters long.")

    if supabase_auth.is_configured():
        remote = supabase_auth.ensure_password(
            user.email,
            password,
            name=user.name,
            user_type=user.user_type or "client",
        )
        user.supabase_id = _remote_id(remote)
    elif is_production():
        raise supabase_auth.SupabaseConfigurationError(
            "Password changes are not configured for production.")

    user.password_hash = security.hash_password(password)
    user.reset_token = None
    user.reset_expires_at = None
    db.commit()


def change_password(
    db: Session,
    user: models.User,
    current_password: str,
    new_password: str,
) -> str:
    if len(new_password or "") < 8:
        return "short"

    if not supabase_auth.is_configured():
        if is_production():
            raise supabase_auth.SupabaseConfigurationError(
                "Password changes are not configured for production.")
        if not security.verify_password(current_password, user.password_hash):
            return "current"
        set_password(db, user, new_password)
        return "changed"

    if user.supabase_id:
        try:
            supabase_auth.sign_in(user.email, current_password)
        except supabase_auth.InvalidCredentials:
            return "current"
    elif not security.verify_password(current_password, user.password_hash):
        try:
            supabase_auth.sign_in(user.email, current_password)
        except supabase_auth.InvalidCredentials:
            return "current"

    set_password(db, user, new_password)
    return "changed"


def ensure_supabase_admin(db: Session) -> None:
    if not supabase_auth.is_configured():
        return
    email = _normalise_email(
        os.getenv("ELIPSIS_ADMIN_EMAIL") or "admin@elipsis.local")
    password = os.getenv("ELIPSIS_ADMIN_PASSWORD") or ""
    if not password:
        return
    user = db.scalar(select(models.User).where(models.User.email == email))
    if user is None or user.supabase_id:
        return
    try:
        remote = supabase_auth.create_or_link_user(
            user.email,
            password,
            name=user.name,
            user_type=user.user_type or "admin",
        )
        user.supabase_id = _remote_id(remote)
        db.commit()
        print(f"[elipsis] linked {email} to Supabase Auth", flush=True)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        print(f"[elipsis] Supabase admin link failed: {exc}", flush=True)


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
