"""Executive digest rendering and delivery."""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta

from elipsis_api import models, services_email, services_ops


def _due(prefs, force: bool) -> bool:
    if force:
        return True
    frequency = (prefs.digest_frequency or "weekly").lower()
    if frequency == "off":
        return False
    if not prefs.digest_last_sent:
        return True
    try:
        last = datetime.fromisoformat(prefs.digest_last_sent.replace("Z", "")).date()
    except ValueError:
        return True
    gap = 1 if frequency == "daily" else 7
    return date.today() >= last + timedelta(days=gap)


def render_digest(user, notifications: list[dict], base_url: str = "") -> tuple[str, str, str]:
    name = getattr(user, "name", None) or getattr(user, "email", "there")
    base = (base_url or "https://elipsis.ai").rstrip("/")
    subject = f"Elipsis weekly pulse — {len(notifications)} item{'s' if len(notifications) != 1 else ''} need attention"
    rows = "".join(
        f'<tr><td style="padding:10px 12px;border-bottom:1px solid #e8e0d2;">'
        f'<a href="{base}{n.get("url", "/dashboard")}" style="color:#10243e;font-weight:600;text-decoration:none;">'
        f'{n.get("title", "Workspace item")}</a><br>'
        f'<span style="color:#6b7280;font-size:13px;">{n.get("detail", "")}</span></td></tr>'
        for n in notifications
    ) or '<tr><td style="padding:12px;color:#6b7280;">No overdue actions or reviews. Keep the cadence.</td></tr>'
    html = f'''<html><body style="margin:0;background:#f7f3ea;font-family:Arial,sans-serif;color:#10243e;">
<div style="max-width:620px;margin:0 auto;padding:28px 18px;">
  <div style="background:#10243e;color:#fff;padding:22px 24px;border-radius:16px 16px 0 0;">
    <div style="color:#d9b45b;font-size:12px;letter-spacing:2px;">ELIPSIS</div>
    <h1 style="margin:8px 0 0;font-size:24px;">Your operating pulse</h1>
  </div>
  <div style="background:#fff;padding:22px 24px;border:1px solid #e8e0d2;border-top:0;border-radius:0 0 16px 16px;">
    <p>Hi {name},</p>
    <p>Here is what needs attention across your workspace.</p>
    <table style="width:100%;border-collapse:collapse;">{rows}</table>
    <p style="margin-top:22px;"><a href="{base}/actions" style="background:#10243e;color:#fff;padding:11px 18px;border-radius:8px;text-decoration:none;">Open action board</a></p>
    <p style="color:#9ca3af;font-size:12px;margin-top:24px;">You are receiving this because your Elipsis digest is on. Change it in Notifications.</p>
  </div>
</div></body></html>'''
    text = f"Elipsis pulse for {name}\n\n" + "\n".join(
        f"- {n.get('title')}: {n.get('detail')} ({base}{n.get('url', '/dashboard')})"
        for n in notifications) + f"\n\nOpen: {base}/actions\n"
    return subject, html, text


async def send_digest(db, user, base_url: str = "", force: bool = False) -> dict:
    prefs = db.get(models.UserPref, user.id)
    if prefs is None:
        prefs = models.UserPref(user_id=user.id, digest_frequency="weekly")
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    if not _due(prefs, force):
        return {"sent": False, "reason": "not_due"}
    notes = services_ops.notifications(db, user)
    for note in notes:
        note["fingerprint"] = services_ops.notification_fingerprint(note)
    subject, html, text = render_digest(user, notes, base_url)
    sent = await services_email.send_email(user.email, subject, html, text)
    if sent:
        prefs.digest_last_sent = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        db.commit()
    return {"sent": bool(sent), "reason": "sent" if sent else "email_not_configured",
            "count": len(notes)}


def run_due_digests(base_url: str = "https://elipsis.ai") -> int:
    from elipsis_api.database import SessionLocal
    db = SessionLocal()
    sent = 0
    try:
        rows = list(db.scalars(models.UserPref))
        for prefs in rows:
            if (prefs.digest_frequency or "weekly").lower() == "off":
                continue
            user = db.get(models.User, prefs.user_id)
            if user is None:
                continue
            result = asyncio.run(send_digest(db, user, base_url))
            if result.get("sent"):
                sent += 1
    finally:
        db.close()
    return sent


if __name__ == "__main__":
    print(run_due_digests())
