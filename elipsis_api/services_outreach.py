"""Low-friction distribution: WhatsApp, SMS, and invite copy."""

from __future__ import annotations

from urllib.parse import quote


def normalize_phone(raw: str | None, default_country: str = "254") -> str:
    digits = "".join(ch for ch in (raw or "") if ch.isdigit())
    if not digits:
        return ""
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("0") and len(digits) >= 9:
        digits = default_country + digits[1:]
    if len(digits) == 9 and default_country == "254":
        digits = default_country + digits
    return digits[:15]


def whatsapp_url(phone: str | None, text: str) -> str:
    digits = normalize_phone(phone)
    return f"https://wa.me/{digits}?text={quote(text)}" if digits else f"https://wa.me/?text={quote(text)}"


def sms_url(phone: str | None, text: str) -> str:
    digits = normalize_phone(phone)
    return f"sms:{digits}?body={quote(text)}" if digits else f"sms:?body={quote(text)}"


def assessment_invite_message(organization, assessment, url: str,
                              deadline: str | None = None) -> str:
    org = getattr(organization, "name", None) or "your organisation"
    dept = getattr(getattr(assessment, "department", None), "name", None)
    scope = f"{org}" + (f" ({dept})" if dept else "")
    when = f" Please complete it by {deadline[:10]}." if deadline else ""
    return (
        f"You are invited to complete the Elipsis operational readiness diagnostic for {scope}. "
        f"It takes about 20 minutes, answers stay inside your workspace, and you can save and resume. "
        f"Start here: {url}.{when}"
    )


def action_nudge_message(item, organization_name: str | None = None) -> str:
    title = getattr(item, "title", "your next action")
    owner = getattr(item, "owner", None) or "there"
    due = getattr(item, "due_date", None)
    org = organization_name or "the workspace"
    due_text = f" It is due {due}." if due else ""
    return (
        f"Hi {owner}, a quick nudge on '{title}' for {org}.{due_text} "
        "Please update the status or flag a blocker in Elipsis so the team can see the real picture."
    )
