"""Customer success, service delivery, support and data-rights services."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from constants import BRAND_NAME
from elipsis_api import models

LEGAL_VERSION = "2026-10-22"
SUPPORT_EMAIL = "support@elipsis.co.ke"
SECURITY_EMAIL = "security@elipsis.co.ke"
PRIVACY_EMAIL = "privacy@elipsis.co.ke"

PRIORITY_LABELS = {
    "urgent": "Urgent",
    "high": "High",
    "normal": "Normal",
    "low": "Low",
}
PRIORITY_ORDER = {"urgent": 0, "high": 1, "normal": 2, "low": 3}

SLA = {
    "urgent": {"first": 30 * 60, "resolution": 4 * 60 * 60, "coverage": "24/7"},
    "high": {"first": 2 * 60 * 60, "resolution": 8 * 60 * 60,
             "coverage": "07:00-19:00 UTC, Mon-Sat"},
    "normal": {"first": 8 * 60 * 60, "resolution": 3 * 24 * 60 * 60,
               "coverage": "08:00-18:00 UTC, Mon-Fri"},
    "low": {"first": 24 * 60 * 60, "resolution": 5 * 24 * 60 * 60,
            "coverage": "08:00-18:00 UTC, Mon-Fri"},
}

STATUS_LABELS = {
    "open": "Open",
    "in_progress": "In progress",
    "waiting_customer": "Waiting on you",
    "resolved": "Resolved",
    "closed": "Closed",
}
INCIDENT_STATUS_LABELS = {
    "investigating": "Investigating",
    "identified": "Identified",
    "monitoring": "Monitoring",
    "resolved": "Resolved",
}
INCIDENT_IMPACT_LABELS = {
    "critical": "Critical",
    "major": "Major",
    "minor": "Minor",
    "maintenance": "Maintenance",
}

TIMEZONE_CHOICES = [
    ("UTC", "UTC"),
    ("Africa/Nairobi", "Nairobi (EAT)"),
    ("Africa/Lagos", "Lagos (WAT)"),
    ("Africa/Johannesburg", "Johannesburg (SAST)"),
    ("Africa/Accra", "Accra (GMT)"),
    ("Europe/London", "London"),
    ("Europe/Paris", "Paris"),
    ("America/New_York", "New York"),
    ("America/Chicago", "Chicago"),
    ("America/Los_Angeles", "Los Angeles"),
    ("Asia/Dubai", "Dubai"),
    ("Asia/Kolkata", "Kolkata"),
    ("Asia/Singapore", "Singapore"),
    ("Australia/Sydney", "Sydney"),
]

HELP_ARTICLES = [
    {
        "slug": "start-first-assessment",
        "title": "Start your first assessment",
        "category": "Getting started",
        "summary": "Choose a company and department, then answer the operating questions.",
        "steps": [
            "Open Start assessment from the dashboard or go to /start.",
            "Choose the company and department you want to assess.",
            "Answer in plain language. A best guess is more useful than a blank.",
            "Submit to generate the readiness index, costed constraint and 90-day plan.",
        ],
        "link": "/start",
    },
    {
        "slug": "invite-your-team",
        "title": "Invite your team",
        "category": "Team workspace",
        "summary": "Add managers, supervisors and analysts with the right access.",
        "steps": [
            "Open your company workspace and choose Team.",
            "Select Invite and set a role, expiry and optional email.",
            "Copy the single-use link and send it to the person.",
            "Managers can invite; viewers can read but not change work.",
        ],
        "link": "/company",
    },
    {
        "slug": "read-your-report",
        "title": "Read the report without getting lost",
        "category": "Reports",
        "summary": "Use the readiness index, confidence level and constraint to decide what to fix first.",
        "steps": [
            "Start with the readiness index and maturity band.",
            "Check the confidence level before treating a score as precise.",
            "Read the costed constraint: it is the financial case for action.",
            "Open the 90-day plan and assign one owner to the first action.",
        ],
        "link": "/dashboard",
    },
    {
        "slug": "assign-actions",
        "title": "Assign and run the 90-day plan",
        "category": "Execution",
        "summary": "A plan only works when every action has one owner and one date.",
        "steps": [
            "Open the assessment plan.",
            "Assign an owner and due date to the first three actions.",
            "Update status in the weekly desk.",
            "Move blocked actions into a company decision.",
        ],
        "link": "/dashboard",
    },
    {
        "slug": "company-workspace",
        "title": "Use the company workspace",
        "category": "Team workspace",
        "summary": "The private space for your team's decisions, notes and weekly rhythm.",
        "steps": [
            "Open Companies and choose your company.",
            "Use Desk for the weekly schedule and workload.",
            "Use Discussion for notes and wins.",
            "Use Decisions to record a choice, owner and due date.",
        ],
        "link": "/company",
    },
    {
        "slug": "assessment-notes",
        "title": "Leave a note on a result",
        "category": "Reports",
        "summary": "Capture local context against a report section so the team remembers why a decision was made.",
        "steps": [
            "Open a completed assessment result.",
            "Find the section you want to annotate.",
            "Add a short note and save it.",
            "Notes appear in the company activity trail.",
        ],
        "link": "/dashboard",
    },
    {
        "slug": "billing-and-renewal",
        "title": "Understand billing and renewal",
        "category": "Billing",
        "summary": "Premium is a one-time Paystack payment for a fixed period, not an automatic subscription.",
        "steps": [
            "Open Pricing to see the current USD price and period.",
            "Pay through Paystack; card details never touch Elipsis.",
            "Your Premium end date is shown in Settings.",
            "Renew before the end date to avoid a gap in access.",
        ],
        "link": "/pricing",
    },
    {
        "slug": "export-your-data",
        "title": "Export your data",
        "category": "Privacy",
        "summary": "Download a JSON copy of your account, assessments, plan, tickets and feedback.",
        "steps": [
            "Open Settings and choose Data and privacy.",
            "Select Download JSON.",
            "The export is generated immediately and is not emailed.",
            "Keep the file somewhere your organisation controls.",
        ],
        "link": "/account/data",
    },
    {
        "slug": "delete-your-data",
        "title": "Request deletion of your data",
        "category": "Privacy",
        "summary": "Ask for erasure and track the 30-day completion clock.",
        "steps": [
            "Open Settings and choose Data and privacy.",
            "Submit an erasure request with an optional note.",
            "You receive a reference and a due date.",
            "We acknowledge within 2 business days and complete within 30 calendar days.",
        ],
        "link": "/account/data",
    },
    {
        "slug": "report-a-security-issue",
        "title": "Report a security issue",
        "category": "Security",
        "summary": "Tell us privately before publishing, and give us enough detail to reproduce the issue.",
        "steps": [
            "Email security@elipsis.co.ke with steps to reproduce.",
            "Do not access other customers' data or disrupt the service.",
            "We acknowledge within 2 business days.",
            "We agree a disclosure timeline with you.",
        ],
        "link": "/security",
    },
    {
        "slug": "status-and-incidents",
        "title": "Check service status",
        "category": "Service",
        "summary": "See active incidents, component health and 30-day availability.",
        "steps": [
            "Open the status page.",
            "Check whether your component is affected.",
            "Read the latest update and next update time.",
            "Subscribe for email updates if you need them.",
        ],
        "link": "/status",
    },
    {
        "slug": "accessibility",
        "title": "Accessibility support",
        "category": "Accessibility",
        "summary": "We target WCAG 2.2 AA and want to know where the experience fails you.",
        "steps": [
            "Use the accessibility statement to see known limitations.",
            "Email support if a keyboard, screen reader or contrast issue blocks you.",
            "Include the page and what you were trying to do.",
            "We treat an access blocker as a service defect.",
        ],
        "link": "/accessibility",
    },
]

CHANGELOG = [
    {
        "date": "2026-10-22",
        "version": "1.4",
        "title": "Service delivery layer",
        "body": "Published support SLAs, status page, incident communication, ticket desk, feedback, trust centre, data-rights workflow, help centre and accessibility statement.",
        "tag": "Service",
    },
    {
        "date": "2026-10-22",
        "version": "1.3",
        "title": "Company workspace",
        "body": "Added company membership, invites, private desk, discussion, decisions, assessment notes, health pulse and branded reports.",
        "tag": "Workspace",
    },
    {
        "date": "2026-10-21",
        "version": "1.2",
        "title": "Evidence and exports",
        "body": "Added evidence attachments, share links, PDF exports and company profile completeness.",
        "tag": "Product",
    },
    {
        "date": "2026-10-20",
        "version": "1.1",
        "title": "Premium and billing",
        "body": "Introduced USD Premium, Paystack checkout, renewal dates and company-scoped team access.",
        "tag": "Billing",
    },
]

SUBPROCESSORS = [
    ("Vercel", "Application hosting and edge delivery", "Global", "Data processing agreement"),
    ("Neon", "PostgreSQL database hosting", "EU / US", "Data processing agreement"),
    ("Paystack", "Payment processing", "Africa / global", "Payment processor terms"),
    ("SendGrid", "Transactional email", "US", "Data processing agreement"),
    ("Google Fonts", "Web font delivery", "Global", "Font licence; no customer data sent"),
]

RETENTION = [
    ("Account and organisation profile", "While the account is active"),
    ("Assessment answers and reports", "While the account is active"),
    ("Evidence files", "Until deleted by the customer or account closure"),
    ("Support tickets", "36 months after resolution"),
    ("Security and access logs", "12 months"),
    ("Billing records", "7 years where tax law requires it"),
    ("Closed-account data", "Deleted within 90 days"),
    ("Backups", "Rolling 35-day expiry"),
]


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def iso_after(seconds: int, start: datetime | None = None) -> str:
    base = start or datetime.now(UTC)
    return (base + timedelta(seconds=seconds)).strftime("%Y-%m-%d %H:%M:%S")


def zone(name: str | None):
    try:
        return ZoneInfo(name or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def format_dt(value: str | None, timezone: str | None = None,
              pattern: str = "%d %b %Y, %H:%M %Z") -> str:
    parsed = parse_dt(value)
    if parsed is None:
        return "Not set"
    return parsed.astimezone(zone(timezone)).strftime(pattern)


def human_due(value: str | None, timezone: str | None = None) -> str:
    parsed = parse_dt(value)
    if parsed is None:
        return "No due time"
    delta = parsed - datetime.now(UTC)
    seconds = int(delta.total_seconds())
    if seconds <= 0:
        return "Overdue"
    if seconds < 3600:
        return f"Due in {max(1, seconds // 60)} min"
    if seconds < 86400:
        return f"Due in {seconds // 3600}h"
    return f"Due {parsed.astimezone(zone(timezone)).strftime('%d %b, %H:%M %Z')}"


def _priority(value: str | None) -> str:
    value = (value or "normal").strip().lower()
    return value if value in SLA else "normal"


def primary_org_id(db: Session, user) -> int | None:
    if user is None:
        return None
    prefs = db.get(models.UserPref, user.id)
    if prefs is not None and prefs.default_organization_id:
        link = db.scalar(select(models.OrgOwner).where(
            models.OrgOwner.user_id == user.id,
            models.OrgOwner.organization_id == prefs.default_organization_id,
            models.OrgOwner.status == "active"))
        if link is not None:
            return link.organization_id
    link = db.scalar(select(models.OrgOwner).where(
        models.OrgOwner.user_id == user.id,
        models.OrgOwner.status == "active").order_by(models.OrgOwner.id))
    return link.organization_id if link is not None else None


def create_ticket(db: Session, user, *, subject: str, body: str,
                  category: str = "general", priority: str = "normal",
                  source_path: str | None = None, email: str | None = None,
                  timezone: str = "UTC") -> models.SupportTicket:
    stamp = _now()
    priority = _priority(priority)
    ticket = models.SupportTicket(
        reference="pending",
        user_id=user.id if user else None,
        organization_id=primary_org_id(db, user),
        requester_email=(email or (user.email if user else "") or "").strip().lower(),
        subject=subject.strip()[:180],
        body=body.strip()[:8000],
        category=category.strip()[:40] or "general",
        priority=priority,
        status="open",
        channel="app" if user else "web",
        source_path=(source_path or "")[:300] or None,
        timezone=timezone or "UTC",
        first_response_due=iso_after(SLA[priority]["first"]),
        resolution_due=iso_after(SLA[priority]["resolution"]),
        created_at=stamp,
        updated_at=stamp,
    )
    db.add(ticket)
    db.flush()
    ticket.reference = f"ELP-{stamp[:10].replace('-', '')}-{ticket.id:04d}"
    db.commit()
    return ticket


def add_message(db: Session, ticket: models.SupportTicket, *, body: str,
                author_id: int | None, author_name: str | None,
                internal: bool = False, from_staff: bool = False) -> models.SupportMessage:
    stamp = _now()
    message = models.SupportMessage(
        ticket_id=ticket.id,
        author_id=author_id,
        author_name=(author_name or "")[:120] or None,
        body=body.strip()[:8000],
        internal=1 if internal else 0,
        created_at=stamp,
    )
    db.add(message)
    if from_staff and not internal and not ticket.first_response_at:
        ticket.first_response_at = stamp
    if not internal:
        if from_staff:
            ticket.status = "waiting_customer"
        else:
            ticket.status = "open"
            ticket.resolved_at = None
    ticket.updated_at = stamp
    db.commit()
    return message


def resolve_ticket(db: Session, ticket: models.SupportTicket) -> None:
    stamp = _now()
    ticket.status = "resolved"
    ticket.resolved_at = stamp
    ticket.updated_at = stamp
    db.commit()


def ticket_state(ticket: models.SupportTicket) -> dict[str, Any]:
    now = datetime.now(UTC)
    first_due = parse_dt(ticket.first_response_due)
    resolution_due = parse_dt(ticket.resolution_due)
    resolved = (ticket.status or "") in {"resolved", "closed"}
    first_breached = bool(first_due and not ticket.first_response_at and now > first_due)
    resolution_breached = bool(
        resolution_due and not ticket.resolved_at and now > resolution_due)
    if resolved:
        state = "resolved"
    elif first_breached or resolution_breached:
        state = "breached"
    elif first_due and (first_due - now).total_seconds() < 3600 and not ticket.first_response_at:
        state = "warning"
    else:
        state = "on_track"
    return {
        "state": state,
        "first_breached": first_breached,
        "resolution_breached": resolution_breached,
        "resolved": resolved,
        "priority_label": PRIORITY_LABELS.get(ticket.priority or "normal", "Normal"),
        "status_label": STATUS_LABELS.get(ticket.status or "open", "Open"),
    }


def tickets_for(db: Session, user, limit: int = 50) -> list[models.SupportTicket]:
    if user is None:
        return []
    return list(db.scalars(
        select(models.SupportTicket)
        .where(models.SupportTicket.user_id == user.id)
        .order_by(models.SupportTicket.id.desc()).limit(limit)
    ))


def ticket_for(db: Session, user, reference: str) -> models.SupportTicket | None:
    if user is None:
        return None
    ticket = db.scalar(select(models.SupportTicket).where(
        models.SupportTicket.reference == reference))
    if ticket is None:
        return None
    from elipsis_api.services import is_admin
    if is_admin(user) or ticket.user_id == user.id:
        return ticket
    return None


def messages_for(db: Session, ticket_id: int, public_only: bool = True) -> list[models.SupportMessage]:
    query = select(models.SupportMessage).where(
        models.SupportMessage.ticket_id == ticket_id)
    if public_only:
        query = query.where(models.SupportMessage.internal == 0)
    return list(db.scalars(query.order_by(models.SupportMessage.created_at,
                                          models.SupportMessage.id)))


def support_metrics(db: Session) -> dict[str, Any]:
    open_rows = list(db.scalars(select(models.SupportTicket).where(
        models.SupportTicket.status.not_in(("resolved", "closed")))))
    breached = [row for row in open_rows if ticket_state(row)["state"] == "breached"]
    urgent = [row for row in open_rows if row.priority == "urgent"]
    ratings = list(db.scalars(select(models.SupportTicket.csat_score).where(
        models.SupportTicket.csat_score.is_not(None))))
    average = round(sum(ratings) / len(ratings), 2) if ratings else None
    low_rows = list(db.scalars(select(models.SupportTicket).where(
        models.SupportTicket.csat_score.is_not(None),
        models.SupportTicket.csat_score <= 2).order_by(
        models.SupportTicket.updated_at.desc()).limit(20)))
    return {
        "open": len(open_rows),
        "urgent": len(urgent),
        "breached": len(breached),
        "csat": average,
        "ratings": len(ratings),
        "low_csat": len(low_rows),
        "low_csat_tickets": low_rows,
        "tickets": sorted(open_rows, key=lambda row: (
            PRIORITY_ORDER.get(row.priority or "normal", 9), row.id)),
    }


def feedback_summary(db: Session) -> dict[str, Any]:
    rows = list(db.scalars(select(models.Feedback).order_by(models.Feedback.id.desc())))
    nps_rows = [row for row in rows if row.kind == "nps" and row.score is not None]
    csat_rows = [row for row in rows if row.kind == "csat" and row.score is not None]
    ces_rows = [row for row in rows if row.kind == "ces" and row.score is not None]
    promoters = sum(1 for row in nps_rows if (row.score or 0) >= 9)
    detractors = sum(1 for row in nps_rows if (row.score or 0) <= 6)
    nps = round(100 * (promoters - detractors) / len(nps_rows)) if nps_rows else None
    csat = (round(100 * sum(1 for row in csat_rows if (row.score or 0) >= 4)
                  / len(csat_rows)) if csat_rows else None)
    ces = round(sum(row.score or 0 for row in ces_rows) / len(ces_rows), 2) if ces_rows else None
    return {
        "nps": nps,
        "csat": csat,
        "ces": ces,
        "responses": len(rows),
        "promoters": promoters,
        "detractors": detractors,
        "nps_responses": len(nps_rows),
        "recent": rows[:12],
    }


def create_feedback(db: Session, user, *, kind: str, score: int,
                    comment: str, context: str, path: str) -> models.Feedback:
    row = models.Feedback(
        user_id=user.id if user else None,
        organization_id=primary_org_id(db, user),
        kind=kind if kind in {"nps", "csat", "ces", "feature"} else "nps",
        score=max(0, min(10, int(score))),
        comment=(comment or "").strip()[:4000] or None,
        context=(context or "").strip()[:120] or None,
        path=(path or "").strip()[:300] or None,
    )
    db.add(row)
    db.commit()
    return row


def record_acceptance(db: Session, user, *, document: str, version: str,
                      request=None) -> models.LegalAcceptance:
    existing = db.scalar(select(models.LegalAcceptance).where(
        models.LegalAcceptance.user_id == user.id,
        models.LegalAcceptance.document == document,
        models.LegalAcceptance.version == version,
    ))
    if existing is not None:
        return existing
    ip = ""
    agent = ""
    if request is not None:
        ip = (request.client.host if request.client else "") or ""
        agent = request.headers.get("user-agent", "")
    row = models.LegalAcceptance(
        user_id=user.id,
        document=document,
        version=version,
        accepted_at=_now(),
        ip_hash=hashlib.sha256(ip.encode()).hexdigest()[:32] if ip else None,
        user_agent=agent[:300] or None,
    )
    db.add(row)
    db.commit()
    return row


def legal_state(db: Session, user) -> dict[str, Any]:
    rows = list(db.scalars(select(models.LegalAcceptance).where(
        models.LegalAcceptance.user_id == user.id))) if user else []
    accepted = {(row.document, row.version) for row in rows}
    return {
        "current_version": LEGAL_VERSION,
        "terms_accepted": ("terms", LEGAL_VERSION) in accepted,
        "privacy_accepted": ("privacy", LEGAL_VERSION) in accepted,
        "records": rows,
    }


def create_data_request(db: Session, user, *, kind: str, note: str = "",
                        organization_id: int | None = None) -> tuple[models.DataRequest, bool]:
    kind = kind if kind in {"export", "erasure", "correction"} else "export"
    existing = db.scalar(select(models.DataRequest).where(
        models.DataRequest.user_id == user.id,
        models.DataRequest.kind == kind,
        models.DataRequest.status.in_(("received", "in_progress")),
    ))
    if existing is not None:
        return existing, False
    stamp = _now()
    row = models.DataRequest(
        reference="pending",
        user_id=user.id,
        organization_id=organization_id or primary_org_id(db, user),
        kind=kind,
        status="received",
        note=(note or "").strip()[:4000] or None,
        due_at=iso_after(30 * 24 * 60 * 60),
        created_at=stamp,
        updated_at=stamp,
    )
    db.add(row)
    db.flush()
    row.reference = f"ELP-DR-{stamp[:10].replace('-', '')}-{row.id:04d}"
    db.commit()
    return row, True


def complete_data_request(db: Session, row: models.DataRequest, note: str = "") -> None:
    stamp = _now()
    row.status = "completed"
    row.completed_at = stamp
    row.updated_at = stamp
    if note:
        row.note = ((row.note or "") + "\n\nResolution: " + note.strip())[:4000]
    db.commit()


def data_requests_for(db: Session, user) -> list[models.DataRequest]:
    rows = db.scalars(select(models.DataRequest).where(
        models.DataRequest.user_id == user.id).order_by(models.DataRequest.id.desc()))
    return list(rows)


def export_payload(db: Session, user) -> dict[str, Any]:
    from elipsis_api import services
    orgs = services.owned_orgs(db, user)
    org_ids = [org.id for org in orgs]
    prefs = db.get(models.UserPref, user.id)
    assessments = list(db.scalars(select(models.Assessment).where(
        models.Assessment.organization_id.in_(org_ids)
    ).order_by(models.Assessment.id))) if org_ids else []
    tickets = tickets_for(db, user, limit=1000)
    data = {
        "generated_at": _now(),
        "brand": BRAND_NAME,
        "account": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "user_type": user.user_type,
            "created_at": user.created_at,
            "email_verified": bool(user.email_verified),
        },
        "preferences": {
            "timezone": prefs.timezone if prefs else "UTC",
            "landing_page": prefs.landing_page if prefs else None,
            "phone": prefs.phone if prefs else None,
            "bio": prefs.bio if prefs else None,
        } if prefs else {},
        "organizations": [
            {
                "id": org.id,
                "name": org.name,
                "industry": org.industry,
                "country": org.country,
                "city": org.city,
                "website": org.website,
                "created_at": org.created_at,
            }
            for org in orgs
        ],
        "assessments": [],
        "support_tickets": [],
        "feedback": [],
        "legal_acceptances": [],
        "data_requests": [],
    }
    for assessment in assessments:
        answers = db.execute(
            select(models.Answer, models.Question.code, models.Question.text)
            .join(models.Question, models.Question.id == models.Answer.question_id)
            .where(models.Answer.assessment_id == assessment.id)
            .order_by(models.Question.id)
        ).all()
        plan = list(db.scalars(select(models.RoadmapItem).where(
            models.RoadmapItem.assessment_id == assessment.id)))
        data["assessments"].append({
            "id": assessment.id,
            "organization_id": assessment.organization_id,
            "department_id": assessment.department_id,
            "status": assessment.status,
            "started_at": assessment.started_at,
            "completed_at": assessment.completed_at,
            "readiness_index": assessment.readiness_index,
            "confidence_index": assessment.confidence_index,
            "maturity_band": assessment.maturity_band,
            "answers": [
                {"question_code": code, "question": text, "score": answer.score,
                 "evidence": answer.evidence}
                for answer, code, text in answers
            ],
            "plan": [
                {"title": item.title, "owner": item.owner, "due_date": item.due_date,
                 "status": item.status, "horizon": item.horizon}
                for item in plan
            ],
        })
    for ticket in tickets:
        data["support_tickets"].append({
            "reference": ticket.reference,
            "subject": ticket.subject,
            "body": ticket.body,
            "priority": ticket.priority,
            "status": ticket.status,
            "created_at": ticket.created_at,
            "resolved_at": ticket.resolved_at,
            "messages": [
                {"author": message.author_name or "Customer",
                 "body": message.body, "created_at": message.created_at}
                for message in messages_for(db, ticket.id, public_only=True)
            ],
        })
    for row in db.scalars(select(models.Feedback).where(models.Feedback.user_id == user.id)):
        data["feedback"].append({
            "kind": row.kind, "score": row.score, "comment": row.comment,
            "context": row.context, "created_at": row.created_at})
    for row in db.scalars(select(models.LegalAcceptance).where(
            models.LegalAcceptance.user_id == user.id)):
        data["legal_acceptances"].append({
            "document": row.document, "version": row.version,
            "accepted_at": row.accepted_at})
    for row in data_requests_for(db, user):
        data["data_requests"].append({
            "reference": row.reference, "kind": row.kind, "status": row.status,
            "due_at": row.due_at, "completed_at": row.completed_at,
            "created_at": row.created_at})
    return data


def activation(db: Session, user, org: models.Organization | None) -> dict[str, Any]:
    from elipsis_api import services
    if org is None:
        milestones = [
            {"key": "account", "label": "Create your account", "done": True,
             "url": "/setup", "detail": "Done"},
            {"key": "profile", "label": "Add your company profile", "done": False,
             "url": "/setup", "detail": "Start here"},
        ]
        return {"percent": 14, "milestones": milestones, "next": milestones[1],
                "complete": 1, "total": 7}
    assessments = list(db.scalars(select(models.Assessment).where(
        models.Assessment.organization_id == org.id)))
    started = bool(assessments)
    completed = [row for row in assessments if (row.status or "") == "completed"]
    profile = services.company_completeness(org)
    actions = list(db.scalars(
        select(models.RoadmapItem)
        .join(models.Assessment, models.Assessment.id == models.RoadmapItem.assessment_id)
        .where(models.Assessment.organization_id == org.id)))
    action_owned = any((item.owner or "").strip() for item in actions)
    member_count = db.scalar(select(func.count()).select_from(models.OrgOwner).where(
        models.OrgOwner.organization_id == org.id,
        models.OrgOwner.status == "active")) or 0
    invite_count = db.scalar(select(func.count()).select_from(models.OrgInvite).where(
        models.OrgInvite.organization_id == org.id,
        models.OrgInvite.status == "active")) or 0
    rhythm = bool(
        db.scalar(select(func.count()).select_from(models.CompanyDecision).where(
            models.CompanyDecision.organization_id == org.id))
        or db.scalar(select(func.count()).select_from(models.Assessment).where(
            models.Assessment.organization_id == org.id,
            models.Assessment.review_due_at.is_not(None)))
    )
    milestones = [
        {"key": "account", "label": "Create your account", "done": True,
         "url": "/dashboard", "detail": "Done"},
        {"key": "profile", "label": "Complete 60% of your company profile",
         "done": profile["percent"] >= 60, "url": "/settings#company",
         "detail": f"{profile['percent']}% complete"},
        {"key": "started", "label": "Start an assessment", "done": started,
         "url": "/start", "detail": "About 8 minutes"},
        {"key": "completed", "label": "Complete the assessment and see your result",
         "done": bool(completed), "url": f"/company/{org.id}",
         "detail": "Unlocks the costed constraint and plan"},
        {"key": "action", "label": "Give one action a named owner", "done": action_owned,
         "url": "/dashboard", "detail": "One owner, one date"},
        {"key": "team", "label": "Invite a teammate",
         "done": member_count > 1 or invite_count > 0,
         "url": f"/company/{org.id}/team", "detail": "Managers and supervisors"},
        {"key": "rhythm", "label": "Record a decision or schedule a review", "done": rhythm,
         "url": f"/company/{org.id}/decisions", "detail": "Build the weekly rhythm"},
    ]
    complete = sum(1 for item in milestones if item["done"])
    next_item = next((item for item in milestones if not item["done"]), None)
    return {
        "percent": round(complete / len(milestones) * 100),
        "milestones": milestones,
        "next": next_item,
        "complete": complete,
        "total": len(milestones),
    }


def customer_health(db: Session, org: models.Organization) -> dict[str, Any]:
    from elipsis_api import services
    score = 0
    factors = []

    profile = services.company_completeness(org)
    profile_points = round(profile["percent"] / 100 * 20)
    score += profile_points
    factors.append({"label": "Profile completeness", "points": profile_points,
                    "max": 20, "detail": f"{profile['percent']}%"})

    latest = db.scalar(select(models.Assessment).where(
        models.Assessment.organization_id == org.id,
        models.Assessment.status == "completed",
        models.Assessment.completed_at.is_not(None),
    ).order_by(models.Assessment.completed_at.desc(), models.Assessment.id.desc()))
    age_days = None
    recency_points = 0
    if latest and latest.completed_at:
        completed = parse_dt(latest.completed_at)
        if completed:
            age_days = (datetime.now(UTC) - completed).days
            recency_points = 20 if age_days <= 90 else 12 if age_days <= 180 else 6 if age_days <= 365 else 0
    score += recency_points
    factors.append({"label": "Assessment recency", "points": recency_points,
                    "max": 20,
                    "detail": f"{age_days} days ago" if age_days is not None else "No completed assessment"})

    actions = list(db.scalars(
        select(models.RoadmapItem)
        .join(models.Assessment, models.Assessment.id == models.RoadmapItem.assessment_id)
        .where(models.Assessment.organization_id == org.id)))
    done = sum(1 for item in actions if item.status == "done")
    progress_points = round((done / len(actions)) * 20) if actions else 0
    score += progress_points
    factors.append({"label": "Plan progress", "points": progress_points, "max": 20,
                    "detail": f"{done}/{len(actions)} done" if actions else "No plan yet"})

    members = db.scalar(select(func.count()).select_from(models.OrgOwner).where(
        models.OrgOwner.organization_id == org.id,
        models.OrgOwner.status == "active")) or 0
    team_points = 15 if members >= 4 else 12 if members == 3 else 8 if members == 2 else 3
    score += team_points
    factors.append({"label": "Team depth", "points": team_points, "max": 15,
                    "detail": f"{members} active member(s)"})

    since = (datetime.now(UTC) - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    posts = db.scalar(select(func.count()).select_from(models.CompanyPost).where(
        models.CompanyPost.organization_id == org.id,
        models.CompanyPost.created_at >= since)) or 0
    decisions = db.scalar(select(func.count()).select_from(models.CompanyDecision).where(
        models.CompanyDecision.organization_id == org.id,
        models.CompanyDecision.created_at >= since)) or 0
    notes = db.scalar(select(func.count()).select_from(models.AssessmentNote).where(
        models.AssessmentNote.organization_id == org.id,
        models.AssessmentNote.created_at >= since)) or 0
    activity = posts + decisions + notes
    collaboration_points = 10 if activity >= 5 else 6 if activity >= 2 else 3 if activity >= 1 else 0
    score += collaboration_points
    factors.append({"label": "30-day collaboration", "points": collaboration_points,
                    "max": 10, "detail": f"{activity} shared update(s)"})

    rhythm_points = 5 if decisions >= 1 else 0
    score += rhythm_points
    factors.append({"label": "Operating rhythm", "points": rhythm_points,
                    "max": 5, "detail": f"{decisions} decision(s) in 30 days"})

    open_risk = db.scalar(select(func.count()).select_from(models.SupportTicket).where(
        models.SupportTicket.organization_id == org.id,
        models.SupportTicket.status.not_in(("resolved", "closed")),
        models.SupportTicket.priority.in_(("urgent", "high")))) or 0
    support_points = 10 if open_risk == 0 else 5 if open_risk == 1 else 0
    score += support_points
    factors.append({"label": "Support risk", "points": support_points, "max": 10,
                    "detail": "No urgent open tickets" if not open_risk else f"{open_risk} open high-priority ticket(s)"})

    score = max(0, min(100, score))
    if score >= 75:
        band = "Healthy"
    elif score >= 50:
        band = "Watch"
    elif latest is None:
        band = "Onboarding"
    else:
        band = "At risk"
    if not latest:
        next_action = ("Complete your first assessment", "/start")
    elif profile["percent"] < 60:
        next_action = ("Complete the company profile", "/settings#company")
    elif members < 2:
        next_action = ("Invite a manager", f"/company/{org.id}/team")
    elif not actions:
        next_action = ("Open the 90-day plan", "/dashboard")
    elif done == 0:
        next_action = ("Start the first action", "/dashboard")
    elif activity < 2:
        next_action = ("Record a decision or note", f"/company/{org.id}/decisions")
    else:
        next_action = ("Repeat the assessment", "/start")
    return {
        "score": score, "band": band, "factors": factors,
        "next_action": {"label": next_action[0], "url": next_action[1]},
        "assessment_age_days": age_days,
    }


def health_queue(db: Session, limit: int = 12) -> list[dict[str, Any]]:
    orgs = list(db.scalars(
        select(models.Organization)
        .join(models.OrgOwner, models.OrgOwner.organization_id == models.Organization.id)
        .where(models.OrgOwner.status == "active")
        .distinct().limit(80)))
    rows = []
    for org in orgs:
        health = customer_health(db, org)
        if health["score"] < 75:
            rows.append({"org": org, "health": health})
    rows.sort(key=lambda row: row["health"]["score"])
    return rows[:limit]


def incidents(db: Session, include_resolved: bool = True) -> list[models.ServiceIncident]:
    query = select(models.ServiceIncident)
    if not include_resolved:
        query = query.where(models.ServiceIncident.status != "resolved")
    return list(db.scalars(query.order_by(models.ServiceIncident.started_at.desc()).limit(30)))


def incident_updates(db: Session, incident_id: int) -> list[models.ServiceIncidentUpdate]:
    return list(db.scalars(select(models.ServiceIncidentUpdate).where(
        models.ServiceIncidentUpdate.incident_id == incident_id
    ).order_by(models.ServiceIncidentUpdate.created_at, models.ServiceIncidentUpdate.id)))


def create_incident(db: Session, *, title: str, summary: str, impact: str,
                    components: list[str], created_by: int | None = None) -> models.ServiceIncident:
    stamp = _now()
    impact = impact if impact in INCIDENT_IMPACT_LABELS else "minor"
    row = models.ServiceIncident(
        reference="pending",
        title=title.strip()[:180],
        summary=summary.strip()[:4000],
        status="investigating",
        impact=impact,
        components=",".join(components)[:200] or "web,api",
        started_at=stamp,
        created_at=stamp,
        updated_at=stamp,
    )
    db.add(row)
    db.flush()
    row.reference = f"INC-{stamp[:10].replace('-', '')}-{row.id:03d}"
    db.add(models.ServiceIncidentUpdate(
        incident_id=row.id, status="investigating",
        body=summary.strip()[:4000] or "We are investigating.",
        created_by=created_by, created_at=stamp))
    db.commit()
    return row


def update_incident(db: Session, row: models.ServiceIncident, *, status: str,
                    body: str, created_by: int | None = None,
                    postmortem: str = "") -> None:
    stamp = _now()
    status = status if status in INCIDENT_STATUS_LABELS else row.status or "investigating"
    row.status = status
    row.updated_at = stamp
    if status == "resolved":
        row.resolved_at = stamp
    if postmortem.strip():
        row.postmortem = postmortem.strip()[:8000]
    db.add(models.ServiceIncidentUpdate(
        incident_id=row.id, status=status, body=body.strip()[:4000],
        created_by=created_by, created_at=stamp))
    db.commit()


def availability_30d(db: Session) -> dict[str, Any]:
    now = datetime.now(UTC)
    start = now - timedelta(days=30)
    downtime = 0.0
    for row in incidents(db):
        if row.impact not in {"critical", "major"}:
            continue
        began = parse_dt(row.started_at)
        if began is None or began > now:
            continue
        ended = parse_dt(row.resolved_at) or now
        began = max(began, start)
        if ended > began:
            downtime += (ended - began).total_seconds()
    total = 30 * 24 * 60 * 60
    availability = max(0.0, min(100.0, 100 * (1 - downtime / total)))
    return {
        "percent": round(availability, 3),
        "downtime_minutes": round(downtime / 60),
        "period_days": 30,
        "target": 99.9,
        "met": availability >= 99.9,
    }


def status_components(db: Session) -> list[dict[str, Any]]:
    active = incidents(db, include_resolved=False)
    affected = set()
    for row in active:
        affected.update(part.strip() for part in (row.components or "").split(","))
    labels = [
        ("web", "Web application"),
        ("api", "API"),
        ("database", "Database"),
        ("email", "Email delivery"),
        ("payments", "Payments"),
    ]
    out = []
    for key, label in labels:
        if key in affected:
            state = "degraded"
        else:
            state = "operational"
        out.append({"key": key, "label": label, "state": state})
    return out


def help_search(query: str = "") -> list[dict[str, Any]]:
    term = (query or "").strip().lower()
    if not term:
        return HELP_ARTICLES
    return [
        article for article in HELP_ARTICLES
        if term in article["title"].lower()
        or term in article["summary"].lower()
        or term in article["category"].lower()
        or any(term in step.lower() for step in article["steps"])
    ]


def help_article(slug: str) -> dict[str, Any] | None:
    return next((item for item in HELP_ARTICLES if item["slug"] == slug), None)
