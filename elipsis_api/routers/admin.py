"""Admin API routes for request verification and management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from elipsis_api import models, services
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user
from elipsis_api.query_utils import count_rows, isoformat

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(current_user: models.User = Depends(get_current_user)):
    """Dependency to check if user is admin."""
    if current_user is None or not (current_user.is_admin or services.is_admin(current_user)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


@router.get("/requests")
def list_all_requests(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """
    List all physical assessment requests (admin only).

    - **status_filter**: Optional filter (pending, verified, published, rejected, completed)
    - Returns all requests with full details
    """
    query = select(models.PhysicalAssessmentRequest)

    if status_filter:
        query = query.where(models.PhysicalAssessmentRequest.status == status_filter)

    requests = db.scalars(query.order_by(models.PhysicalAssessmentRequest.created_at.desc())).all()

    results = []
    for req in requests:
        # Get organization
        org = db.get(models.Organization, req.organization_id)

        # Get client user
        client = db.get(models.User, org.user_id) if org else None

        # Count documents
        doc_count = count_rows(
            db, models.RequestDocument,
            models.RequestDocument.request_id == req.id)

        # Count bids
        bid_count = count_rows(
            db, models.BidSubmission,
            models.BidSubmission.request_id == req.id)

        results.append({
            "id": req.id,
            "title": req.title,
            "description": req.description,
            "budget_range": req.budget_range,
            "deadline": isoformat(req.deadline),
            "location": req.location,
            "status": req.status,
            "verified_by_admin": req.verified_by_admin,
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
            "document_count": doc_count,
            "bid_count": bid_count,
        })

    return {"requests": results, "count": len(results)}


@router.get("/requests/{request_id}")
def get_request_details(
    request_id: int,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """
    Get full details of a request including documents and bids (admin only).

    - **request_id**: Request ID
    """
    req = db.get(models.PhysicalAssessmentRequest, request_id)

    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )

    # Get organization
    org = db.get(models.Organization, req.organization_id)

    # Get client user
    client = db.get(models.User, org.user_id) if org else None

    # Get documents
    documents = db.scalars(
        select(models.RequestDocument).where(
            models.RequestDocument.request_id == request_id
        )
    ).all()

    # Get bids
    bids = db.scalars(
        select(models.BidSubmission).where(
            models.BidSubmission.request_id == request_id
        )
    ).all()

    bid_list = []
    for bid in bids:
        bidder = db.get(models.BidderCompany, bid.bidder_company_id)
        bid_list.append({
            "id": bid.id,
            "bidder_name": bidder.company_name if bidder else "Unknown",
            "bidder_contact": bidder.contact_email if bidder else None,
            "proposal": bid.proposal,
            "estimated_cost": bid.estimated_cost,
            "timeline": bid.timeline,
            "status": bid.status,
            "submitted_at": isoformat(bid.created_at),
        })

    return {
        "id": req.id,
        "title": req.title,
        "description": req.description,
        "budget_range": req.budget_range,
        "deadline": isoformat(req.deadline),
        "location": req.location,
        "status": req.status,
        "verified_by_admin": req.verified_by_admin,
        "admin_notes": req.admin_notes,
        "created_at": isoformat(req.created_at),
        "organization": {
            "id": org.id,
            "name": org.name,
            "industry": org.industry,
            "company_size": org.company_size or "small",
            "employee_count": org.employee_count,
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
        "documents": [
            {
                "id": doc.id,
                "filename": doc.filename,
                "file_url": doc.file_url,
                "file_type": doc.file_type,
                "uploaded_at": isoformat(doc.uploaded_at),
            }
            for doc in documents
        ],
        "bids": bid_list,
    }


@router.post("/requests/{request_id}/verify")
def verify_request(
    request_id: int,
    notes: str | None = None,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """
    Verify a request (admin only).

    Marks request as verified but not yet published to marketplace.

    - **request_id**: Request ID
    - **notes**: Admin notes/comments
    """
    req = db.get(models.PhysicalAssessmentRequest, request_id)

    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )

    if req.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot verify request with status: {req.status}"
        )

    req.status = "verified"
    req.verified_by_admin = admin_user.id
    req.admin_notes = notes

    db.commit()
    db.refresh(req)

    return {
        "id": req.id,
        "status": req.status,
        "message": "Request verified successfully"
    }


@router.post("/requests/{request_id}/publish")
def publish_request(
    request_id: int,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """
    Publish a verified request to the marketplace (admin only).

    - **request_id**: Request ID
    """
    req = db.get(models.PhysicalAssessmentRequest, request_id)

    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )

    if req.status not in ["pending", "verified"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot publish request with status: {req.status}"
        )

    req.status = "published"
    req.verified_by_admin = admin_user.id

    db.commit()
    db.refresh(req)

    return {
        "id": req.id,
        "status": req.status,
        "message": "Request published to marketplace successfully"
    }


@router.post("/requests/{request_id}/reject")
def reject_request(
    request_id: int,
    reason: str,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """
    Reject a request (admin only).

    - **request_id**: Request ID
    - **reason**: Rejection reason (required)
    """
    req = db.get(models.PhysicalAssessmentRequest, request_id)

    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )

    if req.status not in ["pending", "verified"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject request with status: {req.status}"
        )

    req.status = "rejected"
    req.verified_by_admin = admin_user.id
    req.admin_notes = f"Rejected: {reason}"

    db.commit()
    db.refresh(req)

    return {
        "id": req.id,
        "status": req.status,
        "message": "Request rejected"
    }


@router.get("/stats")
def get_admin_stats(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """Get marketplace statistics (admin only)."""

    # Count requests by status
    pending_count = count_rows(
        db, models.PhysicalAssessmentRequest,
        models.PhysicalAssessmentRequest.status == "pending")

    verified_count = count_rows(
        db, models.PhysicalAssessmentRequest,
        models.PhysicalAssessmentRequest.status == "verified")

    published_count = count_rows(
        db, models.PhysicalAssessmentRequest,
        models.PhysicalAssessmentRequest.status == "published")

    # Count users by type
    client_count = count_rows(
        db, models.User, models.User.user_type == "client")

    bidder_count = count_rows(
        db, models.User, models.User.user_type == "bidder")

    # Count active subscriptions
    active_subscriptions = count_rows(
        db, models.BidderCompany,
        models.BidderCompany.subscription_status == "active")

    # Count total bids
    total_bids = count_rows(db, models.BidSubmission)

    return {
        "requests": {
            "pending": pending_count,
            "verified": verified_count,
            "published": published_count,
        },
        "users": {
            "clients": client_count,
            "bidders": bidder_count,
        },
        "marketplace": {
            "active_subscriptions": active_subscriptions,
            "total_bids": total_bids,
        }
    }
