"""Company room: membership, private invites, collaboration, desk, and pulse."""

from __future__ import annotations

import re
import secrets
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from elipsis_api import models, services, services_ops

INVITE_DAYS = (3, 7, 14, 30)
POST_TAGS = ("update", "question", "result", "risk", "win")
DECISION_STATES = ("open", "in_progress", "done", "deferred")
SECTIONS = ("Overall", "Score", "Finance", "Actions", "Operations", "Compliance", "Benchmark")
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def _today() -> date:
    return datetime.now(UTC).date()


def _day(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None


def initials(name: str | None, email: str | None = None) -> str:
    source = (name or email or "?").strip()
    bits = [b for b in re.split(r"[\s@._-]+", source) if b]
    if not bits:
        return "?"
    return (bits[0][:1] + (bits[1][:1] if len(bits) > 1 else "")).upper()


def member_rows(db: Session, organization_id: int) -> list[dict[str, Any]]:
    rows = db.execute(
        select(models.OrgOwner, models.User)
        .join(models.User, models.User.id == models.OrgOwner.user_id)
        .where(models.OrgOwner.organization_id == organization_id)
        .order_by(models.OrgOwner.role, models.User.name, models.User.email)
    ).all()
    order = {"owner": 0, "manager": 1, "supervisor": 2, "analyst": 3, "viewer": 4}
    out = []
    for link, user in rows:
        role = link.role if link.role in services.ROLE_LABELS else "owner"
        out.append({
            "link": link, "user": user, "role": role,
            "role_label": services.ROLE_LABELS[role],
            "initials": initials(user.name, user.email),
            "status": link.status or "active",
            "title": link.title or (db.get(models.UserPref, user.id).job_title
                                    if db.get(models.UserPref, user.id) else ""),
            "department": link.department or "",
            "joined_at": link.joined_at or link.created_at or "",
        })
    out.sort(key=lambda r: (order.get(r["role"], 9), (r["user"].name or r["user"].email).lower()))
    return out


def create_invite(db: Session, organization_id: int, actor_id: int | None, *,
                  email: str = "", role: str = "manager", title: str = "",
                  department: str = "", note: str = "", days: int = 7,
                  max_uses: int = 1) -> tuple[models.OrgInvite | None, str]:
    role = role if role in services.ROLE_LABELS else "manager"
    if role == "owner":
        role = "manager"
    days = days if days in INVITE_DAYS else 7
    max_uses = max(1, min(int(max_uses or 1), 50))
    invite = models.OrgInvite(
        token=secrets.token_urlsafe(24), organization_id=organization_id,
        created_by=actor_id, email=(email or "").strip().lower()[:160] or None,
        role=role, title=(title or "").strip()[:120] or None,
        department=(department or "").strip()[:120] or None,
        note=(note or "").strip()[:1000] or None, max_uses=max_uses, uses=0,
        status="active",
        expires_at=(datetime.now(UTC) + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S"),
        created_at=_now())
    db.add(invite)
    services_ops.record_audit(
        db, action="team.invite", organization_id=organization_id, user_id=actor_id,
        detail=f"Invite created for {invite.email or 'any email'} as {role}")
    db.commit()
    db.refresh(invite)
    return invite, ""


def find_invite(db: Session, token: str) -> models.OrgInvite | None:
    return db.scalar(select(models.OrgInvite).where(models.OrgInvite.token == token))


def invite_error(invite: models.OrgInvite | None) -> str:
    if invite is None:
        return "This invite link is not valid."
    if (invite.status or "active") != "active":
        return "This invite link has been revoked."
    expires = _day(invite.expires_at)
    if expires and expires < _today():
        return "This invite link has expired."
    if (invite.uses or 0) >= (invite.max_uses or 1):
        return "This invite link has already been used."
    return ""


def accept_invite(db: Session, invite: models.OrgInvite, user) -> tuple[bool, str]:
    error = invite_error(invite)
    if error:
        return False, error
    if invite.email and invite.email.lower() != (user.email or "").lower():
        return False, "This invite was issued to a different email address."
    existing = db.scalar(select(models.OrgOwner).where(
        models.OrgOwner.user_id == user.id,
        models.OrgOwner.organization_id == invite.organization_id))
    if existing is None:
        db.add(models.OrgOwner(
            user_id=user.id, organization_id=invite.organization_id,
            role=invite.role or "manager", title=invite.title,
            department=invite.department, status="active",
            invited_by=invite.created_by, joined_at=_now(), created_at=_now()))
    else:
        existing.status = "active"
        if not existing.title and invite.title:
            existing.title = invite.title
        if not existing.department and invite.department:
            existing.department = invite.department
    invite.uses = (invite.uses or 0) + 1
    if invite.uses >= (invite.max_uses or 1):
        invite.status = "used"
    services_ops.record_audit(
        db, action="team.join", organization_id=invite.organization_id, user_id=user.id,
        detail=f"{user.email} joined via private invite")
    db.commit()
    return True, "You are now part of this company workspace."


def revoke_invite(db: Session, invite: models.OrgInvite, actor_id: int | None) -> None:
    invite.status = "revoked"
    services_ops.record_audit(
        db, action="team.invite_revoked", organization_id=invite.organization_id,
        user_id=actor_id, detail=f"Invite {invite.id} revoked")
    db.commit()


def invites(db: Session, organization_id: int) -> list[models.OrgInvite]:
    return list(db.scalars(select(models.OrgInvite).where(
        models.OrgInvite.organization_id == organization_id
    ).order_by(models.OrgInvite.id.desc()).limit(20)))


def update_member(db: Session, link: models.OrgOwner, actor_id: int | None, *,
                  role: str, title: str, department: str,
                  status: str = "active") -> tuple[bool, str]:
    role = role if role in services.ROLE_LABELS else "analyst"
    status = status if status in {"active", "suspended"} else "active"
    if (link.role or "owner") == "owner" and role != "owner":
        owners = list(db.scalars(select(models.OrgOwner).where(
            models.OrgOwner.organization_id == link.organization_id,
            models.OrgOwner.role == "owner",
            models.OrgOwner.status != "suspended")))
        if len(owners) <= 1:
            return False, "Keep at least one owner on the company."
    link.role = role
    link.title = (title or "").strip()[:120] or None
    link.department = (department or "").strip()[:120] or None
    link.status = status
    services_ops.record_audit(
        db, action="team.role", organization_id=link.organization_id, user_id=actor_id,
        detail=f"Member {link.user_id}: {role}, {status}")
    db.commit()
    return True, "Member updated."


def remove_member(db: Session, organization_id: int, link: models.OrgOwner,
                  actor_id: int | None) -> tuple[bool, str]:
    active = [row for row in db.scalars(select(models.OrgOwner).where(
        models.OrgOwner.organization_id == organization_id,
        models.OrgOwner.status != "suspended"))]
    if len(active) <= 1:
        return False, "Keep at least one active member on the company."
    db.delete(link)
    services_ops.record_audit(
        db, action="team.remove", organization_id=organization_id, user_id=actor_id,
        detail=f"Removed user {link.user_id}")
    db.commit()
    return True, "Member removed."


def feed(db: Session, organization_id: int, limit: int = 30) -> list[dict[str, Any]]:
    posts = list(db.scalars(select(models.CompanyPost).where(
        models.CompanyPost.organization_id == organization_id
    ).order_by(models.CompanyPost.pinned.desc(), models.CompanyPost.id.desc()).limit(limit)))
    if not posts:
        return []
    replies = list(db.scalars(select(models.CompanyPostReply).where(
        models.CompanyPostReply.post_id.in_([p.id for p in posts])
    ).order_by(models.CompanyPostReply.id.asc())))
    users: dict[int, models.User] = {}
    for row in posts:
        if row.author_id and row.author_id not in users:
            users[row.author_id] = db.get(models.User, row.author_id)
    for row in replies:
        if row.author_id and row.author_id not in users:
            users[row.author_id] = db.get(models.User, row.author_id)
    by_post: dict[int, list[dict[str, Any]]] = {}
    for row in replies:
        author = users.get(row.author_id or 0)
        by_post.setdefault(row.post_id, []).append({
            "row": row, "author": author,
            "initials": initials(author.name if author else "", author.email if author else ""),
        })
    out = []
    for row in posts:
        author = users.get(row.author_id or 0)
        out.append({
            "row": row, "author": author,
            "initials": initials(author.name if author else "", author.email if author else ""),
            "replies": by_post.get(row.id, []),
        })
    return out


def create_post(db: Session, organization_id: int, actor_id: int | None,
                body: str, tag: str = "update") -> tuple[bool, str]:
    body = (body or "").strip()[:4000]
    if not body:
        return False, "Write something before posting."
    tag = tag if tag in POST_TAGS else "update"
    db.add(models.CompanyPost(organization_id=organization_id, author_id=actor_id,
                              body=body, tag=tag, created_at=_now()))
    services_ops.record_audit(db, action="company.post", organization_id=organization_id,
                              user_id=actor_id, detail=body[:160])
    db.commit()
    return True, "Posted to the company room."


def create_reply(db: Session, post: models.CompanyPost, actor_id: int | None,
                 body: str) -> tuple[bool, str]:
    body = (body or "").strip()[:2000]
    if not body:
        return False, "Write a reply first."
    db.add(models.CompanyPostReply(post_id=post.id, author_id=actor_id,
                                  body=body, created_at=_now()))
    services_ops.record_audit(db, action="company.reply", organization_id=post.organization_id,
                              user_id=actor_id, detail=body[:160])
    db.commit()
    return True, "Reply added."


def toggle_pin(db: Session, post: models.CompanyPost, actor_id: int | None) -> None:
    post.pinned = 0 if post.pinned else 1
    services_ops.record_audit(db, action="company.pin", organization_id=post.organization_id,
                              user_id=actor_id, detail=f"Post {post.id} pinned={post.pinned}")
    db.commit()


def decisions(db: Session, organization_id: int, limit: int = 50) -> list[dict[str, Any]]:
    rows = list(db.scalars(select(models.CompanyDecision).where(
        models.CompanyDecision.organization_id == organization_id
    ).order_by(models.CompanyDecision.status, models.CompanyDecision.due_date,
               models.CompanyDecision.id.desc()).limit(limit)))
    today = _today()
    out = []
    for row in rows:
        due = _day(row.due_date)
        out.append({
            "row": row, "overdue": bool(due and due < today and row.status != "done"),
            "due_soon": bool(due and today <= due <= today + timedelta(days=7)
                             and row.status != "done"),
        })
    return out


def create_decision(db: Session, organization_id: int, actor_id: int | None, *,
                    title: str, detail: str = "", owner_id: int | None = None,
                    owner_name: str = "", due_date: str = "",
                    assessment_id: int | None = None) -> tuple[bool, str]:
    title = (title or "").strip()[:160]
    if not title:
        return False, "Give the decision a title."
    db.add(models.CompanyDecision(
        organization_id=organization_id, title=title,
        detail=(detail or "").strip()[:4000] or None,
        owner_id=owner_id, owner_name=(owner_name or "").strip()[:120] or None,
        due_date=(due_date or "").strip()[:10] or None, status="open",
        assessment_id=assessment_id, created_by=actor_id,
        created_at=_now(), updated_at=_now()))
    services_ops.record_audit(db, action="company.decision", organization_id=organization_id,
                              user_id=actor_id, detail=title)
    db.commit()
    return True, "Decision recorded."


def update_decision(db: Session, row: models.CompanyDecision, actor_id: int | None,
                    status: str) -> None:
    status = status if status in DECISION_STATES else "open"
    row.status = status
    row.completed_at = _now() if status == "done" else None
    row.updated_at = _now()
    services_ops.record_audit(db, action="company.decision_status",
                              organization_id=row.organization_id, user_id=actor_id,
                              detail=f"Decision {row.id} -> {status}")
    db.commit()


def notes(db: Session, assessment_id: int) -> list[dict[str, Any]]:
    rows = list(db.scalars(select(models.AssessmentNote).where(
        models.AssessmentNote.assessment_id == assessment_id
    ).order_by(models.AssessmentNote.id.desc())))
    out = []
    for row in rows:
        author = db.get(models.User, row.user_id) if row.user_id else None
        out.append({"row": row, "author": author,
                    "initials": initials(author.name if author else "",
                                         author.email if author else "")})
    return out


def add_note(db: Session, assessment: models.Assessment, actor_id: int | None,
             section: str, body: str) -> tuple[bool, str]:
    body = (body or "").strip()[:3000]
    if not body:
        return False, "Write a note before saving."
    db.add(models.AssessmentNote(
        assessment_id=assessment.id, organization_id=assessment.organization_id,
        user_id=actor_id, section=(section or "Overall").strip()[:80] or "Overall",
        body=body, created_at=_now()))
    services_ops.record_audit(db, action="assessment.note",
                              organization_id=assessment.organization_id,
                              assessment_id=assessment.id, user_id=actor_id,
                              detail=f"Note on {section}")
    db.commit()
    return True, "Note saved."


def pulse(db: Session, organization_id: int) -> dict[str, Any]:
    overview = services.company_overview(db, db.get(models.Organization, organization_id))
    latest_score = 0.0
    for row in overview["rows"]:
        if row["status"] == "completed" and row["readiness_index"] is not None:
            latest_score = float(row["readiness_index"])
    actions = services_ops.action_items(db, [organization_id], limit=1000)
    total_actions = len(actions)
    done_actions = len([a for a in actions if a["status"] == "done"])
    overdue_actions = len([a for a in actions if a["overdue"]])
    action_score = 50 if not total_actions else round(
        100 * max(0, total_actions - overdue_actions) / total_actions)
    campaigns = list(db.scalars(select(models.CollectCampaign).where(
        models.CollectCampaign.organization_id == organization_id)))
    needed = 0
    got = 0
    for campaign in campaigns:
        needed += max(1, campaign.min_respondents or 1)
        got += db.scalar(select(func.count()).select_from(models.CollectResponse).where(
            models.CollectResponse.campaign_token == campaign.token,
            models.CollectResponse.status == "completed")) or 0
    participation = 70 if not campaigns else min(100, round(100 * got / needed))
    open_incidents = db.scalar(select(func.count()).select_from(models.OperationalIncident).where(
        models.OperationalIncident.organization_id == organization_id,
        models.OperationalIncident.status != "resolved")) or 0
    incident_score = max(0, 100 - int(open_incidents) * 20)
    soon = (_today() + timedelta(days=30)).isoformat()
    expiring = db.scalar(select(func.count()).select_from(models.ComplianceDocument).where(
        models.ComplianceDocument.organization_id == organization_id,
        models.ComplianceDocument.status == "active",
        models.ComplianceDocument.expires_on.is_not(None),
        models.ComplianceDocument.expires_on <= soon)) or 0
    compliance_score = max(0, 100 - int(expiring) * 25)
    members = member_rows(db, organization_id)
    team_score = min(100, 35 + len([m for m in members if m["status"] == "active"]) * 13)
    components = [
        {"key": "readiness", "label": "Operating readiness", "value": round(latest_score),
         "weight": 35, "note": "Latest completed diagnostic"},
        {"key": "actions", "label": "Action control", "value": action_score,
         "weight": 20, "note": f"{overdue_actions} overdue of {total_actions}"},
        {"key": "participation", "label": "Team participation", "value": participation,
         "weight": 15, "note": f"{got} of {needed} responses" if campaigns else "No live campaign"},
        {"key": "incidents", "label": "Incident load", "value": incident_score,
         "weight": 15, "note": f"{open_incidents} open incidents"},
        {"key": "compliance", "label": "Compliance cover", "value": compliance_score,
         "weight": 10, "note": f"{expiring} expiring in 30 days"},
        {"key": "team", "label": "Team depth", "value": team_score,
         "weight": 5, "note": f"{len(members)} members"},
    ]
    score = round(sum(c["value"] * c["weight"] for c in components) / 100)
    band = "strong" if score >= 75 else "watch" if score >= 50 else "risk"
    return {"score": score, "band": band, "components": components,
            "latest_score": latest_score, "actions": {"total": total_actions,
            "done": done_actions, "overdue": overdue_actions},
            "members": len(members), "campaigns": len(campaigns)}


def desk(db: Session, organization: models.Organization, days: int = 14) -> dict[str, Any]:
    today = _today()
    cutoff = today + timedelta(days=max(1, min(days, 60)))
    items: list[dict[str, Any]] = []
    for action in services_ops.action_items(db, [organization.id], limit=1000):
        due = _day(action["due_date"])
        if due and today <= due <= cutoff and action["status"] != "done":
            items.append({"date": due.isoformat(), "kind": "Action",
                          "title": action["title"], "owner": action["owner"] or "Unassigned",
                          "href": f"/actions?org={organization.id}",
                          "tone": "risk" if action["overdue"] else "watch"})
    for campaign in db.scalars(select(models.CollectCampaign).where(
            models.CollectCampaign.organization_id == organization.id)):
        due = _day(campaign.deadline)
        if due and today <= due <= cutoff and campaign.status == "collecting":
            items.append({"date": due.isoformat(), "kind": "Questionnaire",
                          "title": campaign.title or campaign.question_set or "Team questionnaire",
                          "owner": "Team", "href": f"/company/campaign/{campaign.token}",
                          "tone": "watch"})
    for assessment in db.scalars(select(models.Assessment).where(
            models.Assessment.organization_id == organization.id,
            models.Assessment.review_due_at.is_not(None))):
        due = _day(assessment.review_due_at)
        if due and today <= due <= cutoff:
            items.append({"date": due.isoformat(), "kind": "Review",
                          "title": f"Review {('department' if assessment.department_id else 'company')} diagnostic",
                          "owner": "Leadership",
                          "href": f"/assessment/{assessment.id}/results", "tone": "watch"})
    for document in db.scalars(select(models.ComplianceDocument).where(
            models.ComplianceDocument.organization_id == organization.id,
            models.ComplianceDocument.status == "active",
            models.ComplianceDocument.expires_on.is_not(None))):
        due = _day(document.expires_on)
        if due and today <= due <= cutoff:
            items.append({"date": due.isoformat(), "kind": "Compliance",
                          "title": document.title, "owner": document.owner or "Compliance",
                          "href": f"/operations?org={organization.id}", "tone": "risk"})
    for item in decisions(db, organization.id, limit=100):
        due = _day(item["row"].due_date)
        if due and today <= due <= cutoff and item["row"].status != "done":
            items.append({"date": due.isoformat(), "kind": "Decision",
                          "title": item["row"].title,
                          "owner": item["row"].owner_name or "Leadership",
                          "href": f"/company/{organization.id}/decisions",
                          "tone": "risk" if item["overdue"] else "watch"})
    items.sort(key=lambda row: (row["date"], row["kind"], row["title"]))
    huddle = _next_huddle(organization)
    return {"items": items, "days": days, "huddle": huddle,
            "workload": services_ops.owner_workload(db, [organization.id]),
            "today": today.isoformat()}


def _next_huddle(organization: models.Organization) -> dict[str, Any]:
    names = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
    target = (organization.huddle_day or "monday").lower()
    target_index = names.index(target) if target in names else 0
    today = _today()
    ahead = (target_index - today.weekday()) % 7
    if ahead == 0:
        ahead = 7
    day = today + timedelta(days=ahead)
    return {"date": day.isoformat(), "day": names[target_index].title(),
            "time": organization.huddle_time or "08:30"}


def activity(db: Session, organization_id: int, limit: int = 12) -> list[dict[str, Any]]:
    events = list(db.scalars(select(models.AuditEvent).where(
        models.AuditEvent.organization_id == organization_id
    ).order_by(models.AuditEvent.id.desc()).limit(limit)))
    out = []
    for event in events:
        actor = db.get(models.User, event.user_id) if event.user_id else None
        out.append({"at": event.created_at or "", "action": event.action,
                    "detail": event.detail or "", "actor": actor.name if actor else "System"})
    return out


def branding(organization: models.Organization | None) -> dict[str, str]:
    accent = (organization.accent_color or "#b45309") if organization else "#b45309"
    if not HEX.match(accent):
        accent = "#b45309"
    return {"accent": accent,
            "footer": (organization.report_footer or "").strip() if organization else "",
            "cover_note": (organization.report_cover_note or "").strip() if organization else ""}


def update_company_settings(db: Session, organization: models.Organization,
                            actor_id: int | None, *, accent_color: str,
                            report_footer: str, report_cover_note: str,
                            week_start: str, huddle_day: str,
                            huddle_time: str) -> tuple[bool, str]:
    accent = (accent_color or "").strip()
    if accent and not HEX.match(accent):
        return False, "Use a six-digit colour such as #b45309."
    organization.accent_color = accent or "#b45309"
    organization.report_footer = (report_footer or "").strip()[:240] or None
    organization.report_cover_note = (report_cover_note or "").strip()[:2000] or None
    organization.week_start = week_start if week_start in {"monday", "sunday"} else "monday"
    organization.huddle_day = (huddle_day if huddle_day in {
        "monday", "tuesday", "wednesday", "thursday", "friday"} else "monday")
    organization.huddle_time = (huddle_time or "08:30").strip()[:5]
    services_ops.record_audit(db, action="company.settings",
                              organization_id=organization.id, user_id=actor_id,
                              detail="Company workspace identity updated")
    db.commit()
    return True, "Company workspace settings saved."


def ics_escape(text: str) -> str:
    return (text or "").replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


def calendar(organization: models.Organization, schedule: dict[str, Any]) -> str:
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Elipsis//Company desk//EN",
             f"X-WR-CALNAME:{ics_escape(organization.name)} operating desk"]
    for item in schedule["items"]:
        day = item["date"].replace("-", "")
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{organization.id}-{day}-{abs(hash(item['title']))}@elipsis",
            f"DTSTAMP:{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART;VALUE=DATE:{day}",
            f"SUMMARY:{ics_escape(item['kind'] + ': ' + item['title'])}",
            f"DESCRIPTION:{ics_escape('Owner: ' + item['owner'])}",
            "END:VEVENT",
        ])
    huddle = schedule.get("huddle") or {}
    if huddle.get("date"):
        day = huddle["date"].replace("-", "")
        lines.extend([
            "BEGIN:VEVENT", f"UID:{organization.id}-huddle-{day}@elipsis",
            f"DTSTAMP:{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART;VALUE=DATE:{day}",
            f"SUMMARY:{ics_escape('Weekly operating huddle')}",
            "END:VEVENT",
        ])
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
