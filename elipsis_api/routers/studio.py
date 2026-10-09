"""Company workspace, Pro features, settings, letters, physical bids, Paystack."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from elipsis_api import models, paystack, services
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
PRO_PRICE = 45_000


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
        rows.append({
            "org": org, "overview": overview, "portrait": portrait, "insight": insight,
            "latest": latest, "assessments": overview["rows"],
            "spark": analytics.sparkline([t["value"] for t in overview["trend"]]),
            "editing": request.query_params.get("edit") == str(org.id),
        })
    return templates.TemplateResponse(request, "company.html", {
        "user": user, "rows": rows, "prefs": _prefs(db, user),
    })


@router.post("/company")
def create_company(request: Request, name: str = Form(...), industry: str = Form(""),
                   employee_count: str = Form(""), country: str = Form("Kenya"),
                   city: str = Form(""), user=Depends(get_current_user),
                   db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not name.strip():
        return RedirectResponse("/company", status_code=303)
    org = models.Organization(
        name=name.strip()[:160],
        industry=industry.strip()[:120] or None,
        employee_count=_parse_staff(employee_count),
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
                 employee_count: str = Form(""), country: str = Form(""),
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
    org.employee_count = _parse_staff(employee_count)
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
        "user": user, "prefs": prefs, "packages": PACKAGES, "pro_price": PRO_PRICE,
        "orgs": _owned_orgs(db, user),
    })


@router.post("/pro/checkout")
def pro_checkout(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    ref = paystack.new_reference("PRO")
    db.add(models.Payment(user_id=user.id, reference=ref, purpose="pro",
                          amount_kes=PRO_PRICE, status="pending"))
    db.commit()
    base = str(request.base_url).rstrip("/")
    data = paystack.initialize(user.email, PRO_PRICE, ref, f"{base}/pay/return/{ref}",
                               {"purpose": "pro"})
    return RedirectResponse(data["authorization_url"], status_code=303)


@router.get("/physical")
def physical_page(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """On-site / physical assessment — public nav lands here; form lives on /pro."""
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
                          amount_kes=amount, related_id=row.id, status="pending"))
    db.commit()
    base = str(request.base_url).rstrip("/")
    data = paystack.initialize(user.email, amount, ref, f"{base}/pay/return/{ref}",
                               {"purpose": "physical", "request_id": row.id, "package": label})
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


@router.get("/pay/return/{reference}")
def pay_return(reference: str, request: Request, user=Depends(get_current_user),
               db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    payment = db.scalar(select(models.Payment).where(models.Payment.reference == reference))
    if payment is None or payment.user_id != user.id:
        return RedirectResponse("/pro", status_code=303)
    verified = paystack.verify(reference)
    if verified.get("status") == "success":
        payment.status = "success"
        if payment.purpose == "pro":
            prefs = _prefs(db, user)
            prefs.pro_until = "active"
        if payment.purpose == "physical" and payment.related_id:
            req = db.get(models.PhysicalRequest, payment.related_id)
            if req:
                req.status = "open_bid"
        db.commit()
    dest = "/bids" if payment.purpose == "pro" else "/company"
    return RedirectResponse(dest, status_code=303)


@router.get("/bids")
def bids(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    prefs = _prefs(db, user)
    if prefs.pro_until != "active" and not _is_admin(user):
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
    return templates.TemplateResponse(request, "settings.html", {
        "user": user, "prefs": _prefs(db, user),
    })


@router.post("/settings")
def settings_save(symbol: str = Form("E"), motion: str = Form("on"), density: str = Form("comfortable"),
                  user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    prefs = _prefs(db, user)
    prefs.symbol = (symbol or "E").strip()[:2] or "E"
    prefs.motion = "off" if motion == "off" else "on"
    prefs.density = density if density in {"comfortable", "compact"} else "comfortable"
    db.commit()
    response = RedirectResponse("/settings", status_code=303)
    response.set_cookie("elipsis_motion", prefs.motion, max_age=60 * 60 * 24 * 365, samesite="lax")
    response.set_cookie("elipsis_density", prefs.density, max_age=60 * 60 * 24 * 365, samesite="lax")
    response.set_cookie("elipsis_symbol", prefs.symbol, max_age=60 * 60 * 24 * 365, samesite="lax")
    return response


@router.get("/inbox")
def inbox(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Letters inbox — admins see the board; everyone else writes a letter."""
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
