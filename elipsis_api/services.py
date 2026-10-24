"""Service layer: re-exports core + ext + signed session auth."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from elipsis_api import models
from elipsis_api import services_ext as _services_ext
from elipsis_api.permissions import (  # noqa: F401
    ADMIN_ROLES,
    ROLE_LABELS,
    ROLE_LEVELS,
    can_access_org,
    can_contribute_org,
    can_manage_org,
    company_is_pro,
    is_admin,
    is_pro_user,
    is_super_admin,
    org_membership,
    org_role,
    owned_org_ids,
    visible_org_ids,
)
from elipsis_api.services_auth import (  # noqa: F401
    authenticate,
    build_segments,
    create_session,
    delete_session,
    live_scores,
    question_dicts,
    register_user,
    save_answers,
    user_for_token,
)
from elipsis_api.services_core import (  # noqa: F401
    DEFAULT_ADMIN_EMAIL,
    DEFAULT_ADMIN_PASSWORD,
    DEMO_DEPARTMENTS,
    _now,
    _seed_admin,
    answers_map,
    compute,
    compute_scenario,
    create_assessment,
    create_collect_campaign,
    ensure_plan_items,
    get_assumptions,
    get_bank,
    get_questions,
    previous_assessment,
    questionnaire_for_department,
    save,
    save_assumptions,
    seed,
    submit,
    update_plan_item,
)
from elipsis_api.services_ext import (  # noqa: F401
    dashboard_data as _dashboard_data_raw,
)
from elipsis_api.services_ext import (
    department_comparison,
)
from elipsis_api.services_ext import (
    list_organizations as _list_organizations_raw,
)
from elipsis_api.services_ext import (
    reset_demo_data as _reset_demo_data_raw,
)
from elipsis_api.services_ext import (
    run_guided_demo as run_guided_demo,
)


def user_prefs(db: Session, user) -> models.UserPref:
    if user is None:
        raise ValueError("user required")
    row = db.get(models.UserPref, user.id)
    if row is None:
        row = models.UserPref(user_id=user.id, symbol=(user.name or user.email or "E")[:1].upper())
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


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
    return _reset_demo_data_raw(db, org_ids)


def owned_orgs(db: Session, user) -> list[models.Organization]:
    return list_organizations(db, owned_org_ids(db, user))


def claim_org(db: Session, user_id: int, organization_id: int) -> None:
    exists = db.scalar(select(models.OrgOwner).where(
        models.OrgOwner.user_id == user_id,
        models.OrgOwner.organization_id == organization_id))
    if exists is None:
        db.add(models.OrgOwner(user_id=user_id, organization_id=organization_id,
                               role="owner", status="active"))
        db.commit()
    elif (exists.status or "active") != "active":
        exists.status = "active"
        db.commit()


def company_completeness(org: models.Organization | None) -> dict[str, Any]:
    fields = (
        "name", "industry", "sub_industry", "employee_count", "revenue_band",
        "country", "city", "legal_name", "registration_number", "website",
        "contact_name", "contact_email", "contact_phone", "address",
        "operating_sites", "primary_services", "systems_used",
    )
    if org is None:
        return {"percent": 0, "complete": 0, "total": len(fields), "missing": list(fields)}
    missing = [name for name in fields if not getattr(org, name, None)]
    complete = len(fields) - len(missing)
    return {
        "percent": round(complete / len(fields) * 100),
        "complete": complete,
        "total": len(fields),
        "missing": missing,
        "is_complete": not missing,
    }


def company_context(org: models.Organization | None) -> dict[str, Any] | None:
    """Human-readable company profile used to tailor every operating page."""
    if org is None:
        return None
    employees = org.employee_count
    if employees is None:
        size = "Scale not set"
    elif employees < 50:
        size = "Small operator"
    elif employees < 200:
        size = "Mid-sized operator"
    elif employees < 1000:
        size = "Large operator"
    else:
        size = "Enterprise network"
    sector = (org.sub_industry or org.industry or "Logistics").strip()
    location = ", ".join(part for part in (org.city, org.country) if part) or "Footprint not set"
    revenue = (org.revenue_band or "").strip() or "Revenue band not set"
    return {
        "name": org.name,
        "sector": sector,
        "industry": org.industry or "Logistics",
        "sub_industry": org.sub_industry or "",
        "size": size,
        "employees": employees,
        "revenue": revenue,
        "location": location,
        "country": org.country or "",
        "city": org.city or "",
        "legal_name": org.legal_name or "",
        "website": org.website or "",
        "contact_name": org.contact_name or "",
        "contact_email": org.contact_email or "",
        "contact_phone": org.contact_phone or "",
        "operating_sites": org.operating_sites or "",
        "primary_services": org.primary_services or "",
        "systems_used": org.systems_used or "",
        "completeness": company_completeness(org),
    }


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


# Explicit re-exports for the server-rendered share routes.
create_share_link = _services_ext.create_share_link
resolve_share_token = _services_ext.resolve_share_token
