"""Organisation workspace — companies, assessments, team questionnaires."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from constants import PILLAR_LABELS
from elipsis_api import models, narrative, schemas, services, services_room
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user, login_redirect, templates

router = APIRouter()


def _not_found(request, user):
    return templates.TemplateResponse(request, "404.html", {"user": user}, status_code=404)


def _campaign_rows(db: Session, organization_id: int) -> list[dict]:
    rows = db.scalars(select(models.CollectCampaign).where(
        models.CollectCampaign.organization_id == organization_id
    ).order_by(models.CollectCampaign.created_at.desc())).all()
    out = []
    for campaign in rows:
        completed = db.scalar(select(func.count()).select_from(models.CollectResponse).where(
            models.CollectResponse.campaign_token == campaign.token,
            models.CollectResponse.status == "completed")) or 0
        out.append({
            "token": campaign.token,
            "title": campaign.title,
            "question_set": campaign.question_set,
            "deadline": campaign.deadline,
            "min_respondents": campaign.min_respondents,
            "completed": completed,
            "status": campaign.status or "collecting",
        })
    return out


def _company_focus(db: Session, org: models.Organization) -> dict:
    overview = services.company_overview(db, org)
    context = services.company_context(org)
    latest = overview.get("latest")
    portrait = None
    pillars = []
    if latest and latest.get("status") == "completed":
        _, result = services.compute(db, latest["id"])
        if result:
            portrait = narrative.company_portrait(org, None, result)
            raw = result.get("pillars") or {}
            if isinstance(raw, dict):
                pillars = [{"code": code, "label": PILLAR_LABELS.get(code, code),
                            "score": score} for code, score in raw.items()]
            else:
                pillars = list(raw)
            pillars.sort(key=lambda row: row.get("score") or 0)
    members = services_room.member_rows(db, org.id)
    return {
        "org": org,
        "context": context,
        "overview": overview,
        "latest": latest,
        "portrait": portrait,
        "pillars": pillars,
        "assessments": overview.get("rows") or [],
        "campaigns": _campaign_rows(db, org.id),
        "members": len([m for m in members if m.get("status") == "active"]),
        "activity": services_room.activity(db, org.id, 8),
    }


@router.get("/company")
def company_home(request: Request, user=Depends(get_current_user),
                 db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    orgs = services.owned_orgs(db, user)
    selected_id = (request.query_params.get("org") or "").strip()
    focus_org = next((org for org in orgs if str(org.id) == selected_id), None)
    if focus_org is None and orgs:
        focus_org = orgs[0]
    focus = None
    if focus_org is not None:
        try:
            focus = _company_focus(db, focus_org)
        except Exception as exc:  # noqa: BLE001
            print(f"[elipsis] company home failed for org {focus_org.id}: {exc}", flush=True)
    peers = []
    for org in orgs:
        if focus_org is not None and org.id == focus_org.id:
            continue
        peers.append({
            "org": org,
            "context": services.company_context(org),
            "pulse": services_room.pulse(db, org.id),
        })
    return templates.TemplateResponse(
        request, "company.html",
        {"user": user, "focus": focus, "peers": peers,
         "limited": len(orgs) > 1 and not services.is_pro_user(db, user)})


@router.post("/company")
def company_create(
    request: Request,
    name: str = Form(...),
    industry: str = Form(""),
    employee_count: str = Form(""),
    city: str = Form(""),
    country: str = Form(""),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user is None:
        return login_redirect()
    name = (name or "").strip()[:200]
    if not name:
        return RedirectResponse("/company", status_code=303)
    if services.owned_orgs(db, user) and not services.is_pro_user(db, user):
        return RedirectResponse("/pro?locked=companies", status_code=303)
    emp = None
    if (employee_count or "").strip().isdigit():
        emp = int(employee_count)
    org = models.Organization(
        name=name,
        industry=(industry or "").strip()[:120] or None,
        employee_count=emp,
        city=(city or "").strip()[:120] or None,
        country=(country or "").strip()[:120] or None,
        user_id=user.id,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    services.claim_org(db, user.id, org.id)
    return RedirectResponse(f"/company#org-{org.id}", status_code=303)


@router.post("/company/{organization_id}/assess")
def company_start_assessment(
    organization_id: int,
    request: Request,
    department: str = Form("Organisation-wide"),
    respondent: str = Form(""),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user is None:
        return login_redirect()
    if not services.can_access_org(db, user, organization_id):
        return _not_found(request, user)
    try:
        payload = schemas.AssessmentIn(
            organization_id=organization_id,
            department=(department or "Organisation-wide").strip(),
            respondent=(respondent or "").strip() or (user.name or user.email),
        )
        assessment = services.create_assessment(db, payload)
        services.claim_org(db, user.id, organization_id)
    except Exception as exc:  # noqa: BLE001
        print(f"[elipsis] company assess failed: {exc}", flush=True)
        return RedirectResponse("/company", status_code=303)
    return RedirectResponse(f"/assessment/{assessment.id}/step/1", status_code=303)


@router.post("/company/{organization_id}/share")
def company_share_placeholder(
    organization_id: int,
    request: Request,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user is None:
        return login_redirect()
    if not services.can_access_org(db, user, organization_id):
        return _not_found(request, user)
    return RedirectResponse(f"/company#org-{organization_id}", status_code=303)
