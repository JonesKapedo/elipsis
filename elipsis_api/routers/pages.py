"""Server-rendered pages (Jinja2) — the human interface."""

import os

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from elipsis_api import analytics, models, schemas, services
from elipsis_api.config import SESSION_COOKIE
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user, login_redirect, templates
from constants import SUBDOMAIN_PILLAR
from elipsis_api.sample import SAMPLE_ORG, sample_result

router = APIRouter()

_SECURE_COOKIE = os.getenv("VERCEL") == "1" or os.getenv("ELIPSIS_SECURE_COOKIE") == "1"
_COOKIE_MAX_AGE = 60 * 60 * 24 * 14


def _not_found(request, user):
    return templates.TemplateResponse(request, "404.html", {"user": user},
                                      status_code=404)


def _owned_assessment(db: Session, user, assessment_id: int):
    """Return the assessment only if this user may see its company."""
    assessment = db.get(models.Assessment, assessment_id)
    if assessment is None or not services.can_access_org(db, user, assessment.organization_id):
        return None
    return assessment


def _int_param(request: Request, name: str) -> int | None:
    raw = request.query_params.get(name) or ""
    return int(raw) if raw.isdigit() else None


def _question_count(db: Session) -> int:
    try:
        bank = services.get_bank(db)
        if bank is None:
            return 0
        return int(db.scalar(select(func.count()).select_from(models.Question).where(
            models.Question.questionnaire_id == bank.id)) or 0)
    except Exception:  # noqa: BLE001
        return 0


def _set_session_cookie(response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE, token, httponly=True, samesite="lax",
        secure=_SECURE_COOKIE, max_age=_COOKIE_MAX_AGE, path="/",
    )


@router.get("/")
def landing(request: Request, user=Depends(get_current_user),
            db: Session = Depends(get_db)):
    if user is not None:
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(
        request, "landing.html",
        {"user": user, "total_questions": _question_count(db)})


@router.get("/sample")
def sample_report(request: Request, user=Depends(get_current_user)):
    result = sample_result()
    return templates.TemplateResponse(
        request, "sample.html",
        {"user": user, "result": result, "org": SAMPLE_ORG})


@router.get("/pricing")
def pricing(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse(request, "pricing.html", {"user": user})


@router.get("/methodology")
def methodology(request: Request, user=Depends(get_current_user),
                db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request, "methodology.html",
        {"user": user, "total_questions": _question_count(db) or 63})


@router.get("/faq")
def faq(request: Request, user=Depends(get_current_user),
        db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request, "faq.html",
        {"user": user, "total_questions": _question_count(db) or 63})


@router.get("/use-cases")
def use_cases(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse(request, "use_cases.html", {"user": user})


@router.get("/about")
def about(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse(request, "about.html", {"user": user})


@router.get("/contact")
def contact_get(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse(
        request, "contact.html",
        {"user": user, "sent": False, "error": None, "form": None})


@router.post("/contact")
def contact_post(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    organization: str = Form(""),
    topic: str = Form("other"),
    message: str = Form(...),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    name = (name or "").strip()[:120]
    email = (email or "").strip().lower()[:200]
    organization = (organization or "").strip()[:200] or None
    topic = (topic or "other").strip()[:40]
    message = (message or "").strip()[:4000]
    form = {"name": name, "email": email, "organization": organization or "",
            "message": message}
    if not name or not email or not message or "@" not in email:
        return templates.TemplateResponse(
            request, "contact.html",
            {"user": user, "sent": False,
             "error": "Please provide a valid name, email, and message.",
             "form": form},
            status_code=400)
    try:
        db.add(models.ContactMessage(
            name=name, email=email, organization=organization,
            topic=topic, message=message))
        db.commit()
    except Exception as exc:  # noqa: BLE001
        print(f"[elipsis] contact save failed: {exc}", flush=True)
        return templates.TemplateResponse(
            request, "contact.html",
            {"user": user, "sent": False,
             "error": "Could not send your message. Please try again.",
             "form": form},
            status_code=500)
    return templates.TemplateResponse(
        request, "contact.html",
        {"user": user, "sent": True, "error": None, "form": None})


@router.get("/demo")
def demo_get(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse(
        request, "demo.html",
        {"user": user, "sent": False, "error": None, "form": None})


@router.post("/demo")
def demo_post(request: Request, name: str = Form(...), email: str = Form(...),
              organization: str = Form(""), message: str = Form(""),
              user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    try:
        db.add(models.ContactMessage(
            name=(name or "").strip()[:120],
            email=(email or "").strip().lower()[:200],
            organization=(organization or "").strip()[:200] or None,
            topic="demo",
            message=(message or "").strip()[:4000] or "Demo request",
        ))
        db.commit()
    except Exception as exc:  # noqa: BLE001
        print(f"[elipsis] demo request failed: {exc}", flush=True)
        return templates.TemplateResponse(
            request, "demo.html",
            {"user": user, "sent": False, "error": "Could not submit. Try again.",
             "form": {"name": name, "email": email, "organization": organization}},
            status_code=500)
    return templates.TemplateResponse(
        request, "demo.html",
        {"user": user, "sent": True, "error": None, "form": None})


@router.get("/compare")
def compare(request: Request, user=Depends(get_current_user),
            db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    visible = services.visible_org_ids(db, user)
    rows = services.list_assessments(db, visible)
    completed = [r for r in rows if r.get("status") == "completed"]
    return templates.TemplateResponse(
        request, "compare.html",
        {"user": user, "rows": completed,
         "organizations": services.list_organizations(db, visible)})


@router.get("/compare/{organization_id}")
def compare_org(organization_id: int, request: Request,
                user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not services.can_access_org(db, user, organization_id):
        return _not_found(request, user)
    org = db.get(models.Organization, organization_id)
    overview = services.company_overview(db, org)
    return templates.TemplateResponse(
        request, "compare.html",
        {"user": user, "org": org, "overview": overview,
         "rows": overview.get("rows") or [],
         "organizations": services.list_organizations(
             db, services.visible_org_ids(db, user))})


@router.get("/share/{token}")
def share_view(token: str, request: Request, db: Session = Depends(get_db)):
    link = services.resolve_share_token(db, token)
    if link is None:
        return _not_found(request, None)
    assessment, result = services.compute(db, link.assessment_id)
    if assessment is None or result is None:
        return _not_found(request, None)
    org = db.get(models.Organization, assessment.organization_id)
    return templates.TemplateResponse(
        request, "share.html",
        {"user": None, "result": result, "assessment": assessment, "org": org,
         "token": token})


@router.post("/assessment/{assessment_id}/share")
def share_create(assessment_id: int, request: Request,
                 user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if _owned_assessment(db, user, assessment_id) is None:
        return _not_found(request, user)
    try:
        link = services.create_share_link(db, assessment_id, user_id=user.id)
    except ValueError:
        return RedirectResponse(f"/assessment/{assessment_id}/results", status_code=303)
    return RedirectResponse(f"/assessment/{assessment_id}/results?shared={link.token}",
                            status_code=303)


@router.get("/login")
def login_form(request: Request, user=Depends(get_current_user),
               db: Session = Depends(get_db)):
    if user is not None:
        return RedirectResponse("/dashboard", status_code=303)
    from elipsis_api.deps import safe_next
    nxt = safe_next(request.query_params.get("next"))
    return templates.TemplateResponse(
        request, "login.html", {"user": user, "error": None,
                                "next": nxt or "",
                                "total_questions": _question_count(db)})


@router.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...),
          next: str = Form(""),
          db: Session = Depends(get_db)):
    from elipsis_api import auth_extra
    from elipsis_api.deps import safe_next
    account = auth_extra.authenticate_resilient(db, email, password)
    nxt = safe_next(next) or ""
    if account is None:
        return templates.TemplateResponse(
            request, "login.html", {"user": None,
                                    "error": "Invalid email or password. Create a free account if you are new.",
                                    "email": email.strip().lower(),
                                    "next": nxt,
                                    "total_questions": _question_count(db)},
            status_code=401)
    token = services.create_session(db, account.id)
    response = RedirectResponse(nxt or "/dashboard", status_code=303)
    _set_session_cookie(response, token)
    return response


@router.get("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    services.delete_session(db, request.cookies.get(SESSION_COOKIE))
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@router.get("/assessments")
def assessments(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    visible = services.visible_org_ids(db, user)
    focus = _int_param(request, "org")
    scope = visible
    if focus is not None and (visible is None or focus in visible):
        scope = [focus]
    rows = services.list_assessments(db, scope)
    return templates.TemplateResponse(
        request, "assessments.html",
        {"user": user, "rows": rows,
         "organizations": services.list_organizations(db, visible),
         "focus": focus})


@router.get("/start")
def start_get(request: Request, user=Depends(get_current_user),
              db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    visible = services.visible_org_ids(db, user)
    return templates.TemplateResponse(
        request, "start.html",
        {"user": user,
         "organizations": services.list_organizations(db, visible),
         "error": None})


@router.post("/start")
def start_post(request: Request,
               organization_id: str = Form(""),
               organization_name: str = Form(""),
               department: str = Form("Operations"),
               respondent: str = Form(""),
               user=Depends(get_current_user),
               db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    try:
        if organization_id.strip().isdigit():
            org_id = int(organization_id)
            if not services.can_access_org(db, user, org_id):
                raise ValueError("organization not found")
            payload = schemas.AssessmentIn(
                organization_id=org_id,
                department=department.strip() or "Operations",
                respondent=(respondent or "").strip() or None,
            )
        else:
            name = (organization_name or "").strip()
            if not name:
                raise ValueError("Provide a company name or pick an existing one.")
            payload = schemas.AssessmentIn(
                organization=schemas.OrganizationIn(name=name),
                department=department.strip() or "Operations",
                respondent=(respondent or "").strip() or None,
            )
        assessment = services.create_assessment(db, payload)
        services.claim_org(db, user.id, assessment.organization_id)
    except Exception as exc:  # noqa: BLE001
        print(f"[elipsis] start assessment failed: {exc}", flush=True)
        visible = services.visible_org_ids(db, user)
        return templates.TemplateResponse(
            request, "start.html",
            {"user": user, "error": str(exc),
             "organizations": services.list_organizations(db, visible)},
            status_code=400)
    return RedirectResponse(f"/assessment/{assessment.id}/step/1", status_code=303)


@router.get("/assessment/{assessment_id}")
def assessment_redirect(assessment_id: int, request: Request,
                        user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if _owned_assessment(db, user, assessment_id) is None:
        return _not_found(request, user)
    return RedirectResponse(f"/assessment/{assessment_id}/step/1", status_code=303)


@router.get("/assessment/{assessment_id}/step/{number}")
def assessment_step(assessment_id: int, number: int, request: Request,
                    user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    assessment = _owned_assessment(db, user, assessment_id)
    if assessment is None:
        return _not_found(request, user)
    steps = services.build_segments(db, assessment_id)
    if not steps:
        return _not_found(request, user)
    number = max(1, min(number, len(steps)))
    step = steps[number - 1]
    answers = services.answers_map(db, assessment_id)
    live = services.live_scores(db, assessment_id, step["subdomain"]) or {}
    return templates.TemplateResponse(
        request, "step.html",
        {"user": user, "assessment": assessment, "step": step, "steps": steps,
         "total_steps": len(steps), "answers": answers, "live": live,
         "is_last": number >= len(steps)})


@router.post("/assessment/{assessment_id}/live")
async def assessment_live(assessment_id: int, request: Request,
                          user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return JSONResponse({"error": "not signed in"}, status_code=401)
    if _owned_assessment(db, user, assessment_id) is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    body = await request.json()
    items = body.get("answers") or []
    segment = body.get("segment") or ""
    services.save_answers(db, assessment_id, items)
    live = services.live_scores(db, assessment_id, segment) or {}
    return JSONResponse(live)


@router.post("/dashboard/reset")
def dashboard_reset(request: Request, user=Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    visible = services.visible_org_ids(db, user)
    services.reset_demo_data(db, visible)
    return RedirectResponse("/dashboard", status_code=303)


@router.get("/dashboard")
def dashboard(request: Request, user=Depends(get_current_user),
              db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    visible = services.visible_org_ids(db, user)
    data = services.dashboard_data(db, org_ids=visible)
    return templates.TemplateResponse(
        request, "dashboard.html",
        {"user": user, **data,
         "organizations": services.list_organizations(db, visible)})


@router.post("/assessment/{assessment_id}/submit")
def assessment_submit(assessment_id: int, request: Request,
                      user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if _owned_assessment(db, user, assessment_id) is None:
        return _not_found(request, user)
    form = await_form = None
    # Collect scores from form fields q{id}
    answers = []
    form_data = {}
    # FastAPI Form collection via request
    import asyncio
    async def _collect():
        return await request.form()
    # Sync path: use starlette form
    return _submit_sync(assessment_id, request, user, db)


def _submit_sync(assessment_id, request, user, db):
    return RedirectResponse(f"/assessment/{assessment_id}/results", status_code=303)


@router.get("/assessment/{assessment_id}/results")
def assessment_results(assessment_id: int, request: Request,
                       user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    assessment = _owned_assessment(db, user, assessment_id)
    if assessment is None:
        return _not_found(request, user)
    _, result = services.compute(db, assessment_id)
    if result is None:
        return RedirectResponse(f"/assessment/{assessment_id}/step/1", status_code=303)
    if assessment.status != "completed":
        services.save(db, assessment_id, result)
    org = db.get(models.Organization, assessment.organization_id)
    return templates.TemplateResponse(
        request, "results.html",
        {"user": user, "assessment": assessment, "result": result, "org": org,
         "shared": request.query_params.get("shared")})


@router.get("/assessment/{assessment_id}/pillar/{code}")
def assessment_pillar(assessment_id: int, code: str, request: Request,
                      user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    assessment = _owned_assessment(db, user, assessment_id)
    if assessment is None:
        return _not_found(request, user)
    _, result = services.compute(db, assessment_id)
    if result is None:
        return _not_found(request, user)
    return templates.TemplateResponse(
        request, "results.html",
        {"user": user, "assessment": assessment, "result": result,
         "focus_pillar": code.upper()})


@router.get("/assessment/{assessment_id}/export.json")
def assessment_export(assessment_id: int, request: Request,
                      user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    assessment = _owned_assessment(db, user, assessment_id)
    if assessment is None:
        return _not_found(request, user)
    _, result = services.compute(db, assessment_id)
    if result is None:
        return JSONResponse({"error": "not ready"}, status_code=404)
    org = db.get(models.Organization, assessment.organization_id)
    dept = db.get(models.Department, assessment.department_id) if assessment.department_id else None
    return JSONResponse({
        "assessment": {
            "id": assessment.id,
            "status": assessment.status,
            "respondent": assessment.respondent,
            "completed_at": assessment.completed_at,
            "organization": org.name if org else None,
            "department": dept.name if dept else None,
        },
        "result": result,
    })
