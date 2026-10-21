"""Workspace intelligence: action execution, trends, audit, sharing, team."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from elipsis_api import models
from elipsis_api.services_core import _now


def _today() -> date:
    return date.today()


def _parse_day(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def action_items(db: Session, org_ids: list[int] | None = None, *,
                 status: str | None = None, owner: str | None = None,
                 overdue_only: bool = False, limit: int = 100) -> list[dict[str, Any]]:
    query = (
        select(models.RoadmapItem, models.Assessment, models.Organization.name,
               models.Department.name)
        .join(models.Assessment, models.Assessment.id == models.RoadmapItem.assessment_id)
        .join(models.Organization, models.Organization.id == models.Assessment.organization_id)
        .outerjoin(models.Department, models.Department.id == models.Assessment.department_id)
        .order_by(models.RoadmapItem.due_date, models.RoadmapItem.id)
    )
    if org_ids is not None:
        if not org_ids:
            return []
        query = query.where(models.Assessment.organization_id.in_(org_ids))
    if status:
        if status == "open":
            query = query.where((models.RoadmapItem.status.is_(None))
                                | (models.RoadmapItem.status != "done"))
        else:
            query = query.where(models.RoadmapItem.status == status)
    if owner:
        query = query.where(models.RoadmapItem.owner.ilike(f"%{owner.strip()}%"))
    rows = db.execute(query).all()
    today = _today()
    out = []
    for item, _assessment, org_name, dept_name in rows:
        state = item.status or "not_started"
        due = _parse_day(item.due_date)
        is_overdue = bool(due and due < today and state != "done")
        if overdue_only and not is_overdue:
            continue
        out.append({
            "id": item.id,
            "assessment_id": item.assessment_id,
            "title": item.title,
            "owner": item.owner,
            "owner_phone": item.owner_phone,
            "due_date": item.due_date,
            "status": state,
            "notes": item.notes,
            "priority": item.priority,
            "horizon": item.horizon,
            "organization": org_name,
            "department": dept_name or "Organisation-wide",
            "overdue": is_overdue,
            "due_soon": bool(due and today <= due <= today + timedelta(days=14)
                             and state != "done"),
        })
        if len(out) >= limit:
            break
    return out


def action_summary(db: Session, org_ids: list[int] | None = None) -> dict[str, Any]:
    items = action_items(db, org_ids, limit=1000)
    done = sum(1 for i in items if i["status"] == "done")
    blocked = sum(1 for i in items if i["status"] == "blocked")
    overdue = sum(1 for i in items if i["overdue"])
    due_soon = sum(1 for i in items if i["due_soon"])
    open_items = len(items) - done
    return {
        "total": len(items),
        "open": open_items,
        "done": done,
        "blocked": blocked,
        "overdue": overdue,
        "due_soon": due_soon,
        "completion_pct": round(100 * done / len(items), 1) if items else 0.0,
        "next": [i for i in items if i["status"] != "done"][:6],
    }


def org_trends(db: Session, org_ids: list[int] | None = None) -> list[dict[str, Any]]:
    query = select(models.Organization).order_by(models.Organization.name)
    if org_ids is not None:
        if not org_ids:
            return []
        query = query.where(models.Organization.id.in_(org_ids))
    out = []
    for org in db.scalars(query):
        rows = list(db.scalars(
            select(models.Assessment).where(
                models.Assessment.organization_id == org.id,
                models.Assessment.status == "completed",
                models.Assessment.readiness_index.is_not(None),
            ).order_by(models.Assessment.completed_at, models.Assessment.id)
        ))[-12:]
        points = []
        previous = None
        for row in rows:
            value = round(float(row.readiness_index), 1)
            points.append({
                "id": row.id,
                "value": value,
                "label": (row.completed_at or row.started_at or "")[:10],
                "delta": None if previous is None else round(value - previous, 1),
            })
            previous = value
        out.append({"org": org, "points": points,
                    "latest": points[-1] if points else None,
                    "movement": round(points[-1]["value"] - points[0]["value"], 1)
                    if len(points) > 1 else None})
    return out


def notifications(db: Session, user) -> list[dict[str, Any]]:
    from elipsis_api.services import visible_org_ids

    org_ids = visible_org_ids(db, user)
    out = []
    for item in action_items(db, org_ids, limit=500):
        if item["status"] == "done":
            continue
        if item["overdue"]:
            out.append({
                "kind": "overdue", "severity": "danger",
                "title": item["title"],
                "detail": f"{item['organization']} · due {item['due_date']}",
                "url": f"/assessment/{item['assessment_id']}/plan",
                "ref": f"action:{item['id']}",
            })
        elif item["due_soon"]:
            out.append({
                "kind": "due_soon", "severity": "warn",
                "title": item["title"],
                "detail": f"{item['organization']} · due {item['due_date']}",
                "url": f"/assessment/{item['assessment_id']}/plan",
                "ref": f"action:{item['id']}",
            })
    query = select(models.Assessment).where(
        models.Assessment.review_due_at.is_not(None),
        models.Assessment.status == "completed",
    )
    if org_ids is not None:
        if not org_ids:
            query = query.where(False)
        else:
            query = query.where(models.Assessment.organization_id.in_(org_ids))
    today = _today()
    for row in db.scalars(query):
        due = _parse_day(row.review_due_at)
        if due and due <= today + timedelta(days=7):
            org = db.get(models.Organization, row.organization_id)
            out.append({
                "kind": "review", "severity": "warn" if due <= today else "info",
                "title": "Re-assessment due",
                "detail": f"{org.name if org else 'Organisation'} · {row.review_due_at}",
                "url": f"/assessment/{row.id}/results",
                "ref": f"review:{row.id}",
            })
    from elipsis_api import services_operations
    out.extend(services_operations.notifications(db, org_ids))
    return out[:16]


def share_links(db: Session, assessment_id: int) -> list[models.ShareLink]:
    return list(db.scalars(select(models.ShareLink).where(
        models.ShareLink.assessment_id == assessment_id
    ).order_by(models.ShareLink.created_at.desc())))


def touch_share_link(db: Session, link: models.ShareLink) -> None:
    link.view_count = int(link.view_count or 0) + 1
    link.last_viewed_at = _now()
    db.commit()


def revoke_share_link(db: Session, assessment_id: int, token: str) -> bool:
    row = db.get(models.ShareLink, token)
    if row is None or row.assessment_id != assessment_id:
        return False
    db.delete(row)
    db.commit()
    return True


def record_audit(db: Session, *, action: str, organization_id: int | None = None,
                 assessment_id: int | None = None, user_id: int | None = None,
                 detail: str | None = None) -> models.AuditEvent:
    row = models.AuditEvent(
        action=action[:80], organization_id=organization_id,
        assessment_id=assessment_id, user_id=user_id,
        detail=(detail or "").strip()[:2000] or None, created_at=_now())
    db.add(row)
    db.flush()
    return row


def audit_events(db: Session, org_ids: list[int] | None = None,
                 limit: int = 100) -> list[dict[str, Any]]:
    query = select(models.AuditEvent).order_by(models.AuditEvent.id.desc()).limit(limit)
    if org_ids is not None:
        if not org_ids:
            return []
        query = query.where(models.AuditEvent.organization_id.in_(org_ids))
    out = []
    for row in db.scalars(query):
        org = db.get(models.Organization, row.organization_id) if row.organization_id else None
        user = db.get(models.User, row.user_id) if row.user_id else None
        out.append({"event": row, "organization": org, "user": user})
    return out


def search_workspace(db: Session, org_ids: list[int] | None, query: str,
                     limit: int = 8) -> dict[str, Any]:
    """Search the parts of the workspace a user can actually open."""
    q = (query or "").strip()
    out: dict[str, Any] = {
        "query": q, "organizations": [], "assessments": [], "actions": [],
        "operations": [], "total": 0,
    }
    if len(q) < 2:
        return out
    like = f"%{q}%"

    org_query = (
        select(models.Organization)
        .where(models.Organization.name.ilike(like))
        .order_by(models.Organization.name)
        .limit(limit)
    )
    if org_ids is not None:
        if not org_ids:
            return out
        org_query = org_query.where(models.Organization.id.in_(org_ids))
    out["organizations"] = [
        {"org": org, "url": f"/company/{org.id}"} for org in db.scalars(org_query)
    ]

    assessment_query = (
        select(models.Assessment, models.Organization, models.Department)
        .join(models.Organization, models.Organization.id == models.Assessment.organization_id)
        .outerjoin(models.Department, models.Department.id == models.Assessment.department_id)
        .where(or_(
            models.Organization.name.ilike(like),
            models.Department.name.ilike(like),
            models.Assessment.respondent.ilike(like),
            models.Assessment.status.ilike(like),
        ))
        .order_by(models.Assessment.id.desc())
        .limit(limit)
    )
    if org_ids is not None:
        assessment_query = assessment_query.where(
            models.Assessment.organization_id.in_(org_ids))
    out["assessments"] = [
        {"assessment": assessment, "organization": org, "department": dept,
         "url": f"/assessment/{assessment.id}/results"}
        for assessment, org, dept in db.execute(assessment_query).all()
    ]

    action_query = (
        select(models.RoadmapItem, models.Assessment, models.Organization.name,
               models.Department.name)
        .join(models.Assessment, models.Assessment.id == models.RoadmapItem.assessment_id)
        .join(models.Organization, models.Organization.id == models.Assessment.organization_id)
        .outerjoin(models.Department, models.Department.id == models.Assessment.department_id)
        .where(or_(
            models.RoadmapItem.title.ilike(like),
            models.RoadmapItem.owner.ilike(like),
            models.RoadmapItem.notes.ilike(like),
        ))
        .order_by(models.RoadmapItem.due_date, models.RoadmapItem.id)
        .limit(limit)
    )
    if org_ids is not None:
        action_query = action_query.where(
            models.Assessment.organization_id.in_(org_ids))
    out["actions"] = [
        {"item": item, "assessment_id": assessment.id, "organization": org_name,
         "department": dept_name,
         "url": f"/assessment/{assessment.id}/plan"}
        for item, assessment, org_name, dept_name in db.execute(action_query).all()
    ]
    from elipsis_api import services_operations
    out["operations"] = services_operations.search_operations(db, org_ids, q, limit=limit)
    out["total"] = (len(out["organizations"]) + len(out["assessments"])
                    + len(out["actions"]) + len(out["operations"]))
    return out


def team_members(db: Session, organization_id: int) -> list[dict[str, Any]]:
    rows = db.execute(
        select(models.OrgOwner, models.User)
        .join(models.User, models.User.id == models.OrgOwner.user_id)
        .where(models.OrgOwner.organization_id == organization_id)
        .order_by(models.User.email)
    ).all()
    return [{"link": link, "user": user} for link, user in rows]


def add_team_member(db: Session, organization_id: int, email: str,
                    actor_id: int | None) -> tuple[bool, str]:
    email = (email or "").strip().lower()
    user = db.scalar(select(models.User).where(models.User.email == email))
    if user is None:
        return False, "That email is not registered yet. Ask them to create an account first."
    exists = db.scalar(select(models.OrgOwner).where(
        models.OrgOwner.organization_id == organization_id,
        models.OrgOwner.user_id == user.id))
    if exists is not None:
        return False, "That person is already on this organisation."
    db.add(models.OrgOwner(user_id=user.id, organization_id=organization_id))
    record_audit(db, action="team.add", organization_id=organization_id,
                 user_id=actor_id, detail=f"Added {email}")
    db.commit()
    return True, f"Added {email}."


def remove_team_member(db: Session, organization_id: int, user_id: int,
                       actor_id: int | None) -> tuple[bool, str]:
    owners = list(db.scalars(select(models.OrgOwner).where(
        models.OrgOwner.organization_id == organization_id)))
    if len(owners) <= 1:
        return False, "Keep at least one owner on the organisation."
    row = next((o for o in owners if o.user_id == user_id), None)
    if row is None:
        return False, "That person is not on this organisation."
    db.delete(row)
    record_audit(db, action="team.remove", organization_id=organization_id,
                 user_id=actor_id, detail=f"Removed user {user_id}")
    db.commit()
    return True, "Removed."


def set_review(db: Session, assessment: models.Assessment, due_at: str,
               note: str, actor_id: int | None) -> None:
    assessment.review_due_at = (due_at or "").strip()[:10] or None
    assessment.review_note = (note or "").strip()[:2000] or None
    record_audit(db, action="assessment.review", assessment_id=assessment.id,
                 organization_id=assessment.organization_id, user_id=actor_id,
                 detail=f"Review due {assessment.review_due_at}")
    db.commit()


def owner_workload(db: Session, org_ids: list[int] | None = None) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for item in action_items(db, org_ids, limit=2000):
        name = (item.get("owner") or "").strip() or "Unassigned"
        row = buckets.setdefault(name, {
            "owner": name, "open": 0, "done": 0, "overdue": 0,
            "due_soon": 0, "total": 0,
        })
        row["total"] += 1
        if item["status"] == "done":
            row["done"] += 1
        else:
            row["open"] += 1
        if item["overdue"]:
            row["overdue"] += 1
        if item["due_soon"]:
            row["due_soon"] += 1
    rows = list(buckets.values())
    rows.sort(key=lambda r: (-r["overdue"], -r["open"], r["owner"].lower()))
    return rows


def saved_views(db: Session, user) -> list[models.SavedView]:
    if user is None:
        return []
    return list(db.scalars(select(models.SavedView).where(
        models.SavedView.user_id == user.id
    ).order_by(models.SavedView.created_at.desc(), models.SavedView.id.desc())))


def save_view(db: Session, user, name: str, query: str) -> models.SavedView | None:
    if user is None:
        return None
    clean = (name or "").strip()[:60]
    if not clean:
        return None
    query = (query or "").strip()[:500]
    existing = db.scalar(select(models.SavedView).where(
        models.SavedView.user_id == user.id,
        models.SavedView.name == clean))
    if existing:
        existing.query = query
        db.commit()
        return existing
    row = models.SavedView(user_id=user.id, name=clean, query=query)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_view(db: Session, user, view_id: int) -> bool:
    if user is None:
        return False
    row = db.get(models.SavedView, view_id)
    if row is None or row.user_id != user.id:
        return False
    db.delete(row)
    db.commit()
    return True


def notification_fingerprint(item: dict[str, Any]) -> str:
    return str(item.get("ref") or f"{item.get('kind')}:{item.get('url')}:{item.get('title')}")


def read_fingerprints(db: Session, user) -> set[str]:
    if user is None:
        return set()
    return set(db.scalars(select(models.NotificationRead.fingerprint).where(
        models.NotificationRead.user_id == user.id)))


def mark_notifications_read(db: Session, user, fingerprints: list[str]) -> int:
    if user is None:
        return 0
    existing = read_fingerprints(db, user)
    count = 0
    for fingerprint in fingerprints:
        fingerprint = (fingerprint or "").strip()[:300]
        if not fingerprint or fingerprint in existing:
            continue
        db.add(models.NotificationRead(
            user_id=user.id, fingerprint=fingerprint, read_at=_now()))
        count += 1
    db.commit()
    return count
