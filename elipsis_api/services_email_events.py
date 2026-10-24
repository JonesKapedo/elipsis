"""Branded transactional email events for auth, marketplace, and billing."""

from __future__ import annotations

import html
import os
from typing import Any

from sqlalchemy.orm import Session

from elipsis_api import models, services_email

ALWAYS_SEND = {
    "welcome",
    "verify_email",
    "password_reset",
    "invite",
    "payment_receipt",
    "payment_failed",
    "subscription_cancelled",
}


def _public_url(path: str | None) -> str:
    if not path:
        return ""
    if path.startswith(("http://", "https://")):
        return path
    base = (os.getenv("ELIPSIS_PUBLIC_URL") or "https://elipsis.ai").rstrip("/")
    return f"{base}/{path.lstrip('/')}"


def _text(value: Any, fallback: str = "") -> str:
    return html.escape(str(value if value not in (None, "") else fallback))


def _rows(pairs: list[tuple[str, Any]]) -> str:
    cells = []
    for label, value in pairs:
        if value in (None, ""):
            continue
        cells.append(
            '<tr>'
            f'<td style="padding:8px 0;color:#6b7280;font-size:13px;width:38%;">{_text(label)}</td>'
            f'<td style="padding:8px 0;color:#10243e;font-size:14px;font-weight:600;">{_text(value)}</td>'
            '</tr>'
        )
    if not cells:
        return ""
    return '<table style="width:100%;border-collapse:collapse;margin:18px 0;">' + "".join(cells) + "</table>"


def _layout(*, title: str, intro: str, rows: str = "", cta_label: str = "",
            cta_url: str = "", note: str = "") -> str:
    button = ""
    if cta_label and cta_url:
        button = (
            f'<p style="margin:26px 0;"><a href="{_text(cta_url)}" '
            'style="background:#10243e;color:#ffffff;padding:12px 20px;border-radius:8px;'
            'text-decoration:none;display:inline-block;font-weight:600;">'
            f'{_text(cta_label)}</a></p>'
        )
    footer = f'<p style="color:#6b7280;font-size:13px;margin-top:22px;">{_text(note)}</p>' if note else ""
    return f'''<!doctype html>
<html><body style="margin:0;background:#f7f3ea;font-family:Arial,Helvetica,sans-serif;color:#10243e;">
<div style="max-width:620px;margin:0 auto;padding:28px 18px;">
  <div style="background:#10243e;color:#ffffff;padding:22px 24px;border-radius:16px 16px 0 0;">
    <div style="color:#d9b45b;font-size:12px;letter-spacing:2px;">ELIPSIS</div>
    <h1 style="margin:8px 0 0;font-size:24px;line-height:1.25;">{_text(title)}</h1>
  </div>
  <div style="background:#ffffff;padding:24px;border:1px solid #e8e0d2;border-top:0;border-radius:0 0 16px 16px;">
    <p style="font-size:15px;line-height:1.6;">{_text(intro)}</p>
    {rows}
    {button}
    {footer}
    <p style="color:#9ca3af;font-size:12px;margin-top:26px;border-top:1px solid #eee8dc;padding-top:14px;">
      Elipsis sends transactional messages about your account, workspace, and marketplace activity.
    </p>
  </div>
</div></body></html>'''


def render_event(event: str, **context) -> tuple[str, str, str]:
    name = context.get("name") or "there"
    url = _public_url(context.get("url"))
    rows = ""
    cta_label = "Open Elipsis"
    note = ""

    if event == "welcome":
        subject = "Welcome to Elipsis"
        title = f"Welcome aboard, {name}"
        intro = "Your account is ready. Verify your email address to secure it, then finish your workspace setup."
        rows = _rows([("Account type", context.get("user_type_label") or context.get("user_type"))])
        cta_label = "Verify email"
        note = "If a verification link expires, request a new one from the sign-in screen."
    elif event == "verify_email":
        subject = "Verify your Elipsis email"
        title = "Confirm your email address"
        intro = "Use the button below to verify your email and finish securing your Elipsis account."
        cta_label = "Verify email"
        note = "This link is unique to your account."
    elif event == "password_reset":
        subject = "Reset your Elipsis password"
        title = "Choose a new password"
        intro = "We received a request to reset your password. This link expires in one hour."
        cta_label = "Reset password"
        note = "If you did not request this, you can ignore this email."
    elif event == "workspace_added":
        subject = f"You were added to {context.get('org_name') or 'an Elipsis workspace'}"
        title = "You are on a new workspace"
        intro = (
            f"{context.get('inviter_name') or 'A workspace manager'} added you to "
            f"{context.get('org_name') or 'their company'} on Elipsis."
        )
        rows = _rows([
            ("Role", context.get("role_label") or context.get("role")),
            ("Title", context.get("title")),
            ("Department", context.get("department")),
        ])
        cta_label = "Open workspace"
    elif event == "invite":
        subject = f"You are invited to {context.get('org_name') or 'an Elipsis workspace'}"
        title = "Join your company workspace"
        intro = (
            f"{context.get('inviter_name') or 'A workspace manager'} invited you to "
            f"{context.get('org_name') or 'their company'} on Elipsis."
        )
        rows = _rows([
            ("Role", context.get("role_label") or context.get("role")),
            ("Title", context.get("title")),
            ("Department", context.get("department")),
            ("Expires", context.get("expires_at")),
        ])
        cta_label = "Accept invitation"
        note = context.get("note") or "This invitation is private to the recipient."
    elif event == "request_submitted":
        subject = "We received your implementation request"
        title = "Your request is in review"
        intro = "Elipsis will review the scope before publishing it to verified implementation partners."
        rows = _rows([("Request", context.get("request_title")), ("Reference", context.get("request_id"))])
        cta_label = "View request"
    elif event == "request_approved":
        subject = "Your request is live in the marketplace"
        title = "Your request is approved"
        intro = "Verified, subscribed partners can now review your request and submit proposals."
        rows = _rows([("Request", context.get("request_title"))])
        cta_label = "View request"
    elif event == "request_rejected":
        subject = "Your Elipsis request needs changes"
        title = "Your request needs changes"
        intro = "We could not publish this request yet. Review the note below, update the request, and resubmit."
        rows = _rows([("Request", context.get("request_title")), ("Reason", context.get("reason"))])
        cta_label = "Review request"
    elif event == "bid_submitted":
        subject = "Your proposal was submitted for review"
        title = "Proposal submitted"
        intro = "Elipsis will review your proposal before the client can see it. We will email you when it is approved."
        rows = _rows([
            ("Request", context.get("request_title")),
            ("Estimated cost", context.get("estimated_cost")),
            ("Timeline", context.get("timeline")),
        ])
        cta_label = "View your bid"
    elif event == "bid_approved":
        subject = "A new proposal is ready to review"
        title = "A partner submitted a proposal"
        intro = "An admin-approved implementation partner has submitted a proposal for your request."
        rows = _rows([("Request", context.get("request_title"))])
        cta_label = "Review proposal"
    elif event == "bid_rejected":
        subject = "Your proposal needs attention"
        title = "Your proposal was not approved"
        intro = "An Elipsis admin reviewed your proposal and it is not currently visible to the client."
        rows = _rows([("Request", context.get("request_title")), ("Reason", context.get("reason"))])
        cta_label = "Open marketplace"
    elif event == "request_awarded_client":
        subject = "Your implementation partner is confirmed"
        title = "Your partner is confirmed"
        intro = "The award is complete and your private implementation conversation is now open."
        rows = _rows([
            ("Request", context.get("request_title")),
            ("Partner", context.get("partner_name")),
        ])
        cta_label = "Open conversation"
    elif event == "request_awarded_bidder":
        subject = "You won an implementation request"
        title = "You are the selected partner"
        intro = "The client award is complete. Your private implementation conversation is now open."
        rows = _rows([
            ("Request", context.get("request_title")),
            ("Client", context.get("client_name")),
        ])
        cta_label = "Open conversation"
    elif event == "request_switched_old":
        subject = "The client selected another partner"
        title = "The award has changed"
        intro = "The client used a switch and selected another approved partner for this request."
        rows = _rows([("Request", context.get("request_title"))])
        cta_label = "View request"
    elif event == "request_switched_new":
        subject = "You are now the selected partner"
        title = "The award moved to your proposal"
        intro = "The client selected your proposal through a switch. Your private conversation is open."
        rows = _rows([("Request", context.get("request_title"))])
        cta_label = "Open conversation"
    elif event in {"bidder_approved", "bidder_rejected", "bidder_more_info"}:
        approved = event == "bidder_approved"
        subject = ("Your partner verification is approved" if approved
                   else "Your partner verification needs attention")
        title = ("Verification approved" if approved else "Verification update")
        intro = ("Your company can now subscribe and bid on marketplace requests."
                 if approved else "Review the note below and update your verification details.")
        rows = _rows([("Company", context.get("company_name")), ("Note", context.get("notes"))])
        cta_label = "Open partner console" if approved else "Update verification"
    elif event == "conversation_message":
        subject = f"New message about {context.get('request_title') or 'your request'}"
        title = "New implementation message"
        intro = f"{context.get('sender_name') or 'A participant'} sent a message in your private conversation."
        rows = _rows([
            ("Request", context.get("request_title")),
            ("Message", context.get("message")),
        ])
        cta_label = "Reply in Elipsis"
    elif event == "payment_receipt":
        subject = f"Payment received: {context.get('description') or 'Elipsis'}"
        title = "Payment received"
        intro = "Your payment was confirmed. The matching access has been applied to your account."
        rows = _rows([
            ("Item", context.get("description")),
            ("Amount", context.get("amount")),
            ("Reference", context.get("reference")),
        ])
        cta_label = "View account"
    elif event == "payment_failed":
        subject = "We could not process your subscription payment"
        title = "Subscription payment failed"
        intro = "Your subscription is in a short grace period. Update the payment method to avoid losing access."
        rows = _rows([
            ("Plan", context.get("plan")),
            ("Access until", context.get("grace_until")),
        ])
        cta_label = "Update billing"
    elif event == "subscription_cancelled":
        subject = "Your Elipsis subscription is ending"
        title = "Subscription ending"
        intro = "The subscription will not renew. You keep access until the end of the current period."
        rows = _rows([
            ("Plan", context.get("plan")),
            ("Access until", context.get("access_until")),
        ])
        cta_label = "View account"
    else:
        subject = context.get("subject") or "Elipsis update"
        title = context.get("title") or "Elipsis update"
        intro = context.get("intro") or "There is an update in your Elipsis workspace."
        rows = _rows(context.get("details") or [])

    body = _layout(
        title=title, intro=intro, rows=rows, cta_label=cta_label,
        cta_url=url, note=note,
    )
    text_lines = [title, "", intro, ""]
    if rows:
        text_lines.append(context.get("text_summary") or "Open Elipsis for the full details.")
        text_lines.append("")
    if url:
        text_lines.append(url)
    return subject, body, "\n".join(text_lines).strip()


def _allows(db: Session, user_id: int, event: str) -> bool:
    if event in ALWAYS_SEND:
        return True
    prefs = db.get(models.UserPref, user_id)
    return prefs is None or prefs.notify_email is None or bool(prefs.notify_email)


async def send_event(to_email: str, event: str, **context) -> bool:
    try:
        subject, body, text = render_event(event, **context)
        return await services_email.send_email(to_email, subject, body, text)
    except Exception as exc:  # noqa: BLE001
        print(f"[elipsis] Email event {event} failed: {exc}", flush=True)
        return False


def send_event_sync(to_email: str, event: str, **context) -> bool:
    try:
        subject, body, text = render_event(event, **context)
        return services_email.send_email_sync(to_email, subject, body, text)
    except Exception as exc:  # noqa: BLE001
        print(f"[elipsis] Email event {event} failed: {exc}", flush=True)
        return False


async def send_user_event(db: Session, user_id: int | None, event: str,
                          **context) -> bool:
    try:
        user = db.get(models.User, user_id) if user_id else None
        if user is None or not _allows(db, user.id, event):
            return False
        context.setdefault("name", user.name or "there")
        return await send_event(user.email, event, **context)
    except Exception as exc:  # noqa: BLE001
        print(f"[elipsis] Email event {event} skipped: {exc}", flush=True)
        return False


def send_user_event_sync(db: Session, user_id: int | None, event: str,
                         **context) -> bool:
    try:
        user = db.get(models.User, user_id) if user_id else None
        if user is None or not _allows(db, user.id, event):
            return False
        context.setdefault("name", user.name or "there")
        return send_event_sync(user.email, event, **context)
    except Exception as exc:  # noqa: BLE001
        print(f"[elipsis] Email event {event} skipped: {exc}", flush=True)
        return False
