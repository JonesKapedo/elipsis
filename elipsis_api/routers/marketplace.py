"""Marketplace API routes for browsing and bidding on requests."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from elipsis_api import models, schemas
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user
from elipsis_api.services_marketplace import is_bidder_subscribed, get_bidder_company

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


@router.get("/requests")
def list_marketplace_requests(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(get_current_user),
):
    """
    List published physical assessment requests in the marketplace.
    
    - **status_filter**: Optional filter (published, in_progress, completed)
    - Returns list of requests with company details
    """
    query = select(models.PhysicalAssessmentRequest).where(
        models.PhysicalAssessmentRequest.status == "published"
    )
    
    if status_filter:
        query = query.where(models.PhysicalAssessmentRequest.status == status_filter)
    
    requests = db.scalars(query).all()
    
    results = []
    for req in requests:
        # Get organization details
        org = db.get(models.Organization, req.organization_id)
        
        # Count documents
        doc_count = db.scalar(
            select(models.RequestDocument)
            .where(models.RequestDocument.request_id == req.id)
            .count()
        ) or 0
        
        # Count bids
        bid_count = db.scalar(
            select(models.BidSubmission)
            .where(models.BidSubmission.request_id == req.id)
            .count()
        ) or 0
        
        results.append({
            "id": req.id,
            "title": req.title,
            "description": req.description,
            "budget_range": req.budget_range,
            "deadline": req.deadline.isoformat() if req.deadline else None,
            "location": req.location,
            "status": req.status,
            "created_at": req.created_at.isoformat(),
            "organization": {
                "id": org.id,
                "name": org.name,
                "industry": org.industry,
                "company_size": org.company_size or "small",
                "city": org.city,
                "country": org.country,
            } if org else None,
            "document_count": doc_count,
            "bid_count": bid_count,
        })
    
    return {"requests": results, "count": len(results)}


@router.get("/requests/{request_id}")
def get_marketplace_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(get_current_user),
):
    """
    Get detailed information about a specific marketplace request.
    
    - **request_id**: Request ID
    - Returns request details including documents and bids (if authorized)
    """
    req = db.get(models.PhysicalAssessmentRequest, request_id)
    
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )
    
    # Get organization
    org = db.get(models.Organization, req.organization_id)
    
    # Get documents
    documents = db.scalars(
        select(models.RequestDocument).where(
            models.RequestDocument.request_id == request_id
        )
    ).all()
    
    # Check if user is subscribed bidder
    can_view_contact = False
    if current_user and current_user.user_type == "bidder":
        can_view_contact = is_bidder_subscribed(db, current_user.id)
    
    # Get bids (only if user is admin or request owner)
    bids = []
    if current_user and (current_user.is_admin or (org and org.user_id == current_user.id)):
        bid_records = db.scalars(
            select(models.BidSubmission).where(
                models.BidSubmission.request_id == request_id
            )
        ).all()
        
        for bid in bid_records:
            bidder = db.get(models.BidderCompany, bid.bidder_company_id)
            bids.append({
                "id": bid.id,
                "bidder_name": bidder.company_name if bidder else "Unknown",
                "proposal": bid.proposal,
                "estimated_cost": bid.estimated_cost,
                "timeline": bid.timeline,
                "status": bid.status,
                "submitted_at": bid.created_at.isoformat(),
            })
    
    return {
        "id": req.id,
        "title": req.title,
        "description": req.description,
        "budget_range": req.budget_range,
        "deadline": req.deadline.isoformat() if req.deadline else None,
        "location": req.location,
        "status": req.status,
        "created_at": req.created_at.isoformat(),
        "organization": {
            "id": org.id,
            "name": org.name,
            "industry": org.industry,
            "company_size": org.company_size or "small",
            "city": org.city,
            "country": org.country,
            "contact_email": org.contact_email if can_view_contact else None,
            "contact_phone": org.contact_phone if can_view_contact else None,
        } if org else None,
        "documents": [
            {
                "id": doc.id,
                "filename": doc.filename,
                "file_url": doc.file_url,
                "file_type": doc.file_type,
                "uploaded_at": doc.uploaded_at.isoformat(),
            }
            for doc in documents
        ],
        "bids": bids,
    }


@router.post("/requests/{request_id}/bid", status_code=status.HTTP_201_CREATED)
def submit_bid(
    request_id: int,
    proposal: str,
    estimated_cost: float,
    timeline: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Submit a bid for a marketplace request (bidders only with active subscription).
    
    - **request_id**: Request ID
    - **proposal**: Your proposal/approach
    - **estimated_cost**: Your estimated cost in USD
    - **timeline**: Estimated timeline (e.g., "2-3 weeks")
    """
    # Check user is a bidder
    if current_user.user_type != "bidder":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only bidder accounts can submit bids"
        )
    
    # Check subscription
    if not is_bidder_subscribed(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Active subscription required to submit bids"
        )
    
    # Get bidder company
    bidder = get_bidder_company(db, current_user.id)
    if not bidder:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please create your bidder profile first"
        )
    
    # Check request exists and is published
    req = db.get(models.PhysicalAssessmentRequest, request_id)
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )
    
    if req.status != "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request is not available for bidding"
        )
    
    # Check if already submitted bid
    existing_bid = db.scalar(
        select(models.BidSubmission).where(
            models.BidSubmission.request_id == request_id,
            models.BidSubmission.bidder_company_id == bidder.id
        )
    )
    
    if existing_bid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already submitted a bid for this request"
        )
    
    # Create bid
    bid = models.BidSubmission(
        request_id=request_id,
        bidder_company_id=bidder.id,
        proposal=proposal,
        estimated_cost=estimated_cost,
        timeline=timeline,
        status="pending"
    )
    
    db.add(bid)
    db.commit()
    db.refresh(bid)
    
    return {
        "id": bid.id,
        "request_id": request_id,
        "status": bid.status,
        "submitted_at": bid.created_at.isoformat(),
        "message": "Bid submitted successfully"
    }
