"""Admin API routes for marketplace review, verification, and award."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from elipsis_api import models, services
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user
from elipsis_api.query_utils import count_rows, isoformat
from elipsis_api.services_marketplace import (
    BID_APPROVED,
    BID_AWARDED,
    BID_NOT_SELECTED,
    BID_PENDING,
    BID_REJECTED,
    REQUEST_APPROVED,
    REQUEST_AWARDED,
    REQUEST_CLOSED,
    REQUEST_PENDING,
    REQUEST_REJECTED,
    VERIFY_APPROVED,
    VERIFY_MORE_INFO,
    VERIFY_REJECTED,
    conversation_deadline,
    now_iso,
)
from elipsis_api.services_ops import record_audit

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(current_user: models.User = Depends(get_current_user)):
    """Guard admin routes with a 404 to avoid confirming the admin surface."""
    if current_user is None or not (
            current_user.is_admin or services.is_admin(current_user)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return current_user


def _notify(db: Session, user_id: int | None, event: str, title: str,
            body: str | None = None, url: str | None = None):
    if not user_id:
        return
    db.add(models.MarketplaceNotification(
        user_id=user_id, event=event, title=title, body=body, url=url,
        created_at=now_iso()))


def _request_payload(db: Session, req: models.PhysicalAssessmentRequest) -> dict:
    org = db.get(models.Organization, req.organization_id)
    client = db.get(models.User, req.user_id) if req.user_id else None
    if client is None and org and org.user_id:
        client = db.get(models.User, org.user_id)
    bids = db.scalars(select(models.BidSubmission).where(
        models.BidSubmission.request_id == req.id)).all()
    return {
        "id": req.id,
        "title": req.title,
        "description": req.description,
        "expectations": req.expectations,
        "specifications": req.specifications,
        "budget_range": req.budget_range,
        "deadline": isoformat(req.deadline),
        "location": req.location,
        "status": req.status,
        "verified_by_admin": req.verified_by_admin,
        "preferred_bid_id": req.preferred_bid_id,
        "preferred_at": isoformat(req.preferred_at),
        "awarded_bid_id": req.awarded_bid_id,
        "switches_used": req.switches_used or 0,
        "switches_granted": req.switches_granted or 3,
        "admin_notes": req.admin_notes,
        "created_at": isoformat(req.created_at),
        "organization": {
            "id": org.id,
            "name": org.name,
            "industry": org.industry,
            "company_size": org.company_size or "small",
            "city": org.city,
            "country": org.country,
            "contact_email": org.contact_email,
            "contact_phone": org.contact_phone,
        } if org else None,
        "client": {
            "id": client.id,
            "name": client.name,
            "email": client.email,
        } if client else None,
        "document_count": count_rows(
            db, models.RequestDocument,
            models.RequestDocument.request_id == req.id),
        "bid_count": len(bids),
    }


@router.get("/requests")
def list_all_requests(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    query = select(models.PhysicalAssessmentRequest)
    if status_filter:
        query = query.where(models.PhysicalAssessmentRequest.status == status_filter)
    requests = db.scalars(
        query.order_by(models.PhysicalAssessmentRequest.created_at.desc())).all()
    results = [_request_payload(db, req) for req in requests]
    return {"requests": results, "count": len(results)}


@router.get("/requests/{request_id}")
def get_request_details(
    request_id: int,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    req = db.get(models.PhysicalAssessmentRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    payload = _request_payload(db, req)
    documents = db.scalars(select(models.RequestDocument).where(
        models.RequestDocument.request_id == request_id)).all()
    bids = db.scalars(select(models.BidSubmission).where(
        models.BidSubmission.request_id == request_id)).all()
    payload["documents"] = [
        {
            "id": doc.id,
            "filename": doc.filename or doc.file_name,
            "file_type": doc.file_type,
            "uploaded_at": isoformat(doc.uploaded_at),
            "download_url": f"/marketplace/documents/{doc.id}",
        }
        for doc in documents
    ]
    payload["bids"] = []
    for bid in bids:
        bidder = db.get(models.BidderCompany, bid.bidder_company_id)
        payload["bids"].append({
            "id": bid.id,
            "bidder_id": bid.bidder_company_id,
            "bidder_name": bidder.company_name if bidder else "Unknown",
            "bidder_contact": bidder.contact_email if bidder else None,
            "bidder_verified": bidder.verification_status if bidder else None,
            "proposal": bid.proposal,
            "estimated_cost": bid.estimated_cost,
            "timeline": bid.timeline,
            "roadmap_document_id": bid.roadmap_document_id,
            "status": bid.status,
            "preferred": req.preferred_bid_id == bid.id,
            "submitted_at": isoformat(bid.created_at),
        })
    record_audit(
        db, action="marketplace.admin_request_viewed",
        organization_id=req.organization_id, assessment_id=req.assessment_id,
        user_id=admin_user.id, detail=f"request={req.id}")
    db.commit()
    return payload


@router.post("/requests/{request_id}/approve")
def approve_request(
    request_id: int,
    notes: str | None = None,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    req = db.get(models.PhysicalAssessmentRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != REQUEST_PENDING:
        raise HTTPException(status_code=400, detail=f"Cannot approve request with status: {req.status}")
    req.status = REQUEST_APPROVED
    req.verified_by_admin = True
    req.verified_at = now_iso()
    req.published_at = req.published_at or now_iso()
    req.reviewed_by = admin_user.id
    req.reviewed_at = now_iso()
    req.rejection_reason = None
    if notes:
        req.admin_notes = notes[:2000]
    record_audit(
        db, action="marketplace.request_approved",
        organization_id=req.organization_id, assessment_id=req.assessment_id,
        user_id=admin_user.id, detail=f"request={req.id}")
    _notify(db, req.user_id, "request.approved", "Your request is approved",
            "Verified implementation partners can now review it.",
            f"/marketplace/{req.id}")
    db.commit()
    db.refresh(req)
    return {"id": req.id, "status": req.status, "message": "Request approved"}


@router.post("/requests/{request_id}/reject")
def reject_request(
    request_id: int,
    reason: str,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    req = db.get(models.PhysicalAssessmentRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status not in (REQUEST_PENDING, REQUEST_APPROVED):
        raise HTTPException(status_code=400, detail=f"Cannot reject request with status: {req.status}")
    req.status = REQUEST_REJECTED
    req.verified_by_admin = False
    req.reviewed_by = admin_user.id
    req.reviewed_at = now_iso()
    req.rejection_reason = reason.strip()[:2000]
    req.admin_notes = f"Rejected: {req.rejection_reason}"
    record_audit(
        db, action="marketplace.request_rejected",
        organization_id=req.organization_id, assessment_id=req.assessment_id,
        user_id=admin_user.id, detail=f"request={req.id}; reason={req.rejection_reason[:500]}")
    _notify(db, req.user_id, "request.rejected", "Your request needs changes",
            req.rejection_reason, f"/marketplace/{req.id}")
    db.commit()
    db.refresh(req)
    return {"id": req.id, "status": req.status, "message": "Request rejected"}


@router.post("/bids/{bid_id}/approve")
def approve_bid(
    bid_id: int,
    notes: str | None = None,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    bid = db.get(models.BidSubmission, bid_id)
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    if bid.status != BID_PENDING:
        raise HTTPException(status_code=400, detail=f"Cannot approve bid with status: {bid.status}")
    req = db.get(models.PhysicalAssessmentRequest, bid.request_id)
    bid.status = BID_APPROVED
    bid.admin_reviewed_by = admin_user.id
    bid.admin_reviewed_at = now_iso()
    bid.admin_notes = (notes or "").strip()[:2000] or None
    record_audit(
        db, action="marketplace.bid_approved",
        organization_id=req.organization_id if req else None,
        assessment_id=req.assessment_id if req else None,
        user_id=admin_user.id, detail=f"request={bid.request_id}; bid={bid.id}")
    if req:
        _notify(db, req.user_id, "bid.approved", "A new bid is ready to review",
                f"An approved partner submitted a bid for {req.title}.",
                f"/marketplace/{req.id}")
    db.commit()
    db.refresh(bid)
    return {"id": bid.id, "status": bid.status, "message": "Bid approved"}


@router.post("/bids/{bid_id}/reject")
def reject_bid(
    bid_id: int,
    reason: str,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    bid = db.get(models.BidSubmission, bid_id)
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    if bid.status not in (BID_PENDING, BID_APPROVED):
        raise HTTPException(status_code=400, detail=f"Cannot reject bid with status: {bid.status}")
    req = db.get(models.PhysicalAssessmentRequest, bid.request_id)
    bid.status = BID_REJECTED
    bid.admin_reviewed_by = admin_user.id
    bid.admin_reviewed_at = now_iso()
    bid.admin_notes = reason.strip()[:2000]
    record_audit(
        db, action="marketplace.bid_rejected",
        organization_id=req.organization_id if req else None,
        assessment_id=req.assessment_id if req else None,
        user_id=admin_user.id, detail=f"request={bid.request_id}; bid={bid.id}; reason={reason[:500]}")
    db.commit()
    db.refresh(bid)
    return {"id": bid.id, "status": bid.status, "message": "Bid rejected"}


@router.post("/requests/{request_id}/award")
def award_request(
    request_id: int,
    bid_id: int,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    req = db.get(models.PhysicalAssessmentRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status not in (REQUEST_APPROVED, REQUEST_AWARDED):
        raise HTTPException(status_code=400, detail=f"Cannot award request with status: {req.status}")
    bid = db.get(models.BidSubmission, bid_id)
    if not bid or bid.request_id != request_id:
        raise HTTPException(status_code=404, detail="Bid not found")
    if bid.status != BID_APPROVED:
        raise HTTPException(status_code=400, detail="Only an approved bid can be awarded")
    bidder = db.get(models.BidderCompany, bid.bidder_company_id)
    if bidder is None or bidder.verification_status != VERIFY_APPROVED:
        raise HTTPException(status_code=400, detail="Bidder is not verified")

    previous = req.awarded_bid_id
    req.status = REQUEST_AWARDED
    req.awarded_bid_id = bid.id
    req.awarded_at = now_iso()
    bid.status = BID_AWARDED
    bid.awarded_at = now_iso()
    db.query(models.BidSubmission).filter(
        models.BidSubmission.request_id == request_id,
        models.BidSubmission.id != bid.id,
        models.BidSubmission.status == BID_APPROVED,
    ).update({models.BidSubmission.status: BID_NOT_SELECTED}, synchronize_session=False)

    conv = db.scalar(select(models.MarketplaceConversation).where(
        models.MarketplaceConversation.bid_id == bid.id))
    if conv is None:
        conv = models.MarketplaceConversation(
            request_id=request_id,
            bid_id=bid.id,
            requester_id=req.user_id,
            bidder_user_id=bidder.user_id,
            status="open",
            admin_involved=False,
            opened_at=now_iso(),
            last_message_at=now_iso(),
            closes_at=conversation_deadline(),
        )
        db.add(conv)
        db.flush()
    else:
        conv.status = "open"
        conv.closed_at = None
        conv.close_reason = None
        conv.last_message_at = now_iso()
        conv.closes_at = conversation_deadline()

    record_audit(
        db, action="marketplace.request_awarded",
        organization_id=req.organization_id, assessment_id=req.assessment_id,
        user_id=admin_user.id,
        detail=f"request={req.id}; bid={bid.id}; previous={previous}")
    _notify(db, req.user_id, "request.awarded", "Your implementation partner is confirmed",
            f"{bidder.company_name} was awarded {req.title}. The conversation is now open.",
            f"/marketplace/conversations/{conv.id}")
    _notify(db, bidder.user_id, "bid.awarded", "You won an implementation request",
            f"You were awarded {req.title}. The conversation is now open.",
            f"/marketplace/conversations/{conv.id}")
    db.commit()
    db.refresh(req)
    return {
        "id": req.id,
        "status": req.status,
        "awarded_bid_id": req.awarded_bid_id,
        "conversation_id": conv.id,
        "message": "Request awarded and conversation opened",
    }


@router.post("/bidders/{bidder_id}/verify")
def verify_bidder(
    bidder_id: int,
    decision: str = "approved",
    notes: str | None = None,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    bidder = db.get(models.BidderCompany, bidder_id)
    if not bidder:
        raise HTTPException(status_code=404, detail="Bidder not found")
    allowed = {VERIFY_APPROVED, VERIFY_REJECTED, VERIFY_MORE_INFO}
    if decision not in allowed:
        raise HTTPException(status_code=400, detail="invalid verification decision")
    bidder.verification_status = decision
    bidder.verified_by = admin_user.id
    bidder.verified_at = now_iso() if decision == VERIFY_APPROVED else None
    bidder.verification_notes = (notes or "").strip()[:2000] or None
    record_audit(
        db, action=f"marketplace.bidder_{decision}",
        user_id=admin_user.id, detail=f"bidder={bidder.id}; company={bidder.company_name[:120]}")
    _notify(db, bidder.user_id, f"bidder.{decision}", "Bidder verification updated",
            bidder.verification_notes, "/bidder/shop")
    db.commit()
    db.refresh(bidder)
    return {"id": bidder.id, "verification_status": bidder.verification_status}


# Backward-compatible endpoints. New clients should use /approve.
@router.post("/requests/{request_id}/verify")
def verify_request_legacy(
    request_id: int,
    notes: str | None = None,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    return approve_request(request_id, notes, db, admin_user)


@router.post("/requests/{request_id}/publish")
def publish_request_legacy(
    request_id: int,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    return approve_request(request_id, None, db, admin_user)


@router.get("/stats")
def get_admin_stats(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    return {
        "requests": {
            "pending": count_rows(
                db, models.PhysicalAssessmentRequest,
                models.PhysicalAssessmentRequest.status == REQUEST_PENDING),
            "approved": count_rows(
                db, models.PhysicalAssessmentRequest,
                models.PhysicalAssessmentRequest.status == REQUEST_APPROVED),
            "awarded": count_rows(
                db, models.PhysicalAssessmentRequest,
                models.PhysicalAssessmentRequest.status == REQUEST_AWARDED),
            "closed": count_rows(
                db, models.PhysicalAssessmentRequest,
                models.PhysicalAssessmentRequest.status == REQUEST_CLOSED),
        },
        "users": {
            "clients": count_rows(db, models.User, models.User.user_type == "client"),
            "bidders": count_rows(db, models.User, models.User.user_type == "bidder"),
        },
        "marketplace": {
            "active_subscriptions": count_rows(
                db, models.BidderCompany,
                models.BidderCompany.subscription_status == "active"),
            "verified_bidders": count_rows(
                db, models.BidderCompany,
                models.BidderCompany.verification_status == VERIFY_APPROVED),
            "pending_bids": count_rows(
                db, models.BidSubmission,
                models.BidSubmission.status == BID_PENDING),
            "total_bids": count_rows(db, models.BidSubmission),
        },
    }
