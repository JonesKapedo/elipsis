"""Re-score reminders for Constraint Report buyers.

The first nudge is due on day 75 so the report owner can re-run the diagnostic
before the 90-day plan window closes. Later cycles repeat every 90 days.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from elipsis_api import models, services_email

FIRST_DUE_DAY = 75
CYCLE_DAYS = 90


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _due_cycle(created: datetime, now: datetime) -> int | None:
    days = (now - created).days
    if days < FIRST_DUE_DAY:
        return None
    return 1 + (days - FIRST_DUE_DAY) // CYCLE_DAYS


def _base_url() -> str:
    return os.getenv("ELIPSIS_BASE_URL", "https://elipsis.ai").rstrip("/")


def _render(assessment_id: int, org_name: str | None, index: float | None) -> tuple[str, str, str]:
    base = _base_url()
    link = f"{base}/assessment/{assessment_id}/results"
    label = org_name or "your operation"
    score = f" Your last index was {index:.1f}." if isinstance(index, (int, float)) else ""
    subject = "Re-score your Constraint Report — free"
    html = (
        f'<div style="font-family:IBM Plex Sans,Arial,sans-serif;color:#0b1220;max-width:560px">'
        f'<p style="font-size:12px;letter-spacing:2px;color:#8a5a00">ELIPSIS</p>'
        f'<h1 style="font-size:24px;margin:8px 0 12px">The 90-day plan is nearly done.</h1>'
        f'<p>Your Constraint Report for {label} is due for a re-score.{score} '
        f'Re-run the diagnostic to see what moved and what is now the binding constraint.</p>'
        f'<p style="margin:24px 0"><a href="{link}" style="background:#0b1220;color:#fff;'
        f'padding:12px 18px;border-radius:7px;text-decoration:none">Re-score free</a></p>'
        f'<p style="color:#6b7280;font-size:13px">Re-scoring is free with the report you already bought. '
        f'Buying the report again is not required.</p></div>'
    )
    text = (
        f"The 90-day plan for {label} is nearly done.{score}\n"
        f"Re-score free: {link}\n"
        "Re-scoring is free with the report you already bought.\n"
    )
    return subject, html, text


def send_due_rescores(db: Session, now: datetime | None = None) -> dict:
    """Send every reminder that is due and not already recorded."""
    now = now or datetime.now(UTC)
    purchases = db.scalars(select(models.AssessmentPurchase).where(
        models.AssessmentPurchase.active.is_(True))).all()
    sent = 0
    skipped = 0
    for purchase in purchases:
        created = _parse(purchase.created_at)
        cycle = _due_cycle(created, now) if created else None
        if cycle is None:
            continue
        exists = db.scalar(select(models.RescoreReminder.id).where(
            models.RescoreReminder.assessment_id == purchase.assessment_id,
            models.RescoreReminder.cycle == cycle))
        if exists is not None:
            skipped += 1
            continue
        assessment = db.get(models.Assessment, purchase.assessment_id)
        user = db.get(models.User, purchase.user_id)
        if assessment is None or user is None or not user.email:
            continue
        org = (db.get(models.Organization, assessment.organization_id)
               if assessment.organization_id else None)
        subject, html, text = _render(
            assessment.id, getattr(org, "name", None), assessment.readiness_index)
        ok = services_email.send_email_sync(user.email, subject, html, text)
        if not ok:
            continue
        due_at = (created + timedelta(days=FIRST_DUE_DAY + (cycle - 1) * CYCLE_DAYS))
        db.add(models.RescoreReminder(
            user_id=user.id,
            assessment_id=assessment.id,
            cycle=cycle,
            due_at=due_at.isoformat(timespec="seconds"),
            sent_at=now.strftime("%Y-%m-%d %H:%M:%S"),
            status="sent",
        ))
        db.commit()
        sent += 1
    return {"sent": sent, "skipped": skipped, "checked": len(purchases)}
