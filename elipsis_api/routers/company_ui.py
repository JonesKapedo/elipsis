"""Organisation workspace — companies, assessments, team questionnaires."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from elipsis_api import models, schemas, services
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user, login_redirect, templates

router = APIRouter()


def _not_found(request, user):
    return templates.TemplateResponse(request, "404.html", {"user": user}, status_code=404)


@router.get("/company")
def company_home(request: Request, user=Depends(get_current_user),
                 db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    orgs = services.owned_orgs(db, user)
    rows = []
    for org in orgs:
        overview = services.company_overview(db, org)
        assessments = overview.get("rows") or []
        rows.append({
            "org": org,
            "portrait": None,
            "latest": overview.get("latest"),
            "assessments": assessments,
            "campaigns": [],
        })
    return templates.TemplateResponse(
        request, "company.html",
        {"user": user, "rows": rows})


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
