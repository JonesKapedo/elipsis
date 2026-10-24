"""Short-lived, single-use handoff tokens for external implementation partners."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from elipsis_api import models, security, services
from elipsis_api.services_marketplace import now_iso, parse_dt

HANDOFF_MINUTES = 15
DEFAULT_PARTNER_URL = "https://great-turbinez.vercel.app/from-elipsis"


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _secret() -> str:
    return os.getenv("ELIPSIS_HANDOFF_SECRET") or security._session_secret()


def partner_url() -> str:
    return os.getenv("ELIPSIS_PARTNER_HANDOFF_URL", DEFAULT_PARTNER_URL)


def fetch_secret() -> str:
    return (os.getenv("ELIPSIS_HANDOFF_FETCH_SECRET") or "").strip()


def _sign(payload: bytes) -> str:
    return _b64(hmac.new(_secret().encode(), payload, hashlib.sha256).digest())


def create_handoff(db: Session, req: models.PhysicalAssessmentRequest, user_id: int,
                   partner: str = "great_turbinez") -> tuple[str, models.MarketplaceHandoff]:
    jti = secrets.token_urlsafe(24)
    expires = (datetime.now(UTC).replace(tzinfo=None)
               + timedelta(minutes=HANDOFF_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
    row = models.MarketplaceHandoff(
        jti=jti, request_id=req.id, user_id=user_id, partner=partner,
        status="created", expires_at=expires, created_at=now_iso())
    db.add(row)
    db.flush()
    payload = json.dumps({
        "jti": jti, "request": req.id,
        "exp": int(datetime.strptime(expires, "%Y-%m-%d %H:%M:%S")
                   .replace(tzinfo=UTC).timestamp()),
    }, separators=(",", ":"), sort_keys=True).encode()
    token = f"{_b64(payload)}.{_sign(payload)}"
    from elipsis_api.services_ops import record_audit
    record_audit(db, action="marketplace.handoff_created",
                 organization_id=req.organization_id, assessment_id=req.assessment_id,
                 user_id=user_id, detail=f"request={req.id}; partner={partner}; handoff={row.id}")
    db.commit()
    return token, row


def _decode(token: str) -> dict | None:
    try:
        body, signature = token.split(".", 1)
        payload = _unb64(body)
        expected = _sign(payload)
        if not hmac.compare_digest(expected, signature):
            return None
        data = json.loads(payload.decode())
    except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if int(data.get("exp") or 0) < int(datetime.now(UTC).timestamp()):
        return None
    return data


def sanitized_payload(db: Session, req: models.PhysicalAssessmentRequest) -> dict:
    org = db.get(models.Organization, req.organization_id)
    assessment = db.get(models.Assessment, req.assessment_id) if req.assessment_id else None
    constraints = []
    if assessment is not None:
        try:
            _, result = services.compute(db, assessment.id)
            constraints = list((result or {}).get("top_opportunities") or [])[:3]
        except Exception:  # noqa: BLE001
            constraints = []
    snapshot = {}
    if req.summary_snapshot:
        try:
            snapshot = json.loads(req.summary_snapshot)
        except (TypeError, ValueError):
            snapshot = {}
    return {
        "company_name": org.name if org else None,
        "contact_name": (org.contact_name if org else None) or (
            db.get(models.User, org.user_id).name if org and org.user_id else None),
        "contact_email": (org.contact_email if org else None),
        "country": org.country if org else None,
        "city": org.city if org else None,
        "size_band": org.company_size if org else None,
        "index": snapshot.get("index") if snapshot else (assessment.readiness_index if assessment else None),
        "maturity_band": snapshot.get("band") if snapshot else (assessment.maturity_band if assessment else None),
        "top_constraints": constraints,
        "summary": req.description or req.message,
        "expectations": req.expectations,
        "specifications": req.specifications,
        "reference": f"ELP-{req.id}-{req.assessment_id or 0}",
        "expires_in_minutes": HANDOFF_MINUTES,
    }


def consume_handoff(db: Session, token: str) -> dict | None:
    data = _decode(token)
    if data is None:
        return None
    row = db.scalar(select(models.MarketplaceHandoff).where(
        models.MarketplaceHandoff.jti == data["jti"]))
    if row is None or row.used_at is not None or row.status != "created":
        return None
    if (parse_dt(row.expires_at) or datetime.min) < datetime.now(UTC).replace(tzinfo=None):
        row.status = "expired"
        db.commit()
        return None
    req = db.get(models.PhysicalAssessmentRequest, row.request_id)
    if req is None:
        return None
    row.used_at = now_iso()
    row.status = "consumed"
    payload = sanitized_payload(db, req)
    db.commit()
    return payload
