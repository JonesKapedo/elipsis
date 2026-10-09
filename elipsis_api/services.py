"""Service layer: re-exports core + ext + signed session auth."""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from elipsis_api import models
from elipsis_api.services_core import (  # noqa: F401
    DEFAULT_ADMIN_EMAIL,
    DEFAULT_ADMIN_PASSWORD,
    DEMO_DEPARTMENTS,
    _now,
    _seed_admin,
    seed,
    get_bank,
    get_questions,
    create_assessment,
    answers_map,
    compute,
    save,
    submit,
    list_assessments as _list_assessments_raw,
)
from elipsis_api.services_ext import (  # noqa: F401
    dashboard_data as _dashboard_data_raw,
    reset_demo_data as _reset_demo_data_raw,
    create_share_link,
    resolve_share_token,
    list_organizations as _list_organizations_raw,
    department_comparison,
    run_guided_demo,
)
from elipsis_api.services_auth import (  # noqa: F401
    authenticate,
    register_user,
    create_session,
    user_for_token,
    delete_session,
    question_dicts,
    build_segments,
    live_scores,
    save_answers,
)


def is_admin(user) -> bool:
    if user is None:
        return False
    if (getattr(user, "role", "") or "") == "admin":
        return True
    admin_email = (os.getenv("ELIPSIS_ADMIN_EMAIL") or DEFAULT_ADMIN_EMAIL).lower()
    return (getattr(user, "email", "") or "").lower() == admin_email


def list_assessments(db: Session, org_ids: list[int] | None = None) -> list[dict[str, Any]]:
    rows = db.execute(
        select(models.Assessment, models.Organization.name, models.Department.name)
        .join(models.Organization, models.Organization.id == models.Assessment.organization_id)
        .join(models.Department, models.Department.id == models.Assessment.department_id, isouter=True)
        .order_by(models.Assessment.id.desc())
    ).all()
    out = []
    for a, org_name, dept_name in rows:
        if org_ids is not None and a.organization_id not in org_ids:
            continue
        out.append(dict(
            id=a.id, status=a.status, respondent=a.respondent,
            organization_id=a.organization_id,
            organization=org_name, department=dept_name,
            readiness_index=a.readiness_index, maturity_band=a.maturity_band,
            confidence_index=a.confidence_index, completed_at=a.completed_at,
            started_at=a.started_at,
        ))
    return out


def list_organizations(db: Session, org_ids: list[int] | None = None):
    rows = _list_organizations_raw(db)
    if org_ids is None:
        return rows
    if not org_ids:
        return []
    return [o for o in rows if o.id in org_ids]


def dashboard_data(db: Session, limit: int = 8, org_ids: list[int] | None = None) -> dict[str, Any]:
    rows = list_assessments(db, org_ids)
    completed = [r for r in rows if r.get("status") == "completed"
                 and r.get("readiness_index") is not None]
    pillar_totals: dict[str, list[float]] = {}
    for row in completed:
        for p in db.scalars(select(models.PillarScore).where(
                models.PillarScore.assessment_id == row["id"])):
            if p.score is None:
                continue
            bucket = pillar_totals.setdefault(p.pillar, [0.0, 0])
            bucket[0] += p.score
            bucket[1] += 1
    portfolio_pillars = {code: round(total / count, 1)
                         for code, (total, count) in pillar_totals.items() if count}
    scores = [r["readiness_index"] for r in completed]
    bands: dict[str, int] = {}
    for row in completed:
        band = row.get("maturity_band") or "Unknown"
        bands[band] = bands.get(band, 0) + 1
    summary = dict(
        total=len(rows),
        completed=len(completed),
        in_progress=len(rows) - len(completed),
        average=round(sum(scores) / len(scores), 1) if scores else None,
        best=max(scores) if scores else None,
        lowest=min(scores) if scores else None,
        bands=bands,
        savings=0,
    )
    return dict(summary=summary, rows=rows[:limit],
                portfolio_pillars=portfolio_pillars, all_completed=completed)


def reset_demo_data(db: Session, org_ids: list[int] | None = None):
    return _reset_demo_data_raw(db)


def owned_org_ids(db: Session, user) -> list[int]:
    if user is None:
        return []
    return list(db.scalars(select(models.OrgOwner.organization_id).where(
        models.OrgOwner.user_id == user.id)))


def owned_orgs(db: Session, user) -> list[models.Organization]:
    return list_organizations(db, owned_org_ids(db, user))


def claim_org(db: Session, user_id: int, organization_id: int) -> None:
    exists = db.scalar(select(models.OrgOwner).where(
        models.OrgOwner.user_id == user_id,
        models.OrgOwner.organization_id == organization_id))
    if exists is None:
        db.add(models.OrgOwner(user_id=user_id, organization_id=organization_id))
        db.commit()


def visible_org_ids(db: Session, user) -> list[int] | None:
    owned = owned_org_ids(db, user)
    if owned:
        return owned
    return None if is_admin(user) else []


def can_access_org(db: Session, user, organization_id: int | None) -> bool:
    if user is None or organization_id is None:
        return False
    if is_admin(user):
        return True
    return organization_id in owned_org_ids(db, user)


def company_overview(db: Session, org: models.Organization) -> dict[str, Any]:
    rows = list_assessments(db, [org.id])
    completed = sorted(
        [r for r in rows if r["status"] == "completed" and r.get("readiness_index") is not None],
        key=lambda r: (r.get("completed_at") or "", r["id"]),
    )
    latest = completed[-1] if completed else (rows[0] if rows else None)
    trend = [{"id": r["id"], "value": r.get("readiness_index") or 0,
              "label": r.get("completed_at") or r.get("started_at") or ""}
             for r in completed[-8:]]
    return {
        "rows": rows,
        "latest": latest,
        "trend": trend,
        "comparison": department_comparison(db, org.id) if completed else None,
    }
