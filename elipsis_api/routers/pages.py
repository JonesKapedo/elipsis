"""Server-rendered pages (Jinja2) — the human interface."""

import os

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from elipsis_api import (
    benchmarks,
    departments,
    logistics,
    models,
    premium,
    schemas,
    services,
    services_operations,
    services_ops,
    services_room,
    services_success,
    services_webhooks,
)
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


def _owned_assessment(db: Session, user, assessment_id: int):
    """Return the assessment only if this user may see its company."""
    assessment = db.get(models.Assessment, assessment_id)
    if assessment is None or not services.can_access_org(db, user, assessment.organization_id):
        return None
    return assessment


def _int_param(request: Request, name: str) -> int | None:
    raw = request.query_params.get(name) or ""
    return int(raw) if raw.isdigit() else None


def _optional_int(raw: str | None) -> int | None:
    value = (raw or "").strip()
    return int(value) if value.isdigit() else None


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


@router.get("/robots.txt", include_in_schema=False)
def robots(request: Request):
    base = str(request.base_url).rstrip("/")
    body = (
        "User-agent: *\n"
        "Allow: /$\n"
        "Allow: /methodology\n"
        "Allow: /pricing\n"
        "Allow: /partners\n"
        "Allow: /sample\n"
        "Allow: /privacy\n"
        "Allow: /terms\n"
        "Allow: /security\n"
        "Allow: /case-study\n"
        "Allow: /trust\n"
        "Allow: /status\n"
        "Allow: /help\n"
        "Allow: /service-standards\n"
        "Allow: /changelog\n"
        "Allow: /accessibility\n"
        "Allow: /dpa\n"
        "Allow: /subprocessors\n"
        "Disallow: /dashboard\n"
        "Disallow: /assessment/\n"
        "Disallow: /api/\n"
        "Disallow: /company\n"
        "Disallow: /support\n"
        "Disallow: /account\n"
        "Disallow: /admin\n"
        "Disallow: /settings\n"
        f"Sitemap: {base}/sitemap.xml\n"
    )
    return PlainTextResponse(body, media_type="text/plain")


@router.get("/sitemap.xml", include_in_schema=False)
def sitemap(request: Request):
    base = str(request.base_url).rstrip("/")
    paths = ("/", "/methodology", "/pricing", "/partners", "/sample",
             "/privacy", "/terms", "/security", "/case-study", "/trust",
             "/status", "/help", "/service-standards", "/changelog",
             "/accessibility", "/dpa", "/subprocessors", "/login", "/signup")
    urls = "".join(
        f"<url><loc>{base}{path}</loc><changefreq>monthly</changefreq>"
        f"<priority>{'1.0' if path == '/' else '0.7'}</priority></url>"
        for path in paths
    )
    body = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f'{urls}</urlset>')
    return PlainTextResponse(body, media_type="application/xml")


@router.get("/")
def landing(request: Request, user=Depends(get_current_user),
            db: Session = Depends(get_db)):
    if user is not None:
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(
        request, "landing.html",
        {"user": user, "total_questions": _question_count(db),
         "reference_points": benchmarks.REFERENCE_POINTS,
         "icp": benchmarks.ICP_LABEL})


@router.get("/sample")
def sample_report(request: Request, user=Depends(get_current_user)):
    result = sample_result()
    return templates.TemplateResponse(
        request, "sample.html",
        {"user": user, "result": result, "org": SAMPLE_ORG})


@router.get("/pricing")
def pricing(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse(request, "pricing.html", {
        "user": user, "premium_plans": premium.PLANS,
        "premium_currency": premium.CURRENCY})


@router.get("/methodology")
def methodology(request: Request, user=Depends(get_current_user),
                db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request, "methodology.html",
        {"user": user, "total_questions": _question_count(db) or 63,
         "reference_points": benchmarks.REFERENCE_POINTS,
         "sources": benchmarks.SOURCES, "method_note": benchmarks.METHOD_NOTE})


@router.get("/faq")
def faq(request: Request, user=Depends(get_current_user),
        db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request, "faq.html",
        {"user": user, "total_questions": _question_count(db) or 63,
         "reference_points": benchmarks.REFERENCE_POINTS,
         "sources": benchmarks.SOURCES, "method_note": benchmarks.METHOD_NOTE})


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
def demo_get(request: Request, user=Depends(get_current_user),
             db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request, "demo.html",
        {"user": user, "error": None, "total_questions": _question_count(db)})


@router.post("/demo")
def demo_post(request: Request, user=Depends(get_current_user),
              db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    try:
        assessment = services.run_guided_demo(db)
        services.claim_org(db, user.id, assessment.organization_id)
    except Exception as exc:  # noqa: BLE001
        print(f"[elipsis] guided demo failed: {exc}", flush=True)
        return templates.TemplateResponse(
            request, "demo.html",
            {"user": user, "error": "Could not generate the demo. Try again.",
             "total_questions": _question_count(db)},
            status_code=500)
    return RedirectResponse(f"/assessment/{assessment.id}/results", status_code=303)


@router.get("/compare")
def compare(request: Request, user=Depends(get_current_user),
            db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    visible = services.visible_org_ids(db, user)
    return templates.TemplateResponse(
        request, "compare.html",
        {"user": user, "organizations": services.list_organizations(db, visible)})


@router.get("/compare/{organization_id}")
def compare_org(organization_id: int, request: Request,
                user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not services.can_access_org(db, user, organization_id):
        return _not_found(request, user)
    org = db.get(models.Organization, organization_id)
    overview = services.company_overview(db, org)
    comparison = overview.get("comparison") or {}
    return templates.TemplateResponse(
        request, "compare.html",
        {"user": user, "org": org, "organization": org, "overview": overview,
         "rows": comparison.get("rows") or [],
         "pillars": comparison.get("pillars") or [],
         "average": comparison.get("average"),
         "organizations": services.list_organizations(
             db, services.visible_org_ids(db, user))})


@router.get("/share/{token}")
def share_view(token: str, request: Request, db: Session = Depends(get_db)):
    link, assessment, result = services.resolve_share_token(db, token)
    if link is None or assessment is None or result is None:
        return _not_found(request, None)
    org = db.get(models.Organization, assessment.organization_id)
    dept = db.get(models.Department, assessment.department_id) if assessment.department_id else None
    services_ops.touch_share_link(db, link)
    return templates.TemplateResponse(
        request, "share.html",
        {"user": None, "result": result, "assessment": assessment, "org": org,
         "organization": org, "department": dept, "link": link, "token": token})


@router.post("/assessment/{assessment_id}/share")
def share_create(assessment_id: int, request: Request,
                 label: str = Form(""), days: str = Form(""),
                 user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if _owned_assessment(db, user, assessment_id) is None:
        return _not_found(request, user)
    assessment = db.get(models.Assessment, assessment_id)
    if assessment is None or not services.company_is_pro(db, assessment.organization_id, user):
        return RedirectResponse("/pro?locked=reports", status_code=303)
    try:
        days = int(days or request.query_params.get("days") or 30)
    except ValueError:
        days = 30
    try:
        link = services.create_share_link(
            db, assessment_id, user_id=user.id,
            label=(label or request.query_params.get("label") or None),
            expires_days=max(1, min(365, days)))
    except ValueError:
        return RedirectResponse(f"/assessment/{assessment_id}/results", status_code=303)
    services_ops.record_audit(
        db, action="share.create",
        organization_id=assessment.organization_id if assessment else None,
        assessment_id=assessment_id, user_id=user.id,
        detail=f"{link.label or 'share'} · {days} days")
    db.commit()
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
    old = request.cookies.get(SESSION_COOKIE)
    if old:
        services.delete_session(db, old)
    token = services.create_session(db, account.id)
    prefs = db.get(models.UserPref, account.id)
    home = (prefs.landing_page if prefs and prefs.landing_page else "/dashboard")
    dest = nxt or (home if services.owned_org_ids(db, account) else "/setup")
    response = RedirectResponse(dest, status_code=303)
    _set_session_cookie(response, token)
    return response


@router.get("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    services.delete_session(db, request.cookies.get(SESSION_COOKIE))
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(
        SESSION_COOKIE, path="/", secure=_SECURE_COOKIE,
        httponly=True, samesite="lax",
    )
    return response


@router.get("/assessments")
def assessments(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    visible = services.visible_org_ids(db, user)
    focus = _int_param(request, "org")
    orgs = services.list_organizations(db, visible)
    company = next((org for org in orgs if org.id == focus), None)
    if company is None and len(orgs) == 1:
        company = orgs[0]
    scope = [company.id] if company is not None else visible
    rows = services.list_assessments(db, scope)
    completed = [row for row in rows
                 if row.get("status") == "completed"
                 and row.get("readiness_index") is not None]
    scores = [row["readiness_index"] for row in completed]
    lane_snapshot = logistics.snapshot(db, org_ids=scope)
    lanes_at_risk = [lane for lane in lane_snapshot["lanes"]
                     if lane["score"] is not None and lane["score"] < 50]
    summary = {
        "total": len(rows),
        "completed": len(completed),
        "in_progress": len(rows) - len(completed),
        "average": round(sum(scores) / len(scores), 1) if scores else None,
        "lanes_at_risk": len(lanes_at_risk),
    }
    return templates.TemplateResponse(
        request, "assessments.html",
        {"user": user, "rows": rows, "summary": summary,
         "lane_snapshot": lane_snapshot,
         "organizations": orgs,
         "company": company,
         "company_context": services.company_context(company),
         "focus": company.id if company is not None else None})


def _start_context(db: Session, user) -> dict:
    orgs = services.list_organizations(db, services.visible_org_ids(db, user))
    prefs = services.user_prefs(db, user)
    return {
        "organizations": orgs,
        "prefs": prefs,
        "is_pro": services.is_pro_user(db, user),
        "departments": departments.DEPARTMENTS,
        "department_labels": departments.DEPARTMENT_LABELS,
        "brief": departments.department_brief(prefs.default_department),
        "total_questions": _question_count(db),
    }


@router.get("/start")
def start_get(request: Request, user=Depends(get_current_user),
              db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    context = _start_context(db, user)
    orgs = context["organizations"]
    if not orgs:
        return RedirectResponse("/setup?next=assessment", status_code=303)
    focus = _int_param(request, "org")
    selected = next((org for org in orgs if org.id == focus), None)
    if selected is None:
        preferred = context["prefs"].default_organization_id
        selected = next((org for org in orgs if org.id == preferred), None)
    if selected is None:
        selected = orgs[0]
    department = context["prefs"].default_department or "Operations"
    if department not in departments.DEPARTMENT_LABELS:
        department = "Operations"
    return templates.TemplateResponse(
        request, "start.html",
        {"user": user, **context, "company": selected,
         "company_context": services.company_context(selected),
         "company_pro": services.company_is_pro(db, selected.id, user),
         "department": department,
         "brief": departments.department_brief(department),
         "method": request.query_params.get("method") or "self",
         "error": None})


@router.post("/start")
def start_post(request: Request,
               organization_id: str = Form(""),
               department: str = Form("Operations"),
               respondent: str = Form(""),
               method: str = Form("self"),
               deadline_date: str = Form(""),
               deadline_time: str = Form("17:00"),
               min_respondents: int = Form(3),
               contact_mode: str = Form("optional"),
               target_roles: str = Form(""),
               note: str = Form(""),
               user=Depends(get_current_user),
               db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    context = _start_context(db, user)
    orgs = context["organizations"]
    if not orgs:
        return RedirectResponse("/setup?next=assessment", status_code=303)
    try:
        org_id = int(organization_id) if organization_id.strip().isdigit() else 0
        if not org_id or not services.can_access_org(db, user, org_id):
            raise ValueError("Select one of your saved companies.")
        dept = department.strip() or "Operations"
        if method == "team":
            if not services.company_is_pro(db, org_id, user):
                return RedirectResponse("/pro?locked=team", status_code=303)
            deadline = ""
            if deadline_date.strip():
                deadline = f"{deadline_date.strip()}T{(deadline_time or '17:00').strip()}"
            camp = services.create_collect_campaign(
                db, organization_id=org_id, user_id=user.id, department=dept,
                deadline=deadline, min_respondents=min_respondents,
                contact_mode=contact_mode, question_set=dept,
                target_roles=target_roles, note=note,
            )
            prefs = context["prefs"]
            prefs.default_organization_id = org_id
            prefs.default_department = dept
            db.commit()
            return RedirectResponse(f"/company/campaign/{camp.token}", status_code=303)
        payload = schemas.AssessmentIn(
            organization_id=org_id,
            department=dept,
            respondent=(respondent or "").strip() or None,
            source="self",
        )
        assessment = services.create_assessment(db, payload)
        prefs = context["prefs"]
        prefs.default_organization_id = org_id
        prefs.default_department = dept
        db.commit()
    except Exception as exc:  # noqa: BLE001
        print(f"[elipsis] start assessment failed: {exc}", flush=True)
        selected = next((org for org in orgs if str(org.id) == organization_id), orgs[0])
        return templates.TemplateResponse(
            request, "start.html",
            {"user": user, **context, "error": str(exc),
             "company": selected,
             "company_context": services.company_context(selected),
             "company_pro": services.company_is_pro(db, selected.id, user),
             "department": department,
             "brief": departments.department_brief(department),
             "method": method},
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
    orgs = services.list_organizations(db, visible)
    focus = _int_param(request, "org")
    company = next((org for org in orgs if org.id == focus), None)
    if company is None and len(orgs) == 1:
        company = orgs[0]
    scope = [company.id] if company is not None else visible
    data = services.dashboard_data(db, org_ids=scope)
    return templates.TemplateResponse(
        request, "dashboard.html",
        {"user": user, **data,
         "organizations": orgs,
         "company": company,
         "company_context": services.company_context(company),
         "focus": company.id if company is not None else None,
         "action_summary": services_ops.action_summary(db, scope),
         "notifications": services_ops.notifications(db, user),
         "logistics": logistics.snapshot(db, org_ids=scope),
         "operations": services_operations.summary(db, scope),
         "trends": services_ops.org_trends(db, scope),
         "activation": services_success.activation(db, user, company),
         "health": services_success.customer_health(db, company) if company else None})


@router.post("/assessment/{assessment_id}/submit")
async def assessment_submit(assessment_id: int, request: Request,
                            background_tasks: BackgroundTasks,
                            user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    assessment = _owned_assessment(db, user, assessment_id)
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
    _, result = services.submit(db, assessment_id, answers)
    if result is not None:
        for hook in services_webhooks.matching_endpoints(
                db, assessment.organization_id, "assessment.completed"):
            background_tasks.add_task(
                services_webhooks.deliver_event, hook.id, "assessment.completed",
                {"event": "assessment.completed", "assessment_id": assessment_id,
                 "readiness_index": result.get("readiness_index"),
                 "confidence_index": result.get("confidence_index")})
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
    dept = db.get(models.Department, assessment.department_id) if assessment.department_id else None
    token = request.query_params.get("shared")
    share_url = (str(request.base_url).rstrip("/") + f"/share/{token}") if token else None
    previous = services.previous_assessment(db, assessment)
    delta = None
    if previous is not None and previous.readiness_index is not None:
        delta = round((result.get("readiness_index") or 0) - previous.readiness_index, 1)
    return templates.TemplateResponse(
        request, "results.html",
        {"user": user, "assessment": assessment, "result": result, "org": org,
         "organization": org, "department": dept,
         "company_context": services.company_context(org),
         "share_url": share_url, "shared": token,
         "benchmark": benchmarks.cohort_benchmark(
             db, org, score=result.get("readiness_index")),
         "reference_points": benchmarks.REFERENCE_POINTS,
         "sources": benchmarks.SOURCES, "method_note": benchmarks.METHOD_NOTE,
         "previous": previous, "delta": delta,
         "logistics": logistics.snapshot(db, assessment_ids=[assessment_id]),
         "operations": services_operations.summary(db, [assessment.organization_id]),
         "share_links": services_ops.share_links(db, assessment_id),
         "is_pro": services.company_is_pro(db, assessment.organization_id, user),
         "company_pro": services.company_is_pro(db, assessment.organization_id, user),
         "notes": services_room.notes(db, assessment.id),
         "note_sections": services_room.SECTIONS,
         "can_contribute": services.can_contribute_org(db, user, assessment.organization_id),
         "notifications": services_ops.notifications(db, user)})


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
    org = db.get(models.Organization, assessment.organization_id)
    dept = db.get(models.Department, assessment.department_id) if assessment.department_id else None
    return templates.TemplateResponse(
        request, "results.html",
        {"user": user, "assessment": assessment, "result": result,
         "organization": org, "department": dept,
         "benchmark": benchmarks.cohort_benchmark(db, org),
         "is_pro": services.company_is_pro(db, assessment.organization_id, user),
         "focus_pillar": code.upper()})


@router.get("/assessment/{assessment_id}/export.json")
def assessment_export(assessment_id: int, request: Request,
                      user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    assessment = _owned_assessment(db, user, assessment_id)
    if assessment is None:
        return _not_found(request, user)
    if not services.company_is_pro(db, assessment.organization_id, user):
        return RedirectResponse("/pro?locked=reports", status_code=303)
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
