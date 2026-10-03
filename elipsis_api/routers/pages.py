"""Server-rendered pages (Jinja2) — the human interface."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from constants import PILLAR_LABELS, SUBDOMAIN_LABELS
from elipsis_api import models, schemas, services
from elipsis_api.config import SESSION_COOKIE
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user, login_redirect, templates

router = APIRouter()


def _not_found(request, user):
    return templates.TemplateResponse(request, "404.html", {"user": user},
                                      status_code=404)


@router.get("/")
def landing(request: Request, user=Depends(get_current_user)):
    """The sign-in wall: signed-in users go straight to the dashboard."""
    if user is not None:
        return RedirectResponse("/dashboard", status_code=303)
    return RedirectResponse("/login", status_code=303)


@router.get("/login")
def login_form(request: Request, user=Depends(get_current_user),
               db: Session = Depends(get_db)):
    bank = services.get_bank(db)
    total_questions = db.scalar(select(func.count()).select_from(models.Question).where(
        models.Question.questionnaire_id == bank.id)) if bank else 0
    return templates.TemplateResponse(
        request, "login.html", {"user": user, "error": None,
                                "total_questions": total_questions or 0})


@router.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...),
          db: Session = Depends(get_db)):
    account = services.authenticate(db, email, password)
    if account is None:
        return templates.TemplateResponse(
            request, "login.html", {"user": None,
                                    "error": "Invalid email or password."}, status_code=401)
    token = services.create_session(db, account.id)
    response = RedirectResponse("/dashboard", status_code=303)
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax")
    return response


@router.get("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    services.delete_session(db, request.cookies.get(SESSION_COOKIE))
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response


@router.get("/assessments")
def assessments(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    return templates.TemplateResponse(
        request, "assessments.html",
        {"user": user, "rows": services.list_assessments(db)})


@router.get("/start")
def start_form(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    orgs = db.scalars(select(models.Organization).order_by(models.Organization.name)).all()
    bank = services.get_bank(db)
    total_questions = db.scalar(select(func.count()).select_from(models.Question).where(
        models.Question.questionnaire_id == bank.id)) if bank else 0
    return templates.TemplateResponse(
        request, "start.html", {"user": user, "organizations": orgs,
                                "total_questions": total_questions or 0})


@router.post("/start")
def start_create(request: Request,
                 organization_id: str = Form(""), org_name: str = Form(""),
                 industry: str = Form(""), employee_count: str = Form(""),
                 country: str = Form("Kenya"), city: str = Form(""),
                 department: str = Form("Operations"), respondent: str = Form(""),
                 user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    payload = schemas.AssessmentIn(department=department or "Operations",
                                   respondent=respondent or None)
    if organization_id.strip():
        payload.organization_id = int(organization_id)
    else:
        if not org_name.strip():
            return RedirectResponse("/start", status_code=303)
        payload.organization = schemas.OrganizationIn(
            name=org_name.strip(), industry=industry or None,
            employee_count=int(employee_count) if employee_count.strip().isdigit() else None,
            country=country or None, city=city or None)
    assessment = services.create_assessment(db, payload)
    return RedirectResponse(f"/assessment/{assessment.id}", status_code=303)


@router.get("/assessment/{assessment_id}")
def assessment_detail(assessment_id: int, request: Request,
                      user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Send the respondent to their current step rather than a long form."""
    if user is None:
        return login_redirect()
    assessment = db.get(models.Assessment, assessment_id)
    if assessment is None:
        return _not_found(request, user)
    if assessment.status == "completed":
        return RedirectResponse(f"/assessment/{assessment_id}/results", status_code=303)
    steps = services.build_segments(db, assessment_id)
    first_open = next((s["number"] for s in steps if not s["complete"]), 1)
    return RedirectResponse(f"/assessment/{assessment_id}/step/{first_open}", status_code=303)


@router.get("/assessment/{assessment_id}/step/{number}")
def assessment_step(assessment_id: int, number: int, request: Request,
                    user=Depends(get_current_user), db: Session = Depends(get_db)):
    """One short segment: three questions, with live scoring as they answer."""
    if user is None:
        return login_redirect()
    assessment = db.get(models.Assessment, assessment_id)
    if assessment is None:
        return _not_found(request, user)
    if assessment.status == "completed":
        return RedirectResponse(f"/assessment/{assessment_id}/results", status_code=303)

    steps = services.build_segments(db, assessment_id)
    if not steps:
        return _not_found(request, user)
    number = max(1, min(number, len(steps)))
    step = steps[number - 1]

    live = services.live_scores(db, assessment_id, step["subdomain"])
    organization = db.get(models.Organization, assessment.organization_id)
    department = (db.get(models.Department, assessment.department_id)
                  if assessment.department_id else None)

    return templates.TemplateResponse(request, "step.html", {
        "user": user, "assessment": assessment,
        "organization": organization, "department": department,
        "step": step, "steps": steps,
        "is_last": number == len(steps),
        "answers": services.answers_map(db, assessment_id),
        "live": live,
        "total_steps": len(steps),
    })


@router.post("/assessment/{assessment_id}/live")
async def assessment_live(assessment_id: int, request: Request,
                          user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Persist the answers typed so far and return the running scores.

    Called by the form after every answer. It never computes the final result;
    it just reports what the answers imply right now, so the respondent sees
    their section update as they go.
    """
    if user is None:
        return JSONResponse({"error": "not signed in"}, status_code=401)
    payload = await request.json()
    items = []
    for raw in payload.get("answers", []):
        try:
            items.append(dict(question_id=int(raw["question_id"]),
                              score=max(0, min(5, int(raw["score"]))),
                              evidence=str(raw.get("evidence") or "none")))
        except (KeyError, TypeError, ValueError):
            continue
    services.save_answers(db, assessment_id, items)
    live = services.live_scores(db, assessment_id, payload.get("segment") or "")
    if live is None:
        return JSONResponse({"error": "assessment not found"}, status_code=404)
    return JSONResponse(live)


@router.post("/dashboard/reset")
def dashboard_reset(request: Request, user=Depends(get_current_user),
                    db: Session = Depends(get_db)):
    """Clear every assessment so the demo can be run again from scratch."""
    if user is None:
        return login_redirect()
    services.reset_demo_data(db)
    return RedirectResponse("/dashboard", status_code=303)


@router.get("/dashboard")
def dashboard(request: Request, user=Depends(get_current_user),
              db: Session = Depends(get_db)):
    """The landing page for a signed-in user."""
    if user is None:
        return login_redirect()
    data = services.dashboard_data(db)
    recent = data["all_completed"][0] if data["all_completed"] else None
    recent_live = None
    if recent:
        assessment = db.get(models.Assessment, recent["id"])
        if assessment is not None:
            recent_live = services.compute(db, recent["id"])[1]
    return templates.TemplateResponse(request, "dashboard.html", {
        "user": user, **data, "recent": recent, "recent_live": recent_live,
    })


@router.post("/assessment/{assessment_id}/submit")
async def assessment_submit(assessment_id: int, request: Request,
                            user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    assessment = db.get(models.Assessment, assessment_id)
    if assessment is None:
        return _not_found(request, user)
    form = await request.form()
    answers = []
    for question in services.get_questions(db, assessment.questionnaire_id):
        raw = form.get(f"q{question.id}")
        if not isinstance(raw, str) or raw == "":
            continue
        try:
            score = max(0, min(5, int(raw)))
        except ValueError:
            continue
        evidence = form.get(f"e{question.id}")
        answers.append(schemas.AnswerIn(
            question_id=question.id, score=score,
            evidence=evidence if isinstance(evidence, str) else "none"))
    services.submit(db, assessment_id, answers)
    return RedirectResponse(f"/assessment/{assessment_id}/results", status_code=303)


@router.get("/assessment/{assessment_id}/results")
def assessment_results(assessment_id: int, request: Request,
                       user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    assessment, result = services.compute(db, assessment_id)
    if assessment is None or result is None:
        return _not_found(request, user)
    return templates.TemplateResponse(request, "results.html", {
        "user": user, "result": result, "assessment": assessment,
        "organization": db.get(models.Organization, assessment.organization_id),
        "department": db.get(models.Department, assessment.department_id)
        if assessment.department_id else None,
    })


@router.get("/assessment/{assessment_id}/report")
def assessment_report(assessment_id: int, request: Request,
                      user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    assessment, result = services.compute(db, assessment_id)
    if assessment is None or result is None:
        return _not_found(request, user)
    return templates.TemplateResponse(request, "report.html", {
        "user": user, "result": result, "assessment": assessment,
        "organization": db.get(models.Organization, assessment.organization_id),
        "department": db.get(models.Department, assessment.department_id)
        if assessment.department_id else None,
    })