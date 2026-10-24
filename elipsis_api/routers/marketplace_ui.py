"""Server-rendered marketplace + admin request desk pages."""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from elipsis_api import models, paystack, services
from elipsis_api.config import (
    BILLING_ENABLED,
    HANDOFF_ENABLED,
    MARKETPLACE_ENABLED,
    MESSAGING_ENABLED,
    VERIFICATION_ENABLED,
)
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user, login_redirect, templates
from elipsis_api.services_marketplace import (
    BID_APPROVED,
    BID_AWARDED,
    REQUEST_APPROVED,
    REQUEST_AWARDED,
    REQUEST_PENDING,
    REQUEST_REJECTED,
    VISIBLE_REQUEST_STATUSES,
    assessment_is_unlocked,
    bidder_slug,
    bidder_verification_label,
    can_view_bid,
    can_view_contact_details,
    can_view_conversation,
    can_view_full_request,
    conversation_deadline,
    is_active_bidder,
    is_request_owner,
    notify_user,
    now_iso,
    refresh_conversation,
    request_conversation,
    switch_candidates,
    switch_request,
    switches_remaining,
)
from elipsis_api.services_ops import record_audit

router = APIRouter()


def _flag_page(request, user, enabled: bool, message: str = "This feature is not available."):
    if enabled:
        return None
    return templates.TemplateResponse(
        request, "404.html", {"user": user, "message": message}, status_code=404)


def _s3_configured() -> bool:
    from elipsis_api.services_s3 import is_s3_configured
    return is_s3_configured()


def _not_found(request, user):
    return templates.TemplateResponse(request, "404.html", {"user": user}, status_code=404)


def _admin_ok(user) -> bool:
    if user is None:
        return False
    if services.is_admin(user):
        return True
    if getattr(user, "is_admin", False):
        return True
    return (getattr(user, "role", "") or "") == "admin"


@router.get("/marketplace")
def marketplace_list(request: Request, user=Depends(get_current_user),
                     db: Session = Depends(get_db)):
    """Public marketplace of published engagement requests."""
    if not MARKETPLACE_ENABLED and not _admin_ok(user):
        return templates.TemplateResponse(
            request, "marketplace_coming_soon.html", {"user": user})
    rows = db.scalars(
        select(models.PhysicalAssessmentRequest)
        .where(models.PhysicalAssessmentRequest.status.in_(VISIBLE_REQUEST_STATUSES))
        .order_by(models.PhysicalAssessmentRequest.id.desc())
    ).all()
    viewer_is_bidder = bool(user and is_active_bidder(db, user.id))
    requests = []
    for req in rows:
        org = db.get(models.Organization, req.organization_id)
        bid_count = db.scalar(
            select(func.count()).select_from(models.BidSubmission).where(
                models.BidSubmission.request_id == req.id,
                models.BidSubmission.status.in_((BID_APPROVED, BID_AWARDED)))
        ) or 0
        requests.append({
            "id": req.id,
            "title": req.title,
            "message": req.message,
            "requirements": req.requirements,
            "status": req.status,
            "created_at": req.created_at,
            "bid_count": int(bid_count),
            "organization": {
                "name": org.name if viewer_is_bidder else "Verified client",
                "industry": org.industry,
                "company_size": org.company_size,
                "country": org.country,
            } if org else None,
            "can_view_full": bool(user and can_view_full_request(db, user, req)),
        })
    return templates.TemplateResponse(
        request, "marketplace.html",
        {"user": user, "requests": requests, "count": len(requests)})


@router.get("/marketplace/requests")
def marketplace_requests_page(request: Request, user=Depends(get_current_user),
                              db: Session = Depends(get_db)):
    return marketplace_list(request, user, db)


def _bidder_slug(bidder: models.BidderCompany) -> str:
    if bidder.slug:
        return bidder.slug
    return f"company-{bidder.id}"


def _directory_rows(db: Session) -> list[dict]:
    rows = db.scalars(select(models.BidderCompany).where(
        models.BidderCompany.verification_status == "approved"
    ).order_by(
        models.BidderCompany.pinned_rank.is_(None),
        models.BidderCompany.pinned_rank.asc(),
        models.BidderCompany.company_name.asc(),
    )).all()
    out = []
    for row in rows:
        out.append({
            "row": row,
            "slug": _bidder_slug(row),
            "pinned": (row.pinned_rank or 0) > 0 or (row.partner_tier or "") == "trusted",
            "active": is_active_bidder(db, row.user_id),
        })
    return out


@router.get("/marketplace/companies")
def marketplace_companies(request: Request, user=Depends(get_current_user),
                          db: Session = Depends(get_db)):
    if not MARKETPLACE_ENABLED and not _admin_ok(user):
        return templates.TemplateResponse(
            request, "marketplace_coming_soon.html", {"user": user})
    return templates.TemplateResponse(
        request, "marketplace_companies.html",
        {"user": user, "companies": _directory_rows(db)})


@router.get("/marketplace/companies/{slug}")
def marketplace_company(slug: str, request: Request, user=Depends(get_current_user),
                        db: Session = Depends(get_db)):
    if not MARKETPLACE_ENABLED and not _admin_ok(user):
        return templates.TemplateResponse(
            request, "marketplace_coming_soon.html", {"user": user})
    row = db.scalar(select(models.BidderCompany).where(
        models.BidderCompany.slug == slug))
    if row is None and slug.startswith("company-") and slug[8:].isdigit():
        row = db.get(models.BidderCompany, int(slug[8:]))
    if row is None or row.verification_status != "approved":
        return _not_found(request, user)
    return templates.TemplateResponse(
        request, "marketplace_company.html",
        {"user": user, "company": row, "slug": _bidder_slug(row),
         "pinned": (row.pinned_rank or 0) > 0 or (row.partner_tier or "") == "trusted",
         "active": is_active_bidder(db, row.user_id)})


@router.get("/marketplace/partner")
def marketplace_partner(request: Request, user=Depends(get_current_user),
                        db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    blocked = _flag_page(request, user, VERIFICATION_ENABLED)
    if blocked:
        return blocked
    from elipsis_api import premium
    bidder = db.scalar(select(models.BidderCompany).where(
        models.BidderCompany.user_id == user.id))
    documents = []
    if bidder is not None:
        documents = db.scalars(select(models.BidderVerificationDocument).where(
            models.BidderVerificationDocument.bidder_company_id == bidder.id
        ).order_by(models.BidderVerificationDocument.id.desc())).all()
    return templates.TemplateResponse(
        request, "marketplace_partner.html",
        {"user": user, "bidder": bidder, "documents": documents,
         "plans": premium.BIDDER_PLANS, "billing_enabled": BILLING_ENABLED,
         "active": bool(bidder and is_active_bidder(db, bidder.user_id)),
         "subscribed": request.query_params.get("subscribed") == "1",
         "error": request.query_params.get("error")})


@router.post("/marketplace/partner/subscribe")
def marketplace_partner_subscribe(request: Request, tier: str = Form("monthly"),
                                  user=Depends(get_current_user),
                                  db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not BILLING_ENABLED:
        return RedirectResponse("/marketplace/partner?error=Billing+is+not+available",
                                status_code=303)
    from elipsis_api import premium
    plan_info = premium.BIDDER_PLANS.get(tier)
    bidder = db.scalar(select(models.BidderCompany).where(
        models.BidderCompany.user_id == user.id))
    if bidder is None:
        return RedirectResponse("/marketplace/apply?error=Complete+your+application+first",
                                status_code=303)
    if bidder.verification_status != "approved":
        return RedirectResponse(
            "/marketplace/partner?error=Your+company+must+be+verified+before+subscribing",
            status_code=303)
    if plan_info is None:
        return RedirectResponse("/marketplace/partner?error=Choose+a+valid+plan",
                                status_code=303)
    ref = paystack.new_reference("BID")
    amount = int(plan_info["price"] * 100)
    db.add(models.Payment(
        user_id=user.id, reference=ref, purpose="bidder_plan", amount_kes=0,
        currency=premium.CURRENCY, amount_minor=amount, billing_cycle=tier,
        related_id=bidder.id, status="pending"))
    db.commit()
    base = str(request.base_url).rstrip("/")
    data = paystack.initialize(
        user.email, amount, ref, f"{base}/pay/return/{ref}",
        {"purpose": "bidder_plan", "tier": tier, "bidder_id": bidder.id},
        currency=premium.CURRENCY, plan_code=premium.bidder_plan_code(tier))
    return RedirectResponse(data["authorization_url"], status_code=303)


@router.get("/marketplace/apply")
def marketplace_apply(request: Request, user=Depends(get_current_user),
                      db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    blocked = _flag_page(request, user, VERIFICATION_ENABLED)
    if blocked:
        return blocked
    if not MARKETPLACE_ENABLED and not _admin_ok(user):
        return templates.TemplateResponse(
            request, "marketplace_coming_soon.html", {"user": user})
    bidder = db.scalar(select(models.BidderCompany).where(
        models.BidderCompany.user_id == user.id))
    documents = []
    if bidder is not None:
        documents = db.scalars(select(models.BidderVerificationDocument).where(
            models.BidderVerificationDocument.bidder_company_id == bidder.id
        ).order_by(models.BidderVerificationDocument.id.desc())).all()
    return templates.TemplateResponse(
        request, "marketplace_apply.html",
        {"user": user, "bidder": bidder, "error": None, "documents": documents,
         "is_bidder": (user.user_type or "") == "bidder",
         "s3_configured": _s3_configured()})


@router.post("/marketplace/apply")
def marketplace_apply_submit(request: Request,
                             company_name: str = Form(...),
                             description: str = Form(""),
                             services_offered: str = Form(""),
                             website: str = Form(""),
                             contact_email: str = Form(""),
                             years_in_business: str = Form(""),
                             team_size: str = Form(""),
                             user=Depends(get_current_user),
                             db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    blocked = _flag_page(request, user, VERIFICATION_ENABLED)
    if blocked:
        return blocked
    if (user.user_type or "") != "bidder":
        return templates.TemplateResponse(
            request, "marketplace_apply.html",
            {"user": user, "bidder": None, "is_bidder": False,
             "error": "Apply from a partner account. Sign out and create a partner account first."},
            status_code=403)
    if len((company_name or "").strip()) < 2:
        return templates.TemplateResponse(
            request, "marketplace_apply.html",
            {"user": user, "bidder": None, "is_bidder": True,
             "error": "Enter your company name."}, status_code=400)
    bidder = db.scalar(select(models.BidderCompany).where(
        models.BidderCompany.user_id == user.id))
    if bidder is None:
        bidder = models.BidderCompany(
            user_id=user.id, company_name=company_name.strip()[:160],
            slug=bidder_slug(db, company_name),
            verification_status="submitted", verification_submitted_at=now_iso(),
            partner_tier="standard", subscription_status="inactive")
        db.add(bidder)
    else:
        bidder.company_name = company_name.strip()[:160]
        if not bidder.slug:
            bidder.slug = bidder_slug(db, company_name, bidder.id)
        if bidder.verification_status in (None, "", "draft", "rejected", "expired"):
            bidder.verification_status = "submitted"
            bidder.verification_submitted_at = now_iso()
    bidder.description = description.strip()[:4000] or bidder.description
    bidder.services_offered = services_offered.strip()[:4000] or bidder.services_offered
    bidder.website = website.strip()[:300] or bidder.website
    bidder.contact_email = contact_email.strip()[:200] or bidder.contact_email or user.email
    bidder.years_in_business = int(years_in_business) if years_in_business.isdigit() else bidder.years_in_business
    bidder.team_size = int(team_size) if team_size.isdigit() else bidder.team_size
    record_audit(db, action="marketplace.bidder_applied",
                 user_id=user.id, detail=f"bidder={bidder.id}; company={bidder.company_name[:120]}")
    db.commit()
    return RedirectResponse("/marketplace/apply?submitted=1", status_code=303)


@router.post("/marketplace/apply/documents")
async def marketplace_apply_document(
        request: Request, file: UploadFile = File(...),
        document_type: str = Form("business_registration"),
        user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    blocked = _flag_page(request, user, VERIFICATION_ENABLED)
    if blocked:
        return blocked
    bidder = db.scalar(select(models.BidderCompany).where(
        models.BidderCompany.user_id == user.id))
    if bidder is None:
        return RedirectResponse("/marketplace/apply?error=Save+your+application+first", status_code=303)
    from elipsis_api.services_s3 import is_s3_configured, upload_file_to_s3, validate_file
    if not is_s3_configured():
        return RedirectResponse(
            "/marketplace/apply?error=Document+upload+is+not+configured", status_code=303)
    is_valid, error = validate_file(file, "documents")
    if not is_valid:
        return RedirectResponse(f"/marketplace/apply?error={quote(error or 'Invalid file')}", status_code=303)
    try:
        data = await upload_file_to_s3(file, folder="bidder-verification")
    except Exception:  # noqa: BLE001
        return RedirectResponse(
            "/marketplace/apply?error=Could+not+upload+that+document", status_code=303)
    doc = models.BidderVerificationDocument(
        bidder_company_id=bidder.id,
        document_type=(document_type or "business_registration")[:80],
        filename=data["filename"], file_url=data["file_url"],
        s3_key=data.get("s3_key"))
    db.add(doc)
    if bidder.verification_status in ("approved",):
        bidder.verification_status = "submitted"
        bidder.verification_submitted_at = now_iso()
    record_audit(db, action="marketplace.bidder_document_uploaded", user_id=user.id,
                 detail=f"bidder={bidder.id}; document={doc.id}; type={doc.document_type}")
    db.commit()
    return RedirectResponse("/marketplace/apply?doc=uploaded", status_code=303)


@router.get("/marketplace/requests/new")
def marketplace_new(request: Request, user=Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not MARKETPLACE_ENABLED and not _admin_ok(user):
        return templates.TemplateResponse(
            request, "marketplace_coming_soon.html", {"user": user})
    orgs = services.owned_orgs(db, user)
    purchased = db.scalars(select(models.AssessmentPurchase).where(
        models.AssessmentPurchase.user_id == user.id,
        models.AssessmentPurchase.active.is_(True))).all()
    assessments = []
    for row in purchased:
        assessment = db.get(models.Assessment, row.assessment_id)
        if assessment:
            assessments.append(assessment)
    if services.is_pro_user(db, user):
        assessments = db.scalars(select(models.Assessment).where(
            models.Assessment.organization_id.in_([o.id for o in orgs])
        ).order_by(models.Assessment.id.desc()).limit(50)).all()
    return templates.TemplateResponse(
        request, "marketplace_new.html",
        {"user": user, "orgs": orgs, "assessments": assessments,
         "error": None, "form": {}})


@router.post("/marketplace/requests/new")
def marketplace_create(request: Request,
                       title: str = Form(...),
                       description: str = Form(""),
                       budget_range: str = Form(""),
                       deadline: str = Form(""),
                       location: str = Form(""),
                       organization_id: str = Form(""),
                       assessment_id: str = Form(""),
                       expectations: str = Form(""),
                       specifications: str = Form(""),
                       contact_preference: str = Form(""),
                       user=Depends(get_current_user),
                       db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not MARKETPLACE_ENABLED and not _admin_ok(user):
        return templates.TemplateResponse(
            request, "marketplace_coming_soon.html", {"user": user}, status_code=403)
    orgs = services.owned_orgs(db, user)
    assessments = db.scalars(select(models.Assessment).where(
        models.Assessment.organization_id.in_([o.id for o in orgs])
    ).order_by(models.Assessment.id.desc()).limit(50)).all() if orgs else []
    form = {"title": title, "description": description, "budget_range": budget_range,
            "deadline": deadline, "location": location, "expectations": expectations,
            "specifications": specifications, "contact_preference": contact_preference,
            "organization_id": organization_id, "assessment_id": assessment_id}

    def fail(message: str, code: int = 400):
        return templates.TemplateResponse(
            request, "marketplace_new.html",
            {"user": user, "orgs": orgs, "assessments": assessments,
             "error": message, "form": form}, status_code=code)

    if user.user_type == "bidder":
        return fail("Only client accounts can post requests.", 403)
    org_id = int(organization_id) if organization_id.strip().isdigit() else None
    if org_id is None and orgs:
        org_id = orgs[0].id
    if org_id is None or not services.can_access_org(db, user, org_id):
        return fail("Choose an organisation you own before posting.")
    if len((title or "").strip()) < 3:
        return fail("Give the request a short title.")

    selected_assessment = None
    if assessment_id.strip().isdigit():
        selected_assessment = db.get(models.Assessment, int(assessment_id))
    if selected_assessment is None or selected_assessment.organization_id != org_id:
        return fail("Choose a completed Full Assessment for this request.")
    if not assessment_is_unlocked(db, user.id, selected_assessment.id):
        return fail("Complete the Full Assessment before requesting implementation.", 402)

    summary = {
        "index": selected_assessment.readiness_index,
        "band": selected_assessment.maturity_band,
        "confidence": selected_assessment.confidence_index,
        "organization": next((o.name for o in orgs if o.id == org_id), None),
    }
    import json
    row = models.PhysicalAssessmentRequest(
        organization_id=org_id,
        user_id=user.id,
        assessment_id=selected_assessment.id,
        title=title.strip()[:160],
        description=description.strip() or None,
        message=description.strip() or None,
        expectations=expectations.strip() or None,
        specifications=specifications.strip() or None,
        contact_preference=contact_preference.strip() or None,
        budget_range=budget_range.strip() or None,
        deadline=deadline.strip() or None,
        location=location.strip() or None,
        summary_snapshot=json.dumps(summary, separators=(",", ":")),
        status=REQUEST_PENDING,
        payment_status="unlocked",
        switches_granted=3,
        switches_used=0,
        topup_count=0,
        verified_by_admin=False,
    )
    db.add(row)
    db.flush()
    record_audit(
        db, action="marketplace.request_submitted",
        organization_id=org_id, assessment_id=selected_assessment.id,
        user_id=user.id, detail=f"request={row.id}; title={row.title[:120]}")
    db.commit()
    from elipsis_api.services_email_events import send_user_event_sync
    send_user_event_sync(
        db, user.id, "request_submitted", request_title=row.title,
        request_id=row.id, url=f"/marketplace/{row.id}")
    return RedirectResponse("/marketplace?submitted=1", status_code=303)


@router.get("/marketplace/{request_id}")
def marketplace_detail(request_id: int, request: Request,
                       user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not MARKETPLACE_ENABLED and not _admin_ok(user):
        return templates.TemplateResponse(
            request, "marketplace_coming_soon.html", {"user": user})
    req = db.get(models.PhysicalAssessmentRequest, request_id)
    if req is None:
        return _not_found(request, user)
    is_owner = bool(user and services.can_access_org(db, user, req.organization_id))
    if req.status not in VISIBLE_REQUEST_STATUSES and not is_owner and not _admin_ok(user):
        return _not_found(request, user)
    org = db.get(models.Organization, req.organization_id)
    full = bool(user and can_view_full_request(db, user, req))
    contact = bool(user and can_view_contact_details(db, user, req))
    documents = list(db.scalars(
        select(models.RequestDocument).where(
            models.RequestDocument.request_id == request_id)
    ).all()) if full else []
    bid_count = db.scalar(
        select(func.count()).select_from(models.BidSubmission).where(
            models.BidSubmission.request_id == request_id,
            models.BidSubmission.status.in_((BID_APPROVED, BID_AWARDED)))
    ) or 0
    bids = []
    if full:
        record_audit(
            db, action="marketplace.request_viewed",
            organization_id=req.organization_id, assessment_id=req.assessment_id,
            user_id=user.id, detail=f"request={req.id}")
        db.commit()
        for bid in db.scalars(select(models.BidSubmission).where(
                models.BidSubmission.request_id == request_id).order_by(
                models.BidSubmission.created_at.asc())).all():
            if not can_view_bid(db, user, bid):
                continue
            bidder = db.get(models.BidderCompany, bid.bidder_company_id)
            bids.append({
                "row": bid,
                "bidder_name": bidder.company_name if bidder else "Implementation partner",
                "preferred": req.preferred_bid_id == bid.id,
            })
    from elipsis_api.services_marketplace import can_bid
    conv = request_conversation(db, req)
    if conv is not None:
        refresh_conversation(db, conv)
    candidates = []
    if is_owner and req.status == REQUEST_AWARDED:
        for bid, bidder in switch_candidates(db, req):
            candidates.append({"row": bid, "bidder_name": bidder.company_name})
    can_view_conv = bool(user and conv is not None and can_view_conversation(db, user, conv))
    return templates.TemplateResponse(
        request, "marketplace_detail.html",
        {"user": user, "request_row": req,
         "organization": org if full else None,
         "organization_name": org.name if (org and full) else "Verified client",
         "documents": documents, "bid_count": int(bid_count),
         "bids": bids,
         "can_view_full": full, "can_view_contact": contact,
         "can_bid": bool(user and can_bid(db, user, req)),
         "can_choose_partner": bool(
             user and is_request_owner(db, user, req) and req.status == REQUEST_APPROVED),
         "conversation": conv if can_view_conv else None,
         "switch_candidates": candidates,
         "switches_remaining": switches_remaining(req),
         "can_switch": bool(is_owner and req.status == REQUEST_AWARDED
                            and switches_remaining(req) > 0 and candidates),
         "is_owner": is_owner, "is_bidder": bool(user and user.user_type == "bidder"),
         "preferred_saved": request.query_params.get("preferred") == "1",
         "topup_saved": request.query_params.get("topup") == "1"})


@router.post("/marketplace/{request_id}/preferred")
def marketplace_choose_preferred(request_id: int, request: Request,
                                 bid_id: int = Form(...),
                                 user=Depends(get_current_user),
                                 db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    req = db.get(models.PhysicalAssessmentRequest, request_id)
    if req is None or not is_request_owner(db, user, req):
        return _not_found(request, user)
    if req.status != REQUEST_APPROVED:
        return RedirectResponse(f"/marketplace/{request_id}", status_code=303)
    bid = db.get(models.BidSubmission, bid_id)
    if bid is None or bid.request_id != request_id or bid.status != BID_APPROVED:
        return RedirectResponse(f"/marketplace/{request_id}", status_code=303)
    req.preferred_bid_id = bid.id
    req.preferred_at = now_iso()
    record_audit(
        db, action="marketplace.preferred_partner_chosen",
        organization_id=req.organization_id, assessment_id=req.assessment_id,
        user_id=user.id, detail=f"request={req.id}; bid={bid.id}")
    db.commit()
    return RedirectResponse(f"/marketplace/{request_id}?preferred=1", status_code=303)


@router.post("/marketplace/{request_id}/switch")
def marketplace_switch(request_id: int, request: Request,
                       bid_id: int = Form(...),
                       user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    req = db.get(models.PhysicalAssessmentRequest, request_id)
    if req is None or not is_request_owner(db, user, req):
        return _not_found(request, user)
    try:
        conv = switch_request(db, req, bid_id, user.id)
    except ValueError as exc:
        return RedirectResponse(
            f"/marketplace/{request_id}?switch_error={quote(str(exc))}", status_code=303)
    return RedirectResponse(
        f"/marketplace/conversations/{conv.id}", status_code=303)


@router.post("/marketplace/{request_id}/topup")
def marketplace_topup(request_id: int, request: Request,
                      user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not BILLING_ENABLED:
        return RedirectResponse(f"/marketplace/{request_id}?error=This+feature+is+not+available", status_code=303)
    if user is None:
        return login_redirect()
    req = db.get(models.PhysicalAssessmentRequest, request_id)
    if req is None or not is_request_owner(db, user, req):
        return _not_found(request, user)
    if req.status != REQUEST_AWARDED:
        return RedirectResponse(f"/marketplace/{request_id}", status_code=303)
    if switches_remaining(req) > 0:
        return RedirectResponse(f"/marketplace/{request_id}", status_code=303)
    from elipsis_api import premium
    ref = paystack.new_reference("SWT")
    amount = int(premium.SWITCH_TOPUP_USD * 100)
    db.add(models.Payment(
        user_id=user.id, reference=ref, purpose="switch_topup", amount_kes=0,
        currency=premium.CURRENCY, amount_minor=amount, billing_cycle="one_time",
        related_id=request_id, status="pending"))
    db.commit()
    base = str(request.base_url).rstrip("/")
    data = paystack.initialize(
        user.email, amount, ref, f"{base}/pay/return/{ref}",
        {"purpose": "switch_topup", "request_id": request_id,
         "price_usd": premium.SWITCH_TOPUP_USD}, currency=premium.CURRENCY)
    return RedirectResponse(data["authorization_url"], status_code=303)


@router.post("/marketplace/{request_id}/handoff")
def marketplace_handoff(request_id: int, request: Request,
                        user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not HANDOFF_ENABLED:
        return RedirectResponse(f"/marketplace/{request_id}?error=This+feature+is+not+available", status_code=303)
    if user is None:
        return login_redirect()
    req = db.get(models.PhysicalAssessmentRequest, request_id)
    if req is None or not is_request_owner(db, user, req):
        return _not_found(request, user)
    if req.status not in (REQUEST_AWARDED, "closed"):
        return RedirectResponse(f"/marketplace/{request_id}", status_code=303)
    from elipsis_api.services_handoff import create_handoff, partner_url
    token, _ = create_handoff(db, req, user.id)
    url = partner_url()
    sep = "&" if "?" in url else "?"
    return RedirectResponse(f"{url}{sep}handoff={quote(token)}", status_code=303)


@router.get("/marketplace/conversations/{conversation_id}")
def marketplace_conversation(conversation_id: int, request: Request,
                             user=Depends(get_current_user), db: Session = Depends(get_db)):
    blocked = _flag_page(request, user, MESSAGING_ENABLED)
    if blocked:
        return blocked
    if user is None:
        return login_redirect()
    conv = db.get(models.MarketplaceConversation, conversation_id)
    if conv is None or not can_view_conversation(db, user, conv):
        return _not_found(request, user)
    refresh_conversation(db, conv)
    req = db.get(models.PhysicalAssessmentRequest, conv.request_id)
    requester = db.get(models.User, conv.requester_id)
    bidder = db.get(models.User, conv.bidder_user_id)
    messages = db.scalars(select(models.ConversationMessage).where(
        models.ConversationMessage.conversation_id == conv.id
    ).order_by(models.ConversationMessage.id.asc())).all()
    participant = user.id in (conv.requester_id, conv.bidder_user_id)
    return templates.TemplateResponse(
        request, "marketplace_conversation.html",
        {"user": user, "conversation": conv, "request_row": req,
         "requester": requester, "bidder": bidder, "messages": messages,
         "participant": participant,
         "is_admin": services.is_admin(user) or getattr(user, "is_admin", False),
         "can_respond": bool(participant and conv.status == "open"),
         "error": request.query_params.get("error"),
         "ok": request.query_params.get("ok")})


@router.post("/marketplace/conversations/{conversation_id}/messages")
def marketplace_conversation_message(conversation_id: int, request: Request,
                                     body: str = Form(...),
                                     user=Depends(get_current_user),
                                     db: Session = Depends(get_db)):
    blocked = _flag_page(request, user, MESSAGING_ENABLED)
    if blocked:
        return blocked
    if user is None:
        return login_redirect()
    conv = db.get(models.MarketplaceConversation, conversation_id)
    if conv is None or not can_view_conversation(db, user, conv):
        return _not_found(request, user)
    refresh_conversation(db, conv)
    if conv.status != "open":
        return RedirectResponse(
            f"/marketplace/conversations/{conv.id}?error=This conversation is closed.",
            status_code=303)
    text = (body or "").strip()
    if not text:
        return RedirectResponse(
            f"/marketplace/conversations/{conv.id}?error=Write a message first.",
            status_code=303)
    text = text[:4000]
    is_admin = services.is_admin(user) or getattr(user, "is_admin", False)
    db.add(models.ConversationMessage(
        conversation_id=conv.id, sender_id=user.id, body=text,
        is_admin=is_admin, created_at=now_iso()))
    conv.last_message_at = now_iso()
    conv.closes_at = conversation_deadline()
    recipients = {conv.requester_id, conv.bidder_user_id}
    if conv.admin_involved:
        recipients.update(row.id for row in db.scalars(select(models.User).where(
            or_(models.User.is_admin.is_(True), models.User.role.in_(("admin", "super_admin"))))).all())
    recipients.discard(user.id)
    for uid in recipients:
        notify_user(db, uid, "conversation.message", "New marketplace message",
                    text[:180], f"/marketplace/conversations/{conv.id}")
    db.commit()
    from elipsis_api.services_email_events import send_user_event_sync
    req = db.get(models.PhysicalAssessmentRequest, conv.request_id)
    for uid in recipients:
        send_user_event_sync(
            db, uid, "conversation_message",
            request_title=req.title if req else "your implementation request",
            sender_name=user.name or user.email, message=text[:500],
            url=f"/marketplace/conversations/{conv.id}")
    return RedirectResponse(
        f"/marketplace/conversations/{conv.id}?ok=Message sent", status_code=303)


@router.post("/marketplace/conversations/{conversation_id}/involve-admin")
def marketplace_involve_admin(conversation_id: int, request: Request,
                              reason: str = Form(""),
                              user=Depends(get_current_user),
                              db: Session = Depends(get_db)):
    blocked = _flag_page(request, user, MESSAGING_ENABLED)
    if blocked:
        return blocked
    if user is None:
        return login_redirect()
    conv = db.get(models.MarketplaceConversation, conversation_id)
    if conv is None or not can_view_conversation(db, user, conv):
        return _not_found(request, user)
    if user.id not in (conv.requester_id, conv.bidder_user_id):
        return _not_found(request, user)
    conv.admin_involved = True
    admins = db.scalars(select(models.User).where(
        or_(models.User.is_admin.is_(True), models.User.role.in_(("admin", "super_admin"))))).all()
    for admin in admins:
        notify_user(db, admin.id, "conversation.admin_involved",
                    "Admin involvement requested",
                    (reason or "").strip()[:500] or "A participant asked Elipsis to join the conversation.",
                    f"/marketplace/conversations/{conv.id}")
    record_audit(
        db, action="marketplace.admin_involved",
        organization_id=(db.get(models.PhysicalAssessmentRequest, conv.request_id).organization_id
                         if db.get(models.PhysicalAssessmentRequest, conv.request_id) else None),
        user_id=user.id,
        detail=f"conversation={conv.id}; reason={(reason or '')[:500]}")
    db.commit()
    return RedirectResponse(
        f"/marketplace/conversations/{conv.id}?ok=An Elipsis admin has been invited.",
        status_code=303)


@router.post("/marketplace/conversations/{conversation_id}/outcome")
def marketplace_conversation_outcome(conversation_id: int, request: Request,
                                     outcome: str = Form(...),
                                     user=Depends(get_current_user),
                                     db: Session = Depends(get_db)):
    blocked = _flag_page(request, user, MESSAGING_ENABLED)
    if blocked:
        return blocked
    if user is None:
        return login_redirect()
    conv = db.get(models.MarketplaceConversation, conversation_id)
    if conv is None or not can_view_conversation(db, user, conv):
        return _not_found(request, user)
    if user.id not in (conv.requester_id, conv.bidder_user_id):
        return _not_found(request, user)
    if conv.status != "closed":
        return RedirectResponse(
            f"/marketplace/conversations/{conv.id}?error=The conversation is still open.",
            status_code=303)
    if outcome not in {"agreement", "no_agreement", "no_response", "closed_unconfirmed"}:
        return RedirectResponse(
            f"/marketplace/conversations/{conv.id}?error=Choose a valid outcome.",
            status_code=303)
    conv.outcome = outcome
    record_audit(
        db, action="marketplace.conversation_outcome",
        user_id=user.id, detail=f"conversation={conv.id}; outcome={outcome}")
    db.commit()
    return RedirectResponse(
        f"/marketplace/conversations/{conv.id}?ok=Outcome recorded", status_code=303)


@router.get("/marketplace/documents/{document_id}")
def marketplace_document(document_id: int, request: Request,
                         user=Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.get(models.RequestDocument, document_id)
    if doc is None or user is None:
        return _not_found(request, user)
    req = db.get(models.PhysicalAssessmentRequest, doc.request_id)
    if req is None or not can_view_full_request(db, user, req):
        return _not_found(request, user)
    record_audit(
        db, action="marketplace.document_viewed",
        organization_id=req.organization_id, assessment_id=req.assessment_id,
        user_id=user.id, detail=f"request={req.id}; document={doc.id}")
    db.commit()
    if doc.s3_key:
        from elipsis_api.services_s3 import generate_presigned_url
        url = generate_presigned_url(doc.s3_key, expiration=300)
        if url:
            return RedirectResponse(url, status_code=303)
    return _not_found(request, user)


@router.get("/admin")
def admin_pulse(request: Request, user=Depends(get_current_user),
                db: Session = Depends(get_db)):
    """Admin pulse overview — organisations, assessments, request pipeline."""
    if user is None:
        return login_redirect()
    if not _admin_ok(user):
        return _not_found(request, user)

    orgs_raw = db.scalars(
        select(models.Organization).order_by(models.Organization.id.desc()).limit(40)
    ).all()
    orgs = []
    for org in orgs_raw:
        a_count = db.scalar(
            select(func.count()).select_from(models.Assessment).where(
                models.Assessment.organization_id == org.id)
        ) or 0
        latest = db.scalar(
            select(models.Assessment)
            .where(models.Assessment.organization_id == org.id)
            .order_by(models.Assessment.id.desc())
            .limit(1)
        )
        orgs.append({
            "name": org.name,
            "industry": org.industry,
            "city": org.city,
            "country": org.country,
            "employee_count": org.employee_count,
            "assessment_count": int(a_count),
            "latest_at": getattr(latest, "started_at", None) or getattr(latest, "created_at", None) if latest else None,
        })

    assessments_raw = db.scalars(
        select(models.Assessment).order_by(models.Assessment.id.desc()).limit(25)
    ).all()
    assessments = []
    for a in assessments_raw:
        org = db.get(models.Organization, a.organization_id)
        dept = db.get(models.Department, a.department_id) if a.department_id else None
        score = None
        if hasattr(a, "readiness_index") and a.readiness_index is not None:
            try:
                score = round(float(a.readiness_index), 1)
            except (TypeError, ValueError):
                score = a.readiness_index
        assessments.append({
            "org_name": org.name if org else "—",
            "department": dept.name if dept else None,
            "status": a.status or "in_progress",
            "score": score,
            "created_at": getattr(a, "started_at", None) or getattr(a, "created_at", None),
        })

    reqs_raw = db.scalars(
        select(models.PhysicalAssessmentRequest).order_by(
            models.PhysicalAssessmentRequest.id.desc()).limit(20)
    ).all()
    requests = []
    for req in reqs_raw:
        org = db.get(models.Organization, req.organization_id)
        bid_count = db.scalar(
            select(func.count()).select_from(models.BidSubmission).where(
                models.BidSubmission.request_id == req.id)
        ) or 0
        requests.append({
            "title": req.title,
            "org_name": org.name if org else "—",
            "status": req.status,
            "bid_count": int(bid_count),
            "created_at": req.created_at,
        })

    all_orgs = db.scalar(select(func.count()).select_from(models.Organization)) or 0
    all_assess = db.scalar(select(func.count()).select_from(models.Assessment)) or 0
    all_req = db.scalars(select(models.PhysicalAssessmentRequest)).all()
    pending = sum(1 for r in all_req if r.status == REQUEST_PENDING)
    published = sum(1 for r in all_req if r.status == REQUEST_APPROVED)
    completed_a = db.scalar(
        select(func.count()).select_from(models.Assessment).where(
            models.Assessment.status == "completed")
    ) or 0
    bidders = 0
    try:
        bidders = db.scalar(select(func.count()).select_from(models.BidderCompany)) or 0
    except Exception:
        bidders = db.scalar(
            select(func.count()).select_from(models.User).where(
                models.User.user_type == "bidder")
        ) or 0

    stats = {
        "orgs": int(all_orgs),
        "assessments": int(all_assess),
        "pending_requests": pending,
        "published_requests": published,
        "bidders": int(bidders),
        "completed_assessments": int(completed_a),
    }
    max_v = max(stats["orgs"], stats["assessments"], stats["published_requests"], stats["pending_requests"], 1)
    bar_orgs = min(100, int(100 * stats["orgs"] / max_v))
    bar_assess = min(100, int(100 * stats["assessments"] / max_v))
    bar_pub = min(100, int(100 * stats["published_requests"] / max_v))
    bar_pend = min(100, int(100 * stats["pending_requests"] / max_v))

    return templates.TemplateResponse(
        request, "admin.html",
        {
            "user": user,
            "stats": stats,
            "orgs": orgs,
            "assessments": assessments,
            "requests": requests,
            "bar_orgs": bar_orgs,
            "bar_assess": bar_assess,
            "bar_pub": bar_pub,
            "bar_pend": bar_pend,
        },
    )


@router.get("/admin/requests")
def admin_requests_page(request: Request, user=Depends(get_current_user),
                        db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not _admin_ok(user):
        return _not_found(request, user)
    status_filter = (request.query_params.get("status") or "").strip()
    query = select(models.PhysicalAssessmentRequest).order_by(
        models.PhysicalAssessmentRequest.id.desc())
    if status_filter:
        query = query.where(models.PhysicalAssessmentRequest.status == status_filter)
    rows = db.scalars(query).all()
    requests = []
    for req in rows:
        org = db.get(models.Organization, req.organization_id)
        bid_count = db.scalar(
            select(func.count()).select_from(models.BidSubmission).where(
                models.BidSubmission.request_id == req.id)
        ) or 0
        requests.append({
            "id": req.id,
            "title": req.title,
            "message": req.message,
            "status": req.status,
            "created_at": req.created_at,
            "bid_count": int(bid_count),
            "organization": org,
        })
    all_rows = db.scalars(select(models.PhysicalAssessmentRequest)).all()
    stats = {
        "total": len(all_rows),
        "pending": sum(1 for r in all_rows if r.status == REQUEST_PENDING),
        "published": sum(1 for r in all_rows if r.status == REQUEST_APPROVED),
        "awarded": sum(1 for r in all_rows if r.status == REQUEST_AWARDED),
        "rejected": sum(1 for r in all_rows if r.status in ("rejected", "closed")),
    }
    active = [r for r in requests if r["status"] in (REQUEST_PENDING, REQUEST_APPROVED, REQUEST_AWARDED)]
    history = [r for r in requests if r["status"] not in (REQUEST_PENDING, REQUEST_APPROVED, REQUEST_AWARDED)]
    return templates.TemplateResponse(
        request, "admin_requests.html",
        {"user": user, "requests": requests, "active": active, "history": history, "stats": stats})


@router.post("/admin/requests/{request_id}/publish")
def admin_publish_request(request_id: int, request: Request,
                          user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not _admin_ok(user):
        return _not_found(request, user)
    req = db.get(models.PhysicalAssessmentRequest, request_id)
    if req is None:
        return _not_found(request, user)
    if req.status != REQUEST_PENDING:
        return RedirectResponse("/admin/requests", status_code=303)
    req.status = REQUEST_APPROVED
    req.verified_by_admin = True
    req.verified_at = now_iso()
    req.published_at = req.published_at or now_iso()
    req.reviewed_by = user.id
    req.reviewed_at = now_iso()
    notify_user(db, req.user_id, "request.approved", "Your request is approved",
                "Verified implementation partners can now review it.",
                f"/marketplace/{req.id}")
    record_audit(
        db, action="marketplace.request_approved",
        organization_id=req.organization_id, assessment_id=req.assessment_id,
        user_id=user.id, detail=f"request={req.id}")
    db.commit()
    from elipsis_api.services_email_events import send_user_event_sync
    send_user_event_sync(
        db, req.user_id, "request_approved", request_title=req.title,
        url=f"/marketplace/{req.id}")
    return RedirectResponse("/admin/requests", status_code=303)


@router.post("/admin/requests/{request_id}/reject")
def admin_reject_request(request_id: int, request: Request,
                         reason: str = Form(""),
                         user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not _admin_ok(user):
        return _not_found(request, user)
    req = db.get(models.PhysicalAssessmentRequest, request_id)
    if req is None:
        return _not_found(request, user)
    if req.status != REQUEST_PENDING:
        return RedirectResponse("/admin/requests", status_code=303)
    req.status = REQUEST_REJECTED
    note = (reason or "").strip()[:500]
    req.rejection_reason = note or None
    req.reviewed_by = user.id
    req.reviewed_at = now_iso()
    if note:
        req.admin_notes = f"Rejected: {note}"
    notify_user(db, req.user_id, "request.rejected", "Your request needs changes",
                note or "An admin asked for changes before publishing.",
                f"/marketplace/{req.id}")
    record_audit(
        db, action="marketplace.request_rejected",
        organization_id=req.organization_id, assessment_id=req.assessment_id,
        user_id=user.id, detail=f"request={req.id}; reason={note}")
    db.commit()
    from elipsis_api.services_email_events import send_user_event_sync
    send_user_event_sync(
        db, req.user_id, "request_rejected", request_title=req.title,
        reason=note or "Update the request and resubmit.", url=f"/marketplace/{req.id}")
    return RedirectResponse("/admin/requests", status_code=303)


def _admin_redirect(path: str, *, error: str | None = None, ok: str | None = None):
    suffix = ""
    if error:
        suffix = f"?error={quote(error[:300])}"
    elif ok:
        suffix = f"?ok={quote(ok[:300])}"
    return RedirectResponse(f"{path}{suffix}", status_code=303)


@router.get("/admin/requests/{request_id}")
def admin_request_detail(request_id: int, request: Request,
                         user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not _admin_ok(user):
        return _not_found(request, user)
    req = db.get(models.PhysicalAssessmentRequest, request_id)
    if req is None:
        return _not_found(request, user)
    org = db.get(models.Organization, req.organization_id)
    client = db.get(models.User, req.user_id) if req.user_id else None
    if client is None and org and org.user_id:
        client = db.get(models.User, org.user_id)
    documents = db.scalars(select(models.RequestDocument).where(
        models.RequestDocument.request_id == request_id)).all()
    bids = db.scalars(select(models.BidSubmission).where(
        models.BidSubmission.request_id == request_id).order_by(
        models.BidSubmission.created_at.asc())).all()
    bid_rows = []
    for bid in bids:
        bidder = db.get(models.BidderCompany, bid.bidder_company_id)
        bid_rows.append({
            "row": bid,
            "bidder": bidder,
            "bidder_name": bidder.company_name if bidder else "Unknown bidder",
            "verification": bidder_verification_label(
                bidder.verification_status if bidder else None),
            "verified": bool(bidder and bidder.verification_status == "approved"),
            "subscribed": bool(bidder and bidder.subscription_status == "active"),
        })
    conversations = db.scalars(select(models.MarketplaceConversation).where(
        models.MarketplaceConversation.request_id == request_id
    ).order_by(models.MarketplaceConversation.id.desc())).all()
    handoffs = db.scalars(select(models.MarketplaceHandoff).where(
        models.MarketplaceHandoff.request_id == request_id
    ).order_by(models.MarketplaceHandoff.id.desc())).all()
    return templates.TemplateResponse(
        request, "admin_request_detail.html",
        {"user": user, "request_row": req, "organization": org, "client": client,
         "documents": documents, "bids": bid_rows,
         "conversations": conversations, "handoffs": handoffs,
         "error": request.query_params.get("error"),
         "ok": request.query_params.get("ok")})


@router.post("/admin/requests/{request_id}/bids/{bid_id}/approve")
def admin_approve_bid(request_id: int, bid_id: int, request: Request,
                      user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not _admin_ok(user):
        return _not_found(request, user)
    from elipsis_api.routers.admin import approve_bid
    try:
        approve_bid(bid_id, None, db, user)
    except HTTPException as exc:
        return _admin_redirect(f"/admin/requests/{request_id}", error=str(exc.detail))
    return _admin_redirect(f"/admin/requests/{request_id}", ok="Bid approved")


@router.post("/admin/requests/{request_id}/bids/{bid_id}/reject")
def admin_reject_bid(request_id: int, bid_id: int, request: Request,
                     reason: str = Form(""), user=Depends(get_current_user),
                     db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not _admin_ok(user):
        return _not_found(request, user)
    from elipsis_api.routers.admin import reject_bid
    try:
        reject_bid(bid_id, reason or "Not selected for this request", db, user)
    except HTTPException as exc:
        return _admin_redirect(f"/admin/requests/{request_id}", error=str(exc.detail))
    return _admin_redirect(f"/admin/requests/{request_id}", ok="Bid rejected")


@router.post("/admin/requests/{request_id}/award/{bid_id}")
def admin_award_request(request_id: int, bid_id: int, request: Request,
                        user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not _admin_ok(user):
        return _not_found(request, user)
    from elipsis_api.routers.admin import award_request
    try:
        award_request(request_id, bid_id, db, user)
    except HTTPException as exc:
        return _admin_redirect(f"/admin/requests/{request_id}", error=str(exc.detail))
    return _admin_redirect(f"/admin/requests/{request_id}", ok="Request awarded")


@router.get("/admin/conversations")
def admin_conversations_page(request: Request, user=Depends(get_current_user),
                             db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not _admin_ok(user):
        return _not_found(request, user)
    rows = db.scalars(select(models.MarketplaceConversation).order_by(
        models.MarketplaceConversation.id.desc()).limit(100)).all()
    conversations = []
    for row in rows:
        req = db.get(models.PhysicalAssessmentRequest, row.request_id)
        conversations.append({"row": row, "request": req})
    return templates.TemplateResponse(
        request, "admin_conversations.html",
        {"user": user, "conversations": conversations})


@router.get("/admin/handoffs")
def admin_handoffs_page(request: Request, user=Depends(get_current_user),
                        db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not _admin_ok(user):
        return _not_found(request, user)
    rows = db.scalars(select(models.MarketplaceHandoff).order_by(
        models.MarketplaceHandoff.id.desc()).limit(100)).all()
    handoffs = []
    for row in rows:
        handoffs.append({
            "row": row,
            "request": db.get(models.PhysicalAssessmentRequest, row.request_id),
            "client": db.get(models.User, row.user_id),
        })
    return templates.TemplateResponse(
        request, "admin_handoffs.html",
        {"user": user, "handoffs": handoffs})


@router.get("/admin/bidders")
def admin_bidders_page(request: Request, user=Depends(get_current_user),
                       db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not _admin_ok(user):
        return _not_found(request, user)
    rows = db.scalars(select(models.BidderCompany).order_by(
        models.BidderCompany.created_at.desc())).all()
    bidders = []
    for bidder in rows:
        owner = db.get(models.User, bidder.user_id)
        documents = db.scalars(select(models.BidderVerificationDocument).where(
            models.BidderVerificationDocument.bidder_company_id == bidder.id
        ).order_by(models.BidderVerificationDocument.id.desc())).all()
        bidders.append({
            "row": bidder,
            "owner": owner,
            "documents": documents,
            "verification": bidder_verification_label(bidder.verification_status),
        })
    return templates.TemplateResponse(
        request, "admin_bidders.html",
        {"user": user, "bidders": bidders,
         "error": request.query_params.get("error"),
         "ok": request.query_params.get("ok")})


@router.post("/admin/bidders/{bidder_id}/verify")
def admin_verify_bidder(bidder_id: int, request: Request,
                        decision: str = Form("approved"), notes: str = Form(""),
                        user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not _admin_ok(user):
        return _not_found(request, user)
    from elipsis_api.routers.admin import verify_bidder
    try:
        verify_bidder(bidder_id, decision, notes or None, db, user)
    except HTTPException as exc:
        return _admin_redirect("/admin/bidders", error=str(exc.detail))
    return _admin_redirect("/admin/bidders", ok="Bidder verification updated")
