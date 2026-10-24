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
    services_success,
    services_webhooks,
)
from elipsis_api.config import BILLING_ENABLED
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user, login_redirect, templates
from elipsis_api.narrative import company_portrait

router = APIRouter()


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
    if not BILLING_ENABLED:
        return RedirectResponse("/pricing?billing=unavailable", status_code=303)
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
        currency=premium.CURRENCY, plan_code=premium.requester_plan_code(cycle))
    return RedirectResponse(data["authorization_url"], status_code=303)


@router.get("/physical")
def physical_page(request: Request, user=Depends(get_current_user)):
    if user is None:
        return login_redirect()
    return RedirectResponse("/marketplace/requests/new", status_code=303)


@router.post("/physical")
def physical_request(user=Depends(get_current_user)):
    if user is None:
        return login_redirect()
    return RedirectResponse("/marketplace/requests/new", status_code=303)


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


def _payment_description(db: Session, payment: models.Payment) -> str:
    if payment.purpose in {"pro", "premium"}:
        cycle = "annual" if payment.billing_cycle == "annual" else "monthly"
        return f"Premium {cycle} pass"
    if payment.purpose == "assessment" and payment.related_id:
        assessment = db.get(models.Assessment, payment.related_id)
        org = (db.get(models.Organization, assessment.organization_id)
               if assessment is not None else None)
        return f"Full Assessment for {org.name}" if org else "Full Assessment"
    if payment.purpose == "bidder_plan":
        plan = premium.BIDDER_PLANS.get(payment.billing_cycle or "")
        return f"Bidder {plan['label']} plan" if plan else "Bidder subscription"
    if payment.purpose == "switch_topup":
        return "Three-switch top-up"
    if payment.purpose == "physical":
        return "Physical assessment request"
    return "Elipsis payment"


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
    if payment.purpose == "assessment" and payment.related_id:
        assessment = db.get(models.Assessment, payment.related_id)
        if assessment is not None:
            purchase = db.scalar(select(models.AssessmentPurchase).where(
                models.AssessmentPurchase.assessment_id == assessment.id))
            if purchase is None:
                db.add(models.AssessmentPurchase(
                    user_id=payment.user_id, assessment_id=assessment.id,
                    source="one_time", payment_reference=payment.reference,
                    switches_granted=premium.SWITCH_TOPUP_COUNT, active=True))
            else:
                purchase.user_id = payment.user_id
                purchase.payment_reference = payment.reference
                purchase.active = True
    if payment.purpose == "switch_topup" and payment.related_id:
        req = db.get(models.PhysicalAssessmentRequest, payment.related_id)
        if req is not None:
            req.switches_granted = (req.switches_granted or 3) + premium.SWITCH_TOPUP_COUNT
            req.topup_count = (req.topup_count or 0) + 1
    if payment.purpose == "bidder_plan" and payment.related_id:
        bidder = db.get(models.BidderCompany, payment.related_id)
        plan_info = premium.BIDDER_PLANS.get(payment.billing_cycle or "")
        if bidder is not None and plan_info is not None:
            now = datetime.now(UTC).replace(tzinfo=None)
            start = now
            existing = None
            if bidder.subscription_expires_at:
                try:
                    existing = datetime.fromisoformat(bidder.subscription_expires_at)
                except ValueError:
                    existing = None
            if existing and existing > now and bidder.subscription_status == "active":
                start = existing
            bidder.subscription_tier = payment.billing_cycle
            bidder.subscription_status = "active"
            bidder.subscription_expires_at = (
                start + timedelta(days=plan_info["days"])).isoformat(timespec="seconds")
            db.add(models.Subscription(
                bidder_company_id=bidder.id, tier=payment.billing_cycle,
                start_date=now.isoformat(timespec="seconds"),
                end_date=bidder.subscription_expires_at,
                payment_reference=payment.reference, status="active"))
    description = _payment_description(db, payment)
    destination = _payment_destination(payment)
    amount = f"${(payment.amount_minor or 0) / 100:,.2f} {payment.currency or premium.CURRENCY}"
    db.commit()
    from elipsis_api.services_email_events import send_user_event_sync
    send_user_event_sync(
        db, payment.user_id, "payment_receipt", description=description,
        amount=amount, reference=payment.reference, url=destination)
    return True


def _billing_now() -> str:
    return datetime.now(UTC).replace(tzinfo=None).isoformat(timespec="seconds")


def _billing_email(data: dict) -> str:
    customer = data.get("customer") or {}
    return (customer.get("email") or data.get("email") or "").strip().lower()


def _billing_plan(data: dict) -> tuple[str, str] | None:
    plan = data.get("plan") or {}
    code = plan.get("plan_code") if isinstance(plan, dict) else plan
    code = code or data.get("plan_code") or ""
    return premium.plan_for_code(code)


def _provider_charge(db: Session, data: dict) -> bool:
    """Grant access for a renewal charge that has no local Payment row."""
    parsed = _billing_plan(data)
    if parsed is None:
        return False
    purpose, cycle = parsed
    email = _billing_email(data)
    user = db.scalar(select(models.User).where(func.lower(models.User.email) == email))
    if user is None:
        return False
    plan_info = (premium.BIDDER_PLANS.get(cycle) if purpose == "bidder_plan"
                 else premium.plan(cycle))
    if plan_info is None:
        return False
    amount = data.get("amount")
    currency = (data.get("currency") or premium.CURRENCY).upper()
    if currency != premium.CURRENCY:
        return False
    if amount is not None and int(amount) < int(plan_info["price"] * 100):
        return False
    reference = data.get("reference") or ""
    if not reference:
        return False
    related_id = None
    if purpose == "bidder_plan":
        bidder = db.scalar(select(models.BidderCompany).where(
            models.BidderCompany.user_id == user.id))
        if bidder is None:
            return False
        related_id = bidder.id
    payment = models.Payment(
        user_id=user.id, reference=reference, purpose=purpose, amount_kes=0,
        currency=premium.CURRENCY, amount_minor=int(amount or plan_info["price"] * 100),
        billing_cycle=cycle, related_id=related_id, status="pending")
    db.add(payment)
    db.flush()
    verified = {
        "status": "success", "reference": reference,
        "amount": payment.amount_minor, "currency": premium.CURRENCY,
    }
    return _apply_payment(db, payment, verified)


def _billing_subscription_row(db: Session, code: str):
    return db.scalar(select(models.BillingSubscription).where(
        models.BillingSubscription.provider_subscription_code == code))


def _record_provider_subscription(db: Session, data: dict) -> None:
    code = data.get("subscription_code") or ""
    if not code:
        return
    parsed = _billing_plan(data)
    if parsed is None:
        return
    purpose, _cycle = parsed
    email = _billing_email(data)
    user = db.scalar(select(models.User).where(func.lower(models.User.email) == email))
    if user is None:
        return
    plan = data.get("plan") or {}
    plan_code = plan.get("plan_code") if isinstance(plan, dict) else (plan or "")
    row = _billing_subscription_row(db, code)
    if row is None:
        row = models.BillingSubscription(
            user_id=user.id, plan_code=plan_code or "",
            provider_subscription_code=code, provider_email_token=data.get("email_token"),
            status="active", current_period_start=_billing_now(),
            current_period_end=data.get("next_payment_date"),
            created_at=_billing_now(), updated_at=_billing_now())
        db.add(row)
    else:
        row.user_id = user.id
        row.plan_code = plan_code or row.plan_code
        row.provider_email_token = data.get("email_token") or row.provider_email_token
        row.status = "active"
        row.updated_at = _billing_now()
    if purpose == "bidder_plan":
        bidder = db.scalar(select(models.BidderCompany).where(
            models.BidderCompany.user_id == user.id))
        row.bidder_company_id = bidder.id if bidder else row.bidder_company_id
    db.commit()


def _update_provider_subscription(db: Session, data: dict, status: str,
                                  cancel: bool = False, grace: bool = False) -> None:
    code = data.get("subscription_code") or ""
    subscription = data.get("subscription") or {}
    if not code and isinstance(subscription, dict):
        code = subscription.get("subscription_code") or ""
    if not code:
        return
    row = _billing_subscription_row(db, code)
    if row is None:
        _record_provider_subscription(db, data)
        row = _billing_subscription_row(db, code)
    if row is None:
        return
    row.status = status
    row.cancel_at_period_end = cancel
    if grace:
        row.grace_until = (
            datetime.now(UTC).replace(tzinfo=None) + timedelta(days=3)
        ).isoformat(timespec="seconds")
    row.updated_at = _billing_now()
    db.commit()
    parsed = premium.plan_for_code(row.plan_code)
    if parsed is not None:
        purpose, cycle = parsed
        plan_info = (premium.BIDDER_PLANS.get(cycle) if purpose == "bidder_plan"
                     else premium.plan(cycle))
        plan_label = plan_info.get("label") if plan_info else "Elipsis subscription"
    else:
        plan_label = "Elipsis subscription"
    from elipsis_api.services_email_events import send_user_event_sync
    if grace:
        send_user_event_sync(
            db, row.user_id, "payment_failed", plan=plan_label,
            grace_until=row.grace_until, url="/pro")
    elif cancel:
        send_user_event_sync(
            db, row.user_id, "subscription_cancelled", plan=plan_label,
            access_until=row.current_period_end or row.grace_until, url="/pro")


def _payment_destination(payment: models.Payment) -> str:
    if payment.purpose in {"pro", "premium"}:
        return "/pro?upgraded=1"
    if payment.purpose == "assessment" and payment.related_id:
        return f"/assessment/{payment.related_id}/results?unlocked=1"
    if payment.purpose == "switch_topup" and payment.related_id:
        return f"/marketplace/{payment.related_id}?topup=1"
    if payment.purpose == "bidder_plan":
        return "/marketplace/partner?subscribed=1"
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
    name = event.get("event")
    data = event.get("data") or {}
    if name == "charge.success":
        reference = data.get("reference") or ""
        payment = db.scalar(select(models.Payment).where(
            models.Payment.reference == reference))
        if payment is None:
            if _provider_charge(db, data):
                return JSONResponse({"status": "ok"})
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
    if name == "subscription.create":
        _record_provider_subscription(db, data)
        return JSONResponse({"status": "ok"})
    if name == "subscription.not_renew":
        _update_provider_subscription(db, data, "active", cancel=True)
        return JSONResponse({"status": "ok"})
    if name == "subscription.disable":
        _update_provider_subscription(db, data, "cancelled", cancel=True)
        return JSONResponse({"status": "ok"})
    if name == "invoice.payment_failed":
        _update_provider_subscription(db, data, "attention", grace=True)
        return JSONResponse({"status": "ok"})
    return JSONResponse({"status": "ignored"})


@router.get("/bids")
def bids(user=Depends(get_current_user)):
    if user is None:
        return login_redirect()
    return RedirectResponse("/marketplace", status_code=303)


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
        "timezone_choices": services_success.TIMEZONE_CHOICES,
        "legal": services_success.legal_state(db, user),
    })


@router.post("/settings")
def settings_save(symbol: str = Form("E"), motion: str = Form("on"), density: str = Form("comfortable"),
                  name: str = Form(""), job_title: str = Form(""), phone: str = Form(""),
                  bio: str = Form(""), landing_page: str = Form("/dashboard"),
                  digest_day: str = Form("monday"), quiet_hours: str = Form(""),
                  timezone: str = Form("UTC"),
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
    allowed_zones = {key for key, _ in services_success.TIMEZONE_CHOICES}
    prefs.timezone = timezone if timezone in allowed_zones else "UTC"
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
