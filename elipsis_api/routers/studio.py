"""Company workspace, Pro features, settings, letters, physical bids, Paystack."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from elipsis_api import (
    departments,
    models,
    paystack,
    premium,
    security,
    services,
    services_webhooks,
)
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user, login_redirect, templates
from elipsis_api.narrative import company_portrait

router = APIRouter()

PACKAGES = {
    "discovery": ("Discovery sweep", 180_000,
                  "One site, five days. Map the procedures that actually run, name the ones worth automating, and leave a written starting picture."),
    "mapping": ("Procedure mapping", 420_000,
                "Two to three weeks. Walk every core flow, time the handoffs, and produce an automation-bearing map leadership can fund."),
    "programme": ("Transformation programme", 950_000,
                  "Six to eight weeks. Full sweep plus a sequenced build plan, control design, and a board pack tied to the Elipsis Index."),
}


def _prefs(db: Session, user) -> models.UserPref:
    row = db.get(models.UserPref, user.id)
    if row is None:
        row = models.UserPref(user_id=user.id, symbol=(user.name or user.email or "E")[:1].upper())
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _is_admin(user) -> bool:
    return services.is_admin(user)


def _owned_orgs(db: Session, user):
    return services.owned_orgs(db, user)


def _claim(db: Session, user_id: int, organization_id: int):
    services.claim_org(db, user_id, organization_id)


def _parse_staff(raw: str):
    raw = (raw or "").strip()
    return int(raw) if raw.isdigit() and int(raw) > 0 else None


@router.get("/setup")
def company_setup(request: Request, user=Depends(get_current_user),
                  db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    orgs = _owned_orgs(db, user)
    new_mode = request.query_params.get("new") == "1"
    if new_mode and orgs and not services.is_pro_user(db, user):
        return RedirectResponse("/pro?locked=companies", status_code=303)
    focus = request.query_params.get("org")
    selected = next((org for org in orgs if str(org.id) == focus), None)
    if selected is None and orgs and not new_mode:
        selected = orgs[0]
    return templates.TemplateResponse(request, "company_setup.html", {
        "user": user, "company": selected, "organizations": orgs,
        "context": services.company_context(selected),
        "prefs": _prefs(db, user),
        "departments": departments.DEPARTMENTS,
        "next": request.query_params.get("next") or "",
        "is_new": new_mode or not orgs,
        "is_pro": services.is_pro_user(db, user),
    })


@router.post("/setup")
def company_setup_save(request: Request,
                       organization_id: str = Form(""),
                       name: str = Form(...),
                       legal_name: str = Form(""),
                       industry: str = Form("Logistics"),
                       sub_industry: str = Form(""),
                       employee_count: str = Form(""),
                       revenue_band: str = Form(""),
                       country: str = Form(""),
                       city: str = Form(""),
                       address: str = Form(""),
                       timezone: str = Form(""),
                       fiscal_year_start: str = Form(""),
                       operating_sites: str = Form(""),
                       primary_services: str = Form(""),
                       systems_used: str = Form(""),
                       website: str = Form(""),
                       registration_number: str = Form(""),
                       tax_id: str = Form(""),
                       contact_name: str = Form(""),
                       contact_email: str = Form(""),
                       contact_phone: str = Form(""),
                       default_department: str = Form("Operations"),
                       description: str = Form(""),
                       next: str = Form(""),
                       new: str = Form(""),
                       user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    orgs = _owned_orgs(db, user)
    org = None
    if organization_id.strip().isdigit():
        org = next((row for row in orgs if row.id == int(organization_id)), None)
    creating = org is None and (not orgs or new == "1")
    if creating:
        if orgs and not services.is_pro_user(db, user):
            return RedirectResponse("/pro?locked=companies", status_code=303)
        org = models.Organization(name=name.strip()[:160])
        db.add(org)
        db.flush()
    if org is None:
        return RedirectResponse("/company", status_code=303)
    org.name = name.strip()[:160]
    org.legal_name = legal_name.strip()[:160] or None
    org.industry = industry.strip()[:120] or None
    org.sub_industry = sub_industry.strip()[:120] or None
    org.employee_count = _parse_staff(employee_count)
    org.revenue_band = revenue_band.strip()[:80] or None
    org.country = country.strip()[:80] or None
    org.city = city.strip()[:80] or None
    org.address = address.strip()[:240] or None
    org.timezone = timezone.strip()[:80] or None
    org.fiscal_year_start = fiscal_year_start.strip()[:80] or None
    org.operating_sites = operating_sites.strip()[:240] or None
    org.primary_services = primary_services.strip()[:2000] or None
    org.systems_used = systems_used.strip()[:2000] or None
    org.website = website.strip()[:240] or None
    org.registration_number = registration_number.strip()[:120] or None
    org.tax_id = tax_id.strip()[:120] or None
    org.contact_name = contact_name.strip()[:120] or None
    org.contact_email = contact_email.strip()[:160] or None
    org.contact_phone = contact_phone.strip()[:80] or None
    org.description = description.strip()[:4000] or None
    _claim(db, user.id, org.id)
    prefs = _prefs(db, user)
    prefs.default_organization_id = org.id
    prefs.default_department = (
        default_department if default_department in departments.DEPARTMENT_LABELS
        else "Operations")
    prefs.onboarding_complete = 1
    db.commit()
    if next == "assessment" or creating:
        return RedirectResponse(f"/start?org={org.id}", status_code=303)
    return RedirectResponse(f"/dashboard?org={org.id}", status_code=303)


@router.get("/company")
def my_company(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    from elipsis_api import analytics
    rows = []
    for org in _owned_orgs(db, user):
        overview = services.company_overview(db, org)
        portrait, insight, latest = None, None, None
        if overview["latest"]:
            latest = db.get(models.Assessment, overview["latest"]["id"])
            _, result = services.compute(db, latest.id)
            if result:
                dept = db.get(models.Department, latest.department_id) if latest.department_id else None
                portrait = company_portrait(org, dept, result)
                insight = analytics.build(result)
        camps = []
        try:
            for c in db.scalars(select(models.CollectCampaign).where(
                    models.CollectCampaign.organization_id == org.id).order_by(
                    models.CollectCampaign.created_at.desc())).all():
                completed = db.scalar(select(func.count()).select_from(models.CollectResponse).where(
                    models.CollectResponse.campaign_token == c.token,
                    models.CollectResponse.status == "completed")) or 0
                camps.append({
                    "token": c.token, "title": c.title, "status": c.status,
                    "deadline": c.deadline, "min_respondents": c.min_respondents,
                    "completed": int(completed), "question_set": c.question_set,
                    "contact_mode": c.contact_mode, "target_roles": c.target_roles,
                    "master_assessment_id": c.master_assessment_id,
                })
        except Exception:
            camps = []
        from elipsis_api import services_room
        rows.append({
            "org": org, "context": services.company_context(org),
            "overview": overview, "portrait": portrait, "insight": insight,
            "latest": latest, "assessments": overview["rows"],
            "spark": analytics.sparkline([t["value"] for t in overview["trend"]]),
            "editing": request.query_params.get("edit") == str(org.id),
            "campaigns": camps,
            "pulse": services_room.pulse(db, org.id),
            "members": len(services_room.member_rows(db, org.id)),
            "company_pro": services.company_is_pro(db, org.id, user),
        })
    return templates.TemplateResponse(request, "company.html", {
        "user": user, "rows": rows, "prefs": _prefs(db, user),
        "is_pro": services.is_pro_user(db, user),
        "departments": departments.DEPARTMENTS,
        "limited": request.query_params.get("limit") == "1",
    })


@router.post("/company")
def create_company(request: Request, name: str = Form(...), industry: str = Form(""),
                   sub_industry: str = Form(""), employee_count: str = Form(""),
                   revenue_band: str = Form(""), country: str = Form(""),
                   city: str = Form(""), user=Depends(get_current_user),
                   db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not name.strip():
        return RedirectResponse("/company", status_code=303)
    if _owned_orgs(db, user) and not services.is_pro_user(db, user):
        return RedirectResponse("/company?limit=1", status_code=303)
    org = models.Organization(
        name=name.strip()[:160],
        industry=industry.strip()[:120] or None,
        sub_industry=sub_industry.strip()[:120] or None,
        employee_count=_parse_staff(employee_count),
        revenue_band=revenue_band.strip()[:80] or None,
        country=country.strip()[:80] or None,
        city=city.strip()[:80] or None,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    _claim(db, user.id, org.id)
    return RedirectResponse(f"/dashboard?org={org.id}", status_code=303)


@router.post("/company/{organization_id}/edit")
def edit_company(organization_id: int, name: str = Form(...), industry: str = Form(""),
                 sub_industry: str = Form(""), employee_count: str = Form(""),
                 revenue_band: str = Form(""), country: str = Form(""),
                 city: str = Form(""), user=Depends(get_current_user),
                 db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    org = db.get(models.Organization, organization_id)
    if org is None or organization_id not in services.owned_org_ids(db, user):
        return RedirectResponse("/company", status_code=303)
    if name.strip():
        org.name = name.strip()[:160]
    org.industry = industry.strip()[:120] or None
    org.sub_industry = sub_industry.strip()[:120] or None
    org.employee_count = _parse_staff(employee_count)
    org.revenue_band = revenue_band.strip()[:80] or None
    org.country = country.strip()[:80] or None
    org.city = city.strip()[:80] or None
    db.commit()
    return RedirectResponse(f"/company#org-{org.id}", status_code=303)


@router.get("/pro")
def pro_page(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    prefs = _prefs(db, user)
    return templates.TemplateResponse(request, "pro.html", {
        "user": user, "prefs": prefs, "orgs": _owned_orgs(db, user),
        "plans": premium.PLANS, "features": premium.FEATURES,
        "currency": premium.CURRENCY, "is_pro": services.is_pro_user(db, user),
        "upgraded": request.query_params.get("upgraded") == "1",
        "locked": request.query_params.get("locked") or "",
    })


@router.post("/pro/checkout")
def pro_checkout(request: Request, billing: str = Form("annual"),
                 user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    cycle = "annual" if billing == "annual" else "monthly"
    amount = premium.amount_minor(cycle)
    ref = paystack.new_reference("PRE")
    db.add(models.Payment(
        user_id=user.id, reference=ref, purpose="premium", amount_kes=0,
        currency=premium.CURRENCY, amount_minor=amount, billing_cycle=cycle,
        status="pending"))
    db.commit()
    base = str(request.base_url).rstrip("/")
    data = paystack.initialize(
        user.email, amount, ref, f"{base}/pay/return/{ref}",
        {"purpose": "premium", "billing": cycle, "price_usd": premium.plan(cycle)["price"]},
        currency=premium.CURRENCY)
    return RedirectResponse(data["authorization_url"], status_code=303)


@router.get("/physical")
def physical_page(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    return RedirectResponse("/pro", status_code=303)


@router.post("/physical")
def physical_request(request: Request, company_name: str = Form(...), package: str = Form(...),
                     sites: str = Form("1"), notes: str = Form(""),
                     organization_id: str = Form(""),
                     user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    spec = PACKAGES.get(package)
    if spec is None:
        return RedirectResponse("/pro", status_code=303)
    label, amount, _ = spec
    site_n = int(sites) if sites.strip().isdigit() else 1
    amount = amount + max(0, site_n - 1) * 60_000
    row = models.PhysicalRequest(
        user_id=user.id,
        organization_id=int(organization_id) if organization_id.strip().isdigit() else None,
        company_name=company_name.strip()[:160],
        package=package,
        amount_kes=amount,
        sites=site_n,
        notes=notes.strip() or None,
        status="awaiting_payment",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    ref = paystack.new_reference("PHY")
    db.add(models.Payment(user_id=user.id, reference=ref, purpose="physical",
                          amount_kes=amount, currency="KES", amount_minor=amount * 100,
                          related_id=row.id, status="pending"))
    db.commit()
    base = str(request.base_url).rstrip("/")
    data = paystack.initialize(user.email, amount * 100, ref, f"{base}/pay/return/{ref}",
                               {"purpose": "physical", "request_id": row.id, "package": label},
                               currency="KES")
    return RedirectResponse(data["authorization_url"], status_code=303)


@router.get("/pay/dummy/{reference}")
def dummy_checkout(reference: str, request: Request, user=Depends(get_current_user),
                   db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    payment = db.scalar(select(models.Payment).where(models.Payment.reference == reference))
    if payment is None or payment.user_id != user.id:
        return RedirectResponse("/pro", status_code=303)
    return templates.TemplateResponse(request, "pay_dummy.html", {
        "user": user, "payment": payment, "public_key": paystack.PUBLIC,
    })


@router.post("/pay/dummy/{reference}")
def dummy_confirm(reference: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    return RedirectResponse(f"/pay/return/{reference}?simulate=success", status_code=303)


def _payment_matches(payment: models.Payment, verified: dict) -> bool:
    if verified.get("status") != "success" or verified.get("reference") != payment.reference:
        return False
    expected = (payment.amount_minor if payment.amount_minor is not None
                else int(round(payment.amount_kes * 100)))
    paid = verified.get("amount")
    if paid is not None and int(paid) != int(expected):
        return False
    expected_currency = (payment.currency or "KES").upper()
    paid_currency = verified.get("currency")
    if paid_currency and str(paid_currency).upper() != expected_currency:
        return False
    return True


def _apply_payment(db: Session, payment: models.Payment, verified: dict) -> bool:
    """Idempotently mark a payment paid and grant the matching entitlement."""
    if payment.status == "success":
        return True
    if not _payment_matches(payment, verified):
        return False
    from elipsis_api.models import _now
    payment.status = "success"
    payment.paid_at = _now()
    if payment.purpose in {"pro", "premium"} and payment.user_id:
        user = db.get(models.User, payment.user_id)
        if user is not None:
            prefs = _prefs(db, user)
            if prefs.pro_until != "active":
                days = (365 if payment.purpose == "pro" or payment.billing_cycle == "annual"
                        else premium.MONTHLY_DAYS)
                now = datetime.now(UTC).replace(tzinfo=None)
                start = now
                if prefs.pro_until:
                    try:
                        start = max(start, datetime.fromisoformat(prefs.pro_until))
                    except ValueError:
                        pass
                prefs.pro_until = (start + timedelta(days=days)).isoformat(timespec="seconds")
    if payment.purpose == "physical" and payment.related_id:
        req = db.get(models.PhysicalRequest, payment.related_id)
        if req:
            req.status = "open_bid"
    db.commit()
    return True


def _payment_destination(payment: models.Payment) -> str:
    if payment.purpose in {"pro", "premium"}:
        return "/pro?upgraded=1"
    return "/company"


@router.get("/pay/return/{reference}")
def pay_return(reference: str, request: Request, user=Depends(get_current_user),
               db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    payment = db.scalar(select(models.Payment).where(models.Payment.reference == reference))
    if payment is None or payment.user_id != user.id:
        return RedirectResponse("/pro", status_code=303)
    try:
        verified = paystack.verify(reference)
    except Exception:  # noqa: BLE001
        verified = {}
    _apply_payment(db, payment, verified)
    return RedirectResponse(_payment_destination(payment), status_code=303)


@router.post("/paystack/webhook")
async def paystack_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        paystack.ensure_configured()
    except RuntimeError:
        return JSONResponse({"detail": "payment provider not configured"}, status_code=503)
    raw = await request.body()
    signature = request.headers.get("x-paystack-signature")
    if not paystack.verify_webhook(raw, signature):
        return JSONResponse({"detail": "invalid signature"}, status_code=401)
    try:
        event = json.loads(raw.decode())
    except (ValueError, UnicodeDecodeError):
        return JSONResponse({"detail": "invalid payload"}, status_code=400)
    if event.get("event") != "charge.success":
        return JSONResponse({"status": "ignored"})
    data = event.get("data") or {}
    reference = data.get("reference") or ""
    payment = db.scalar(select(models.Payment).where(
        models.Payment.reference == reference))
    if payment is None:
        return JSONResponse({"status": "ignored"})
    verified = {
        "status": "success",
        "reference": reference,
        "amount": data.get("amount"),
        "currency": data.get("currency"),
    }
    if not _apply_payment(db, payment, verified):
        return JSONResponse({"detail": "payment mismatch"}, status_code=400)
    return JSONResponse({"status": "ok"})


@router.get("/bids")
def bids(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not services.is_pro_user(db, user):
        return RedirectResponse("/pro?locked=bids", status_code=303)
    rows = list(db.scalars(select(models.PhysicalRequest).where(
        models.PhysicalRequest.status == "open_bid").order_by(models.PhysicalRequest.id.desc())))
    mine = {r.id for r in rows if r.user_id == user.id}
    return templates.TemplateResponse(request, "bids.html", {
        "user": user, "rows": rows, "packages": PACKAGES, "mine": mine, "is_admin": _is_admin(user),
    })


@router.get("/settings")
def settings(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    org_ids = services.visible_org_ids(db, user)
    hooks = services_webhooks.endpoints(db, org_ids)
    deliveries = list(db.scalars(select(models.WebhookDelivery).where(
        models.WebhookDelivery.endpoint_id.in_([h.id for h in hooks] or [0])
    ).order_by(models.WebhookDelivery.id.desc()).limit(20))) if hooks else []
    organizations = services.list_organizations(db, org_ids)
    managed = [org for org in organizations if services.can_manage_org(db, user, org.id)]
    from elipsis_api import services_room
    return templates.TemplateResponse(request, "settings.html", {
        "user": user, "prefs": _prefs(db, user), "webhooks": hooks,
        "deliveries": deliveries, "events": sorted(services_webhooks.ALLOWED_EVENTS),
        "organizations": organizations, "managed_orgs": managed,
        "branding": {org.id: services_room.branding(org) for org in managed},
        "departments": departments.DEPARTMENTS,
        "webhook_message": request.query_params.get("webhook"),
        "saved": request.query_params.get("saved") == "1",
        "password_message": request.query_params.get("password"),
        "company_saved": request.query_params.get("company") == "saved",
        "company_error": request.query_params.get("company_error"),
    })


@router.post("/settings")
def settings_save(symbol: str = Form("E"), motion: str = Form("on"), density: str = Form("comfortable"),
                  name: str = Form(""), job_title: str = Form(""), phone: str = Form(""),
                  bio: str = Form(""), landing_page: str = Form("/dashboard"),
                  digest_day: str = Form("monday"), quiet_hours: str = Form(""),
                  notify_email: str = Form(""), notify_team: str = Form(""),
                  notify_reports: str = Form(""), notify_actions: str = Form(""),
                  default_organization_id: str = Form(""),
                  default_department: str = Form(""),
                  user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if (name or "").strip():
        user.name = name.strip()[:120]
    prefs = _prefs(db, user)
    prefs.symbol = (symbol or "E").strip()[:2] or "E"
    prefs.motion = "off" if motion == "off" else "on"
    prefs.density = density if density in {"comfortable", "compact"} else "comfortable"
    prefs.job_title = (job_title or "").strip()[:120] or None
    prefs.phone = (phone or "").strip()[:40] or None
    prefs.bio = (bio or "").strip()[:500] or None
    prefs.landing_page = landing_page if landing_page in {
        "/dashboard", "/assessments", "/actions", "/company", "/operations"} else "/dashboard"
    prefs.digest_day = digest_day if digest_day in {
        "monday", "tuesday", "wednesday", "thursday", "friday"} else "monday"
    prefs.quiet_hours = (quiet_hours or "").strip()[:40] or None
    prefs.notify_email = 1 if notify_email else 0
    prefs.notify_team = 1 if notify_team else 0
    prefs.notify_reports = 1 if notify_reports else 0
    prefs.notify_actions = 1 if notify_actions else 0
    prefs.default_department = (
        default_department if default_department in departments.DEPARTMENT_LABELS else None)
    org_id = int(default_organization_id) if default_organization_id.strip().isdigit() else None
    if org_id and services.can_access_org(db, user, org_id):
        prefs.default_organization_id = org_id
    db.commit()
    response = RedirectResponse("/settings?saved=1", status_code=303)
    response.set_cookie("elipsis_motion", prefs.motion, max_age=60 * 60 * 24 * 365, samesite="lax")
    response.set_cookie("elipsis_density", prefs.density, max_age=60 * 60 * 24 * 365, samesite="lax")
    response.set_cookie("elipsis_symbol", prefs.symbol, max_age=60 * 60 * 24 * 365, samesite="lax")
    return response


@router.post("/settings/password")
def settings_password(current_password: str = Form(""), new_password: str = Form(""),
                      confirm_password: str = Form(""),
                      user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not security.verify_password(current_password, user.password_hash):
        return RedirectResponse("/settings?password=current", status_code=303)
    if len(new_password or "") < 8:
        return RedirectResponse("/settings?password=short", status_code=303)
    if new_password != confirm_password:
        return RedirectResponse("/settings?password=mismatch", status_code=303)
    user.password_hash = security.hash_password(new_password)
    db.commit()
    return RedirectResponse("/settings?password=changed", status_code=303)


@router.post("/settings/webhooks")
def webhook_create(organization_id: int = Form(...), url: str = Form(...),
                   events: list[str] = Form([]),
                   user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not services.can_access_org(db, user, organization_id):
        return RedirectResponse("/settings?webhook=denied", status_code=303)
    _, error = services_webhooks.create_endpoint(
        db, organization_id, url, events, user.id)
    return RedirectResponse(
        f"/settings?webhook={'saved' if not error else 'invalid'}", status_code=303)


@router.post("/settings/webhooks/{endpoint_id}/delete")
def webhook_delete(endpoint_id: int, user=Depends(get_current_user),
                   db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    services_webhooks.delete_endpoint(
        db, services.visible_org_ids(db, user), endpoint_id)
    return RedirectResponse("/settings?webhook=deleted", status_code=303)


@router.post("/settings/webhooks/{endpoint_id}/test")
async def webhook_test(endpoint_id: int, background_tasks: BackgroundTasks,
                       user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    endpoint = db.get(models.WebhookEndpoint, endpoint_id)
    if endpoint is None or not services.can_access_org(db, user, endpoint.organization_id):
        return RedirectResponse("/settings?webhook=denied", status_code=303)
    background_tasks.add_task(
        services_webhooks.deliver_event, endpoint.id, "webhook.test",
        {"event": "webhook.test", "endpoint_id": endpoint.id,
         "message": "Elipsis webhook test"})
    return RedirectResponse("/settings?webhook=test_queued", status_code=303)


@router.get("/inbox")
def inbox(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if _is_admin(user):
        return RedirectResponse("/admin/letters", status_code=303)
    return RedirectResponse("/letter", status_code=303)


@router.get("/letter")
def letter(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse(request, "letter.html", {"user": user, "sent": False})


@router.post("/letter")
def letter_send(request: Request, name: str = Form(...), email: str = Form(...),
                organization: str = Form(""), role_title: str = Form(""), body: str = Form(...),
                user=Depends(get_current_user), db: Session = Depends(get_db)):
    db.add(models.TeamLetter(
        user_id=user.id if user else None,
        name=name.strip()[:120],
        email=email.strip()[:160],
        organization=organization.strip()[:160] or None,
        role_title=role_title.strip()[:120] or None,
        body=body.strip()[:8000],
    ))
    db.commit()
    return templates.TemplateResponse(request, "letter.html", {"user": user, "sent": True})


@router.get("/admin/letters")
def admin_letters(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not _is_admin(user):
        return RedirectResponse("/letter", status_code=303)
    rows = list(db.scalars(select(models.TeamLetter).order_by(models.TeamLetter.id.desc())))
    return templates.TemplateResponse(request, "admin_letters.html", {"user": user, "rows": rows})
