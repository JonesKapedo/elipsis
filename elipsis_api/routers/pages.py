"""Server-rendered pages (Jinja2) — the human interface."""

import os

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from elipsis_api import models, schemas, services
from elipsis_api.config import SESSION_COOKIE
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user, login_redirect, templates
from elipsis_api.sample import SAMPLE_ORG, sample_result

router = APIRouter()

_SECURE_COOKIE = os.getenv("VERCEL") == "1" or os.getenv("ELIPSIS_SECURE_COOKIE") == "1"
_COOKIE_MAX_AGE = 60 * 60 * 24 * 14


def _not_found(request, user):
    return templates.TemplateResponse(request, "404.html", {"user": user},
                                      status_code=404)


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
        secure=_SECURE_COOKIE, max_age=_COOKIE_MAX_AGE,
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
        print(f"[elipsis] contact from {email} topic={topic}", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"[elipsis] contact save failed: {exc}", flush=True)
        return templates.TemplateResponse(
            request, "contact.html",
            {"user": user, "sent": False,
             "error": "Could not save your message. Please try again.",
             "form": form},
            status_code=500)
    return templates.TemplateResponse(
        request, "contact.html",
        {"user": user, "sent": True, "error": None, "form": None})


@router.get("/demo")
def demo_page(request: Request, user=Depends(get_current_user),
              db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request, "demo.html",
        {"user": user, "total_questions": _question_count(db) or 63})


@router.post("/demo")
def demo_run(request: Request, user=Depends(get_current_user),
             db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    try:
        assessment = services.run_guided_demo(db)
    except Exception:
        return RedirectResponse("/demo", status_code=303)
    return RedirectResponse(f"/assessment/{assessment.id}/results", status_code=303)


@router.get("/compare")
def compare_index(request: Request, user=Depends(get_current_user),
                  db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    return templates.TemplateResponse(request, "compare.html", {
        "user": user,
        "organization": None,
        "organizations": services.list_organizations(db),
        "rows": [],
        "pillars": [],
        "average": None,
    })


@router.get("/compare/{organization_id}")
def compare_org(organization_id: int, request: Request,
                user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    data = services.department_comparison(db, organization_id)
    if data.get("organization") is None:
        return _not_found(request, user)
    return templates.TemplateResponse(request, "compare.html", {
        "user": user,
        "organizations": [],
        **data,
    })


@router.get("/share/{token}")
def shared_report(token: str, request: Request, user=Depends(get_current_user),
                  db: Session = Depends(get_db)):
    link, assessment, result = services.resolve_share_token(db, token)
    if link is None or assessment is None or result is None:
        return _not_found(request, user)
    return templates.TemplateResponse(request, "share.html", {
        "user": user,
        "link": link,
        "assessment": assessment,
        "result": result,
        "organization": db.get(models.Organization, assessment.organization_id),
        "department": db.get(models.Department, assessment.department_id)
        if assessment.department_id else None,
    })


@router.post("/assessment/{assessment_id}/share")
def create_share(assessment_id: int, request: Request,
                 user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
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
    return templates.TemplateResponse(
        request, "login.html", {"user": user, "error": None,
                                "total_questions": _question_count(db)})


@router.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...),
          db: Session = Depends(get_db)):
    account = services.authenticate(db, email.strip().lower(), password)
    if account is None:
        return templates.TemplateResponse(
            request, "login.html", {"user": None,
                                    "error": "Invalid email or password. Create a free account if you are new.",
                                    "email": email.strip().lower(),
                                    "total_questions": _question_count(db)},
            status_code=401)
    token = services.create_session(db, account.id)
    response = RedirectResponse("/dashboard", status_code=303)
    _set_session_cookie(response, token)
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
    from elipsis_api.routers.studio import _owned_orgs
    orgs = _owned_orgs(db, user)
    return templates.TemplateResponse(
        request, "start.html", {"user": user, "organizations": orgs,
                                "total_questions": _question_count(db)})


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
    try:
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
        from elipsis_api.routers.studio import _claim
        _claim(db, user.id, assessment.organization_id)
    except (ValueError, Exception):
        return RedirectResponse("/start", status_code=303)
    return RedirectResponse(f"/assessment/{assessment.id}", status_code=303)


@router.get("/assessment/{assessment_id}")
def assessment_detail(assessment_id: int, request: Request,
                      user=Depends(get_current_user), db: Session = Depends(get_db)):
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
    if user is None:
        return JSONResponse({"error": "not signed in"}, status_code=401)
    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001
        return JSONResponse({"error": "invalid json"}, status_code=400)
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
    if user is None:
        return login_redirect()
    services.reset_demo_data(db)
    return RedirectResponse("/dashboard", status_code=303)


@router.get("/dashboard")
def dashboard(request: Request, user=Depends(get_current_user),
              db: Session = Depends(get_db)):
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
    shared = request.query_params.get("shared")
    share_url = None
    if shared:
        share_url = str(request.base_url).rstrip("/") + f"/share/{shared}"
    return templates.TemplateResponse(request, "results.html", {
        "user": user, "result": result, "assessment": assessment,
        "organization": db.get(models.Organization, assessment.organization_id),
        "department": db.get(models.Department, assessment.department_id)
        if assessment.department_id else None,
        "share_url": share_url,
    })


@router.get("/assessment/{assessment_id}/report")
def assessment_report(assessment_id: int, request: Request,
                      user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    assessment, result = services.compute(db, assessment_id)
    if assessment is None or result is None:
        return _not_found(request, user)
    from elipsis_api.narrative import company_portrait
    org = db.get(models.Organization, assessment.organization_id)
    dept = db.get(models.Department, assessment.department_id) if assessment.department_id else None
    return templates.TemplateResponse(request, "report.html", {
        "user": user, "result": result, "assessment": assessment,
        "organization": org,
        "department": dept,
        "portrait": company_portrait(org, dept, result),
    })


@router.get("/assessment/{assessment_id}/export.json")
def assessment_export_json(assessment_id: int, request: Request,
                           user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return JSONResponse({"error": "not signed in"}, status_code=401)
    assessment, result = services.compute(db, assessment_id)
    if assessment is None or result is None:
        return JSONResponse({"error": "assessment not found"}, status_code=404)
    org = db.get(models.Organization, assessment.organization_id)
    dept = (db.get(models.Department, assessment.department_id)
            if assessment.department_id else None)
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
