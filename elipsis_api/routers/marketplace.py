"""Marketplace API routes for browsing and bidding on implementation requests."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from elipsis_api import models, schemas, services
from elipsis_api.config import HANDOFF_ENABLED, MARKETPLACE_ENABLED
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user
from elipsis_api.query_utils import count_rows, isoformat
from elipsis_api.services_marketplace import (
    BID_APPROVED,
    BID_AWARDED,
    BID_PENDING,
    BID_REJECTED,
    BID_WITHDRAWN,
    REQUEST_APPROVED,
    REQUEST_PENDING,
    VISIBLE_REQUEST_STATUSES,
    assessment_is_unlocked,
    can_bid,
    can_view_contact_details,
    can_view_full_request,
    get_bidder_company,
    is_active_bidder,
    is_request_owner,
    now_iso,
    visible_bid_status,
)

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


def _require_marketplace():
    if not MARKETPLACE_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Marketplace is coming soon. Join the partner list at /partners.")


def _require_user(user):
    if user is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    return user


def _org_teaser(org: models.Organization | None) -> dict | None:
    if org is None:
        return None
    return {
        "industry": org.industry,
        "company_size": org.company_size or "small",
        "city": org.city,
        "country": org.country,
    }


def _org_full(org: models.Organization | None, include_contact: bool) -> dict | None:
    if org is None:
        return None
    return {
        "id": org.id,
        "name": org.name,
        "industry": org.industry,
        "company_size": org.company_size or "small",
        "city": org.city,
        "country": org.country,
        "contact_name": org.contact_name if include_contact else None,
        "contact_email": org.contact_email if include_contact else None,
        "contact_phone": org.contact_phone if include_contact else None,
    }


def _summary_payload(db: Session, assessment: models.Assessment | None) -> str | None:
    if assessment is None:
        return None
    org = db.get(models.Organization, assessment.organization_id)
    pains = db.scalars(
        select(models.PainPoint)
        .where(models.PainPoint.assessment_id == assessment.id)
        .order_by(models.PainPoint.impact_score.desc())
        .limit(3)
    ).all()
    payload = {
        "index": assessment.readiness_index,
        "band": assessment.maturity_band,
        "confidence": assessment.confidence_index,
        "industry": org.industry if org else None,
        "country": org.country if org else None,
        "company_size": org.company_size if org else None,
        "constraints": [
            {"title": pain.title, "severity": pain.severity,
             "impact": pain.impact_score, "detail": pain.detail}
            for pain in pains
        ],
    }
    return json.dumps(payload, separators=(",", ":"))


@router.get("/requests")
def list_marketplace_requests(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(get_current_user),
):
    """List approved marketplace requests as public teaser cards."""
    _require_marketplace()
    query = select(models.PhysicalAssessmentRequest).where(
        models.PhysicalAssessmentRequest.status.in_(VISIBLE_REQUEST_STATUSES)
    )
    if status_filter:
        if status_filter not in VISIBLE_REQUEST_STATUSES:
            raise HTTPException(status_code=400, detail="invalid status filter")
        query = query.where(models.PhysicalAssessmentRequest.status == status_filter)
    rows = db.scalars(
        query.order_by(models.PhysicalAssessmentRequest.id.desc())
    ).all()

    viewer_is_bidder = bool(current_user and is_active_bidder(db, current_user.id))
    results = []
    for req in rows:
        org = db.get(models.Organization, req.organization_id)
        bid_count = count_rows(
            db, models.BidSubmission,
            models.BidSubmission.request_id == req.id,
            models.BidSubmission.status.in_((BID_APPROVED, BID_AWARDED)),
        )
        results.append({
            "id": req.id,
            "title": req.title,
            "description": req.description,
            "budget_range": req.budget_range,
            "deadline": isoformat(req.deadline),
            "location": req.location,
            "status": req.status,
            "premium": True,
            "created_at": isoformat(req.created_at),
            "organization": _org_full(org, False) if viewer_is_bidder else _org_teaser(org),
            "document_count": count_rows(
                db, models.RequestDocument,
                models.RequestDocument.request_id == req.id),
            "bid_count": bid_count,
            "can_view_details": bool(
                current_user and can_view_full_request(db, current_user, req)),
        })
    return {"requests": results, "count": len(results)}


@router.post("/requests", status_code=status.HTTP_201_CREATED)
def create_marketplace_request(
    payload: schemas.MarketplaceRequestIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Submit an implementation request for admin review."""
    _require_marketplace()
    _require_user(current_user)
    if (current_user.user_type or "") == "bidder":
        raise HTTPException(status_code=403, detail="Only client accounts can post requests")

    org_id = payload.organization_id
    if org_id is None:
        orgs = services.owned_org_ids(db, current_user)
        org_id = orgs[0] if orgs else None
    if org_id is None or not services.can_access_org(db, current_user, org_id):
        raise HTTPException(status_code=404, detail="organization not found")

    assessment = None
    if payload.assessment_id is not None:
        assessment = db.get(models.Assessment, payload.assessment_id)
        if assessment is None or assessment.organization_id != org_id:
            raise HTTPException(status_code=404, detail="assessment not found")
        if not assessment_is_unlocked(db, current_user.id, assessment.id):
            raise HTTPException(status_code=402, detail="Full Assessment required")
    elif not services.is_pro_user(db, current_user):
        raise HTTPException(
            status_code=402,
            detail="Complete a Full Assessment before requesting implementation",
        )

    row = models.PhysicalAssessmentRequest(
        organization_id=org_id,
        user_id=current_user.id,
        assessment_id=assessment.id if assessment else None,
        title=payload.title.strip(),
        description=(payload.description or "").strip() or None,
        message=(payload.description or "").strip() or None,
        expectations=(payload.expectations or "").strip() or None,
        specifications=(payload.specifications or "").strip() or None,
        contact_preference=(payload.contact_preference or "").strip() or None,
        budget_range=(payload.budget_range or "").strip() or None,
        deadline=(payload.deadline or "").strip() or None,
        location=(payload.location or "").strip() or None,
        summary_snapshot=_summary_payload(db, assessment),
        status=REQUEST_PENDING,
        payment_status="unlocked" if assessment else "subscription",
        switches_granted=3,
        switches_used=0,
        topup_count=0,
        verified_by_admin=False,
    )
    db.add(row)
    db.flush()
    from elipsis_api.services_ops import record_audit
    record_audit(
        db,
        action="marketplace.request_submitted",
        organization_id=org_id,
        assessment_id=assessment.id if assessment else None,
        user_id=current_user.id,
        detail=f"request={row.id}; title={row.title[:120]}",
    )
    db.commit()
    db.refresh(row)
    return {"id": row.id, "status": row.status, "message": "Request submitted for review"}


@router.get("/requests/{request_id}")
def get_marketplace_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(get_current_user),
):
    """Get a full approved request when the viewer is authorized."""
    _require_marketplace()
    req = db.get(models.PhysicalAssessmentRequest, request_id)
    if req is None or current_user is None:
        raise HTTPException(status_code=404, detail="Request not found")
    if not can_view_full_request(db, current_user, req):
        raise HTTPException(status_code=404, detail="Request not found")

    org = db.get(models.Organization, req.organization_id)
    include_contact = can_view_contact_details(db, current_user, req)
    documents = db.scalars(
        select(models.RequestDocument).where(
            models.RequestDocument.request_id == request_id
        )
    ).all()

    bid_query = select(models.BidSubmission).where(
        models.BidSubmission.request_id == request_id
    )
    if not (services.is_admin(current_user) or getattr(current_user, "is_admin", False)):
        bidder = get_bidder_company(db, current_user.id)
        if bidder and can_bid(db, current_user, req):
            bids = db.scalars(bid_query.where(
                models.BidSubmission.bidder_company_id == bidder.id)).all()
        else:
            bids = db.scalars(bid_query.where(
                models.BidSubmission.status.in_((BID_APPROVED, BID_AWARDED)))).all()
    else:
        bids = db.scalars(bid_query).all()

    bid_list = []
    for bid in bids:
        if not visible_bid_status(bid) and not (
                services.is_admin(current_user) or getattr(current_user, "is_admin", False)):
            bidder = get_bidder_company(db, current_user.id)
            if bidder is None or bid.bidder_company_id != bidder.id:
                continue
        bidder = db.get(models.BidderCompany, bid.bidder_company_id)
        bid_list.append({
            "id": bid.id,
            "bidder_name": bidder.company_name if bidder else "Unknown",
            "proposal": bid.proposal or bid.message,
            "estimated_cost": bid.estimated_cost or bid.proposed_cost,
            "timeline": bid.timeline or bid.proposed_timeline,
            "status": bid.status,
            "submitted_at": isoformat(bid.created_at),
        })

    return {
        "id": req.id,
        "title": req.title,
        "description": req.description,
        "expectations": req.expectations,
        "specifications": req.specifications,
        "summary_snapshot": json.loads(req.summary_snapshot) if req.summary_snapshot else None,
        "budget_range": req.budget_range,
        "deadline": isoformat(req.deadline),
        "location": req.location,
        "status": req.status,
        "premium": True,
        "created_at": isoformat(req.created_at),
        "switches_used": req.switches_used or 0,
        "switches_granted": req.switches_granted or 3,
        "awarded_bid_id": req.awarded_bid_id,
        "preferred_bid_id": req.preferred_bid_id,
        "preferred_at": isoformat(req.preferred_at),
        "can_choose_partner": bool(
            req.status == REQUEST_APPROVED and is_request_owner(db, current_user, req)),
        "organization": _org_full(org, include_contact),
        "documents": [
            {
                "id": doc.id,
                "filename": doc.filename or doc.file_name,
                "file_type": doc.file_type,
                "uploaded_at": isoformat(doc.uploaded_at),
                "download_url": f"/marketplace/documents/{doc.id}",
            }
            for doc in documents
        ],
        "bids": bid_list,
        "can_bid": can_bid(db, current_user, req),
    }


@router.post("/requests/{request_id}/bid", status_code=status.HTTP_201_CREATED)
def submit_bid(
    request_id: int,
    payload: schemas.BidSubmissionIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Submit a bid. Requires an approved, subscribed bidder."""
    _require_marketplace()
    _require_user(current_user)
    if (current_user.user_type or "") != "bidder":
        raise HTTPException(status_code=403, detail="Only bidder accounts can submit bids")
    if not is_active_bidder(db, current_user.id):
        raise HTTPException(
            status_code=402,
            detail="Verified bidder status and an active subscription are required",
        )

    bidder = get_bidder_company(db, current_user.id)
    if not bidder:
        raise HTTPException(status_code=400, detail="Please create your bidder profile first")

    req = db.get(models.PhysicalAssessmentRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if not can_bid(db, current_user, req):
        raise HTTPException(status_code=400, detail="Request is not available for bidding")

    if payload.roadmap_document_id is not None:
        doc = db.get(models.RequestDocument, payload.roadmap_document_id)
        if doc is None or doc.request_id != request_id:
            raise HTTPException(status_code=400, detail="Invalid roadmap document")

    existing = db.scalar(select(models.BidSubmission).where(
        models.BidSubmission.request_id == request_id,
        models.BidSubmission.bidder_company_id == bidder.id,
    ))
    if existing and (existing.status or "") not in (BID_REJECTED, BID_WITHDRAWN):
        raise HTTPException(status_code=400, detail="You have already submitted a bid")
    if existing:
        existing.proposal = payload.proposal
        existing.estimated_cost = payload.estimated_cost
        existing.timeline = payload.timeline
        existing.roadmap_document_id = payload.roadmap_document_id
        existing.status = BID_PENDING
        existing.admin_notes = None
        existing.admin_reviewed_at = None
        existing.admin_reviewed_by = None
        bid = existing
    else:
        bid = models.BidSubmission(
            request_id=request_id,
            bidder_company_id=bidder.id,
            proposal=payload.proposal,
            estimated_cost=payload.estimated_cost,
            timeline=payload.timeline,
            roadmap_document_id=payload.roadmap_document_id,
            status=BID_PENDING,
        )
        db.add(bid)
    db.flush()
    from elipsis_api.services_ops import record_audit
    record_audit(
        db,
        action="marketplace.bid_submitted",
        organization_id=req.organization_id,
        assessment_id=req.assessment_id,
        user_id=current_user.id,
        detail=f"request={request_id}; bid={bid.id}",
    )
    db.commit()
    db.refresh(bid)
    return {
        "id": bid.id,
        "request_id": request_id,
        "status": bid.status,
        "submitted_at": isoformat(bid.created_at),
        "message": "Bid submitted for review",
    }


@router.post("/requests/{request_id}/preferred")
def choose_preferred_bid(
    request_id: int,
    payload: schemas.PreferredBidIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Record the client's preferred approved partner for admin to award."""
    _require_marketplace()
    _require_user(current_user)
    req = db.get(models.PhysicalAssessmentRequest, request_id)
    if req is None or not is_request_owner(db, current_user, req):
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != REQUEST_APPROVED:
        raise HTTPException(status_code=400, detail="This request is not open for partner selection")
    bid = db.get(models.BidSubmission, payload.bid_id)
    if bid is None or bid.request_id != request_id or bid.status != BID_APPROVED:
        raise HTTPException(status_code=400, detail="Choose an approved bid")
    req.preferred_bid_id = bid.id
    req.preferred_at = now_iso()
    from elipsis_api.services_ops import record_audit
    record_audit(
        db,
        action="marketplace.preferred_partner_chosen",
        organization_id=req.organization_id,
        assessment_id=req.assessment_id,
        user_id=current_user.id,
        detail=f"request={req.id}; bid={bid.id}",
    )
    db.commit()
    return {
        "request_id": req.id,
        "preferred_bid_id": req.preferred_bid_id,
        "preferred_at": isoformat(req.preferred_at),
        "message": "Preference recorded. The Elipsis team will confirm the award.",
    }


@router.get("/handoffs/{token}")
def fetch_handoff(token: str, request: Request, db: Session = Depends(get_db)):
    """Server-to-server handoff fetch for Great Turbinez. Single use."""
    if not HANDOFF_ENABLED:
        raise HTTPException(status_code=404, detail="Handoffs are not enabled")
    from elipsis_api.services_handoff import consume_handoff, fetch_secret
    expected = fetch_secret()
    supplied = (request.headers.get("x-elipsis-handoff-secret") or "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Handoff fetch is not configured")
    if not supplied or supplied != expected:
        raise HTTPException(status_code=401, detail="Invalid handoff credential")
    payload = consume_handoff(db, token)
    if payload is None:
        raise HTTPException(status_code=410, detail="Handoff is invalid, expired, or already used")
    return payload
