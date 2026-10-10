"""Advanced search and filtering service for marketplace."""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import Session

from elipsis_api import models


def search_marketplace_requests(
    db: Session,
    query: str | None = None,
    industry: str | None = None,
    company_size: str | None = None,
    budget_min: float | None = None,
    budget_max: float | None = None,
    location: str | None = None,
    deadline_before: datetime | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    limit: int = 50,
    offset: int = 0
) -> tuple[list[models.PhysicalAssessmentRequest], int]:
    """
    Advanced search for marketplace requests with filters.
    
    Args:
        db: Database session
        query: Text search query (title, description)
        industry: Filter by organization industry
        company_size: Filter by company size (small, medium, big)
        budget_min: Minimum budget range
        budget_max: Maximum budget range
        location: Filter by location (partial match)
        deadline_before: Filter requests with deadline before this date
        sort_by: Sort field (created_at, deadline, budget)
        sort_order: Sort order (asc, desc)
        limit: Results per page
        offset: Pagination offset
    
    Returns:
        (list of requests, total count)
    """
    # Base query for published requests
    base_query = select(models.PhysicalAssessmentRequest).where(
        models.PhysicalAssessmentRequest.status == "published"
    )
    
    conditions = []
    
    # Text search
    if query:
        search_filter = or_(
            models.PhysicalAssessmentRequest.title.ilike(f"%{query}%"),
            models.PhysicalAssessmentRequest.description.ilike(f"%{query}%")
        )
        conditions.append(search_filter)
    
    # Location filter
    if location:
        conditions.append(
            models.PhysicalAssessmentRequest.location.ilike(f"%{location}%")
        )
    
    # Deadline filter
    if deadline_before:
        conditions.append(
            models.PhysicalAssessmentRequest.deadline <= deadline_before
        )
    
    # Apply conditions
    if conditions:
        base_query = base_query.where(and_(*conditions))
    
    # Join with Organization for industry and company_size filters
    if industry or company_size:
        base_query = base_query.join(
            models.Organization,
            models.PhysicalAssessmentRequest.organization_id == models.Organization.id
        )
        
        if industry:
            base_query = base_query.where(
                models.Organization.industry.ilike(f"%{industry}%")
            )
        
        if company_size:
            base_query = base_query.where(
                models.Organization.company_size == company_size
            )
    
    # Sorting
    sort_field_map = {
        "created_at": models.PhysicalAssessmentRequest.created_at,
        "deadline": models.PhysicalAssessmentRequest.deadline,
        "title": models.PhysicalAssessmentRequest.title,
    }
    
    sort_field = sort_field_map.get(sort_by, models.PhysicalAssessmentRequest.created_at)
    
    if sort_order == "asc":
        base_query = base_query.order_by(sort_field.asc())
    else:
        base_query = base_query.order_by(sort_field.desc())
    
    # Get total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total_count = db.scalar(count_query) or 0
    
    # Apply pagination
    results = db.scalars(
        base_query.limit(limit).offset(offset)
    ).all()
    
    return results, total_count


def get_available_filters(db: Session) -> dict:
    """
    Get available filter options for marketplace search.
    
    Returns:
        dict with industries, locations, company_sizes
    """
    # Get unique industries
    industries = db.scalars(
        select(models.Organization.industry)
        .distinct()
        .where(models.Organization.industry.isnot(None))
        .order_by(models.Organization.industry)
    ).all()
    
    # Get unique locations from published requests
    locations = db.scalars(
        select(models.PhysicalAssessmentRequest.location)
        .distinct()
        .where(
            and_(
                models.PhysicalAssessmentRequest.status == "published",
                models.PhysicalAssessmentRequest.location.isnot(None)
            )
        )
        .order_by(models.PhysicalAssessmentRequest.location)
    ).all()
    
    # Company sizes
    company_sizes = ["small", "medium", "big"]
    
    return {
        "industries": list(industries),
        "locations": list(locations),
        "company_sizes": company_sizes
    }


def get_bidder_recommendations(
    db: Session,
    bidder_id: int,
    limit: int = 10
) -> list[models.PhysicalAssessmentRequest]:
    """
    Get recommended requests for a bidder based on their profile.
    
    Args:
        db: Database session
        bidder_id: Bidder company ID
        limit: Number of recommendations
    
    Returns:
        List of recommended requests
    """
    # Get bidder profile
    bidder = db.get(models.BidderCompany, bidder_id)
    if not bidder:
        return []
    
    # Get published requests
    query = select(models.PhysicalAssessmentRequest).where(
        models.PhysicalAssessmentRequest.status == "published"
    )
    
    # Filter out requests bidder already bid on
    existing_bids = db.scalars(
        select(models.BidSubmission.request_id).where(
            models.BidSubmission.bidder_company_id == bidder_id
        )
    ).all()
    
    if existing_bids:
        query = query.where(
            models.PhysicalAssessmentRequest.id.notin_(existing_bids)
        )
    
    # Sort by most recent first
    query = query.order_by(
        models.PhysicalAssessmentRequest.created_at.desc()
    ).limit(limit)
    
    return db.scalars(query).all()


def get_trending_requests(
    db: Session,
    days: int = 7,
    limit: int = 10
) -> list[tuple[models.PhysicalAssessmentRequest, int]]:
    """
    Get trending requests based on bid activity.
    
    Args:
        db: Database session
        days: Look back period in days
        limit: Number of results
    
    Returns:
        List of (request, bid_count) tuples
    """
    from datetime import timedelta
    
    cutoff_date = datetime.now() - timedelta(days=days)
    
    # Count bids per request
    bid_counts = db.execute(
        select(
            models.BidSubmission.request_id,
            func.count(models.BidSubmission.id).label("bid_count")
        )
        .where(models.BidSubmission.created_at >= cutoff_date)
        .group_by(models.BidSubmission.request_id)
        .order_by(func.count(models.BidSubmission.id).desc())
        .limit(limit)
    ).all()
    
    results = []
    for request_id, bid_count in bid_counts:
        request = db.get(models.PhysicalAssessmentRequest, request_id)
        if request and request.status == "published":
            results.append((request, bid_count))
    
    return results
