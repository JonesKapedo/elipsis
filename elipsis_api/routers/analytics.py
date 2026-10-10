"""Analytics dashboard router for KPIs and metrics."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from elipsis_api import models
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user
from elipsis_api.services_analytics import (
    get_marketplace_overview,
    get_request_metrics,
    get_bidder_metrics,
    get_time_series_metrics,
    get_revenue_metrics,
    get_engagement_metrics,
    get_conversion_metrics
)
from elipsis_api.services_search import (
    get_available_filters,
    search_marketplace_requests,
    get_trending_requests
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


def require_admin(current_user: models.User = Depends(get_current_user)):
    """Dependency to check if user is admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


@router.get("/dashboard")
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """
    Get comprehensive dashboard metrics (admin only).
    
    Returns overview, requests, bidders, revenue, engagement, and conversion metrics.
    """
    return {
        "overview": get_marketplace_overview(db),
        "requests": get_request_metrics(db),
        "bidders": get_bidder_metrics(db),
        "revenue": get_revenue_metrics(db),
        "engagement": get_engagement_metrics(db),
        "conversions": get_conversion_metrics(db)
    }


@router.get("/overview")
def get_overview(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """Get high-level marketplace metrics."""
    return get_marketplace_overview(db)


@router.get("/requests")
def get_requests_analytics(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """Get request-specific analytics."""
    return get_request_metrics(db)


@router.get("/bidders")
def get_bidders_analytics(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """Get bidder-specific analytics."""
    return get_bidder_metrics(db)


@router.get("/time-series")
def get_time_series(
    days: int = 30,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """
    Get time series data for charts.
    
    - **days**: Look back period (default 30)
    """
    return get_time_series_metrics(db, days)


@router.get("/revenue")
def get_revenue(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """Get revenue and financial metrics."""
    return get_revenue_metrics(db)


@router.get("/engagement")
def get_engagement(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """Get user engagement metrics."""
    return get_engagement_metrics(db)


@router.get("/conversions")
def get_conversions(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """Get conversion funnel metrics."""
    return get_conversion_metrics(db)


@router.get("/trending")
def get_trending(
    days: int = 7,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Get trending requests based on bid activity.
    
    - **days**: Look back period (default 7)
    - **limit**: Number of results (default 10)
    """
    results = get_trending_requests(db, days, limit)
    
    return {
        "trending": [
            {
                "id": req.id,
                "title": req.title,
                "description": req.description,
                "budget_range": req.budget_range,
                "location": req.location,
                "bid_count": bid_count,
                "created_at": req.created_at.isoformat()
            }
            for req, bid_count in results
        ],
        "count": len(results)
    }


@router.get("/filters")
def get_filters(
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(get_current_user),
):
    """Get available filter options for marketplace search."""
    return get_available_filters(db)


@router.get("/search")
def search_requests(
    query: str | None = None,
    industry: str | None = None,
    company_size: str | None = None,
    location: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(get_current_user),
):
    """
    Advanced search for marketplace requests.
    
    - **query**: Text search in title/description
    - **industry**: Filter by industry
    - **company_size**: Filter by company size (small, medium, big)
    - **location**: Filter by location
    - **sort_by**: Sort field (created_at, deadline, title)
    - **sort_order**: Sort order (asc, desc)
    - **limit**: Results per page
    - **offset**: Pagination offset
    """
    requests, total_count = search_marketplace_requests(
        db,
        query=query,
        industry=industry,
        company_size=company_size,
        location=location,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset
    )
    
    # Format results
    results = []
    for req in requests:
        org = db.get(models.Organization, req.organization_id)
        
        # Count documents
        from sqlalchemy import select
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
    
    return {
        "requests": results,
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total_count
    }
