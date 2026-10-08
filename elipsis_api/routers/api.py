"""JSON API router (/api/v1) — the primary programmatic interface."""

import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from constants import BRAND_NAME, INDEX_NAME, scale_options
from elipsis_api import models, schemas, services
from elipsis_api.config import DATABASE_URL, SESSION_COOKIE
from elipsis_api.database import get_db, ping_db
from elipsis_api.state import seed_status

router = APIRouter(prefix="/api/v1", tags=["api"])

_SECURE_COOKIE = os.getenv("VERCEL") == "1" or os.getenv("ELIPSIS_SECURE_COOKIE") == "1"


def _assessment_out(a):
    return schemas.AssessmentOut(
        id=a.id, organization_id=a.organization_id, department_id=a.department_id,
        questionnaire_id=a.questionnaire_id, respondent=a.respondent, status=a.status,
        readiness_index=a.readiness_index, maturity_band=a.maturity_band,
        confidence_index=a.confidence_index)


@router.get("/health", response_model=schemas.HealthOut)
def health():
    """Liveness + basic readiness. Never raises — used by monitors and Vercel."""
    db_ok = ping_db()
    seed = seed_status()
    status = "ok" if db_ok and seed.get("seed_ok") else "degraded"
    return schemas.HealthOut(
        status=status,
        brand=BRAND_NAME,
        index=INDEX_NAME,
        database=DATABASE_URL.split("://", 1)[0],
    )


@router.get("/health/detail")
def health_detail():
    """Richer health for operators (not for public load balancers)."""
    db_ok = ping_db()
    seed = seed_status()
    return {
        "status": "ok" if db_ok and seed.get("seed_ok") else "degraded",
        "database": DATABASE_URL.split("://", 1)[0],
        "database_reachable": db_ok,
        "seed_ok": seed.get("seed_ok"),
        "seed_error": seed.get("seed_error"),
    }


@router.get("/questionnaire", response_model=list[schemas.QuestionOut])
def questionnaire(db: Session = Depends(get_db)):
    bank = services.get_bank(db)
    if bank is None:
        raise HTTPException(status_code=503, detail="questionnaire not seeded")
    return [schemas.QuestionOut(
                id=q.id, code=q.code, scale=q.scale,
                options=[schemas.OptionOut(score=s, emoji=e, label=label, help=h)
                         for s, e, label, h in (scale_options(q.scale or "") or ())],
                subdomain=q.subdomain, pillar=q.pillar,
                text=q.text, why=q.why, weight=q.weight or 0,
                evidence_required=bool(q.evidence_required))
            for q in services.get_questions(db, bank.id)]


def _api_user(request: Request, db: Session):
    return services.user_for_token(db, request.cookies.get(SESSION_COOKIE))


@router.get("/assessments")
def list_assessments(request: Request, db: Session = Depends(get_db)):
    user = _api_user(request, db)
    return services.list_assessments(db, services.visible_org_ids(db, user) if user else None)


@router.post("/assessments", response_model=schemas.AssessmentOut, status_code=201)
def create_assessment(payload: schemas.AssessmentIn, request: Request,
                      db: Session = Depends(get_db)):
    user = _api_user(request, db)
    if user and payload.organization_id and not services.can_access_org(
            db, user, payload.organization_id):
        raise HTTPException(status_code=404, detail="organization not found")
    try:
        assessment = services.create_assessment(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if user is not None:
        services.claim_org(db, user.id, assessment.organization_id)
    return _assessment_out(assessment)


@router.get("/assessments/{assessment_id}/analytics")
def assessment_analytics(assessment_id: int, db: Session = Depends(get_db)):
    from elipsis_api import analytics
    _, result = services.compute(db, assessment_id)
    if result is None:
        raise HTTPException(status_code=404, detail="assessment not found")
    return analytics.build(result)


@router.get("/organizations/{organization_id}/overview")
def organization_overview(organization_id: int, request: Request,
                          db: Session = Depends(get_db)):
    user = _api_user(request, db)
    if user is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    org = db.get(models.Organization, organization_id)
    if org is None or not services.can_access_org(db, user, organization_id):
        raise HTTPException(status_code=404, detail="organization not found")
    data = services.company_overview(db, org)
    data["organization"] = {"id": org.id, "name": org.name, "industry": org.industry,
                            "employee_count": org.employee_count, "city": org.city,
                            "country": org.country}
    return data


@router.get("/assessments/{assessment_id}")
def assessment_result(assessment_id: int, db: Session = Depends(get_db)):
    assessment, result = services.compute(db, assessment_id)
    if assessment is None or result is None:
        raise HTTPException(status_code=404, detail="assessment not found")
    return result


@router.get("/assessments/{assessment_id}/results")
def assessment_results(assessment_id: int, db: Session = Depends(get_db)):
    return assessment_result(assessment_id, db)


@router.get("/assessments/{assessment_id}/report")
def assessment_report(assessment_id: int, db: Session = Depends(get_db)):
    return assessment_result(assessment_id, db)


@router.post("/assessments/{assessment_id}/submit")
def assessment_submit(assessment_id: int, payload: schemas.SubmitIn,
                      db: Session = Depends(get_db)):
    try:
        _, result = services.submit(db, assessment_id, payload.answers)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="assessment not found")
    return result


@router.post("/auth/login", response_model=schemas.LoginOut)
def login(payload: schemas.LoginIn, response: Response, db: Session = Depends(get_db)):
    user = services.authenticate(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = services.create_session(db, user.id)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        secure=_SECURE_COOKIE,
        max_age=60 * 60 * 24 * 14,
    )
    return schemas.LoginOut(
        token=token,
        user=schemas.AuthOut(
            user_id=user.id,
            email=user.email,
            name=user.name or "",
            role=user.role or "client",
            token=token,
        ),
    )


@router.get("/auth/me", response_model=schemas.AuthOut)
def me(request: Request, db: Session = Depends(get_db)):
    user = services.user_for_token(db, request.cookies.get(SESSION_COOKIE))
    if user is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    return schemas.AuthOut(
        user_id=user.id,
        email=user.email,
        name=user.name or "",
        role=user.role or "client",
        token=request.cookies.get(SESSION_COOKIE) or "",
    )


@router.post("/auth/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    services.delete_session(db, request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE)
    return JSONResponse(content={"ok": True})
