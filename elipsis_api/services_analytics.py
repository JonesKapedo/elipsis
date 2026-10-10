"""Analytics and metrics service for marketplace KPIs."""

from __future__ import annotations

from datetime import datetime, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from elipsis_api import models


def get_marketplace_overview(db: Session) -> dict:
    """Get high-level marketplace metrics."""
    
    # Total counts
    total_requests = db.scalar(
        select(func.count()).select_from(models.PhysicalAssessmentRequest)
    ) or 0
    
    total_bids = db.scalar(
        select(func.count()).select_from(models.BidSubmission)
    ) or 0
    
    total_clients = db.scalar(
        select(func.count()).select_from(models.User).where(
            models.User.user_type == "client"
        )
    ) or 0
    
    total_bidders = db.scalar(
        select(func.count()).select_from(models.User).where(
            models.User.user_type == "bidder"
        )
    ) or 0
    
    active_subscriptions = db.scalar(
        select(func.count()).select_from(models.BidderCompany).where(
            models.BidderCompany.subscription_status == "active"
        )
    ) or 0
    
    published_requests = db.scalar(
        select(func.count()).select_from(models.PhysicalAssessmentRequest).where(
            models.PhysicalAssessmentRequest.status == "published"
        )
    ) or 0
    
    return {
        "total_requests": total_requests,
        "published_requests": published_requests,
        "total_bids": total_bids,
        "total_clients": total_clients,
        "total_bidders": total_bidders,
        "active_subscriptions": active_subscriptions,
        "average_bids_per_request": round(total_bids / published_requests, 2) if published_requests > 0 else 0
    }


def get_request_metrics(db: Session) -> dict:
    """Get request-specific metrics."""
    
    # Requests by status
    status_counts = {}
    for status in ["pending", "verified", "published", "in_progress", "completed", "rejected"]:
        count = db.scalar(
            select(func.count()).select_from(models.PhysicalAssessmentRequest).where(
                models.PhysicalAssessmentRequest.status == status
            )
        ) or 0
        status_counts[status] = count
    
    # Average time to verification (pending -> verified)
    # This would require timestamp tracking, simplified here
    
    # Requests by company size
    size_counts = db.execute(
        select(
            models.Organization.company_size,
            func.count(models.PhysicalAssessmentRequest.id).label("count")
        )
        .join(
            models.Organization,
            models.PhysicalAssessmentRequest.organization_id == models.Organization.id
        )
        .group_by(models.Organization.company_size)
    ).all()
    
    requests_by_size = {size or "unknown": count for size, count in size_counts}
    
    return {
        "by_status": status_counts,
        "by_company_size": requests_by_size
    }


def get_bidder_metrics(db: Session) -> dict:
    """Get bidder-specific metrics."""
    
    # Top bidders by number of bids
    top_bidders = db.execute(
        select(
            models.BidderCompany.company_name,
            func.count(models.BidSubmission.id).label("bid_count")
        )
        .join(
            models.BidSubmission,
            models.BidderCompany.id == models.BidSubmission.bidder_company_id
        )
        .group_by(models.BidderCompany.id, models.BidderCompany.company_name)
        .order_by(func.count(models.BidSubmission.id).desc())
        .limit(10)
    ).all()
    
    # Bidders with most portfolio items
    top_portfolio = db.execute(
        select(
            models.BidderCompany.company_name,
            func.count(models.BidderPortfolio.id).label("portfolio_count")
        )
        .join(
            models.BidderPortfolio,
            models.BidderCompany.id == models.BidderPortfolio.bidder_company_id
        )
        .group_by(models.BidderCompany.id, models.BidderCompany.company_name)
        .order_by(func.count(models.BidderPortfolio.id).desc())
        .limit(10)
    ).all()
    
    # Average rating
    avg_rating = db.scalar(
        select(func.avg(models.BidderFeedback.rating)).where(
            models.BidderFeedback.rating.isnot(None)
        )
    ) or 0
    
    return {
        "top_bidders": [
            {"company": name, "bids": count}
            for name, count in top_bidders
        ],
        "top_portfolio": [
            {"company": name, "items": count}
            for name, count in top_portfolio
        ],
        "average_rating": round(float(avg_rating), 2)
    }


def get_time_series_metrics(
    db: Session,
    days: int = 30
) -> dict:
    """Get time series data for charts."""
    
    cutoff_date = datetime.now() - timedelta(days=days)
    
    # Requests created per day
    requests_by_day = db.execute(
        select(
            func.date(models.PhysicalAssessmentRequest.created_at).label("date"),
            func.count(models.PhysicalAssessmentRequest.id).label("count")
        )
        .where(models.PhysicalAssessmentRequest.created_at >= cutoff_date)
        .group_by(func.date(models.PhysicalAssessmentRequest.created_at))
        .order_by(func.date(models.PhysicalAssessmentRequest.created_at))
    ).all()
    
    # Bids submitted per day
    bids_by_day = db.execute(
        select(
            func.date(models.BidSubmission.created_at).label("date"),
            func.count(models.BidSubmission.id).label("count")
        )
        .where(models.BidSubmission.created_at >= cutoff_date)
        .group_by(func.date(models.BidSubmission.created_at))
        .order_by(func.date(models.BidSubmission.created_at))
    ).all()
    
    # New users per day
    users_by_day = db.execute(
        select(
            func.date(models.User.created_at).label("date"),
            func.count(models.User.id).label("count")
        )
        .where(models.User.created_at >= cutoff_date)
        .group_by(func.date(models.User.created_at))
        .order_by(func.date(models.User.created_at))
    ).all()
    
    return {
        "requests_by_day": [
            {"date": str(date), "count": count}
            for date, count in requests_by_day
        ],
        "bids_by_day": [
            {"date": str(date), "count": count}
            for date, count in bids_by_day
        ],
        "users_by_day": [
            {"date": str(date), "count": count}
            for date, count in users_by_day
        ]
    }


def get_revenue_metrics(db: Session) -> dict:
    """Get revenue and financial metrics."""
    
    # Active subscriptions by tier
    subscriptions_by_tier = db.execute(
        select(
            models.BidderCompany.subscription_tier,
            func.count(models.BidderCompany.id).label("count")
        )
        .where(models.BidderCompany.subscription_status == "active")
        .group_by(models.BidderCompany.subscription_tier)
    ).all()
    
    # Subscription pricing (would come from config)
    pricing = {
        "monthly": 99,
        "quarterly": 249,
        "yearly": 899
    }
    
    # Estimated monthly recurring revenue
    mrr = sum(
        (pricing.get(tier, 0) if tier != "yearly" else pricing["yearly"] / 12)
        * count
        for tier, count in subscriptions_by_tier
    )
    
    return {
        "subscriptions_by_tier": {
            tier or "none": count
            for tier, count in subscriptions_by_tier
        },
        "estimated_mrr": round(mrr, 2),
        "estimated_arr": round(mrr * 12, 2)
    }


def get_engagement_metrics(db: Session) -> dict:
    """Get user engagement metrics."""
    
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    # Active users (last 7 days)
    active_week = db.scalar(
        select(func.count()).select_from(models.User).where(
            models.User.last_login >= week_ago
        )
    ) or 0
    
    # Active users (last 30 days)
    active_month = db.scalar(
        select(func.count()).select_from(models.User).where(
            models.User.last_login >= month_ago
        )
    ) or 0
    
    # Average bids per active bidder
    active_bidders = db.scalar(
        select(func.count()).select_from(models.User).where(
            and_(
                models.User.user_type == "bidder",
                models.User.last_login >= month_ago
            )
        )
    ) or 0
    
    total_bids = db.scalar(
        select(func.count()).select_from(models.BidSubmission)
    ) or 0
    
    return {
        "active_users_week": active_week,
        "active_users_month": active_month,
        "avg_bids_per_bidder": round(total_bids / active_bidders, 2) if active_bidders > 0 else 0
    }


def get_conversion_metrics(db: Session) -> dict:
    """Get conversion funnel metrics."""
    
    total_requests = db.scalar(
        select(func.count()).select_from(models.PhysicalAssessmentRequest)
    ) or 1  # Avoid division by zero
    
    verified_requests = db.scalar(
        select(func.count()).select_from(models.PhysicalAssessmentRequest).where(
            models.PhysicalAssessmentRequest.status.in_(["verified", "published", "in_progress", "completed"])
        )
    ) or 0
    
    published_requests = db.scalar(
        select(func.count()).select_from(models.PhysicalAssessmentRequest).where(
            models.PhysicalAssessmentRequest.status.in_(["published", "in_progress", "completed"])
        )
    ) or 0
    
    requests_with_bids = db.scalar(
        select(func.count(func.distinct(models.BidSubmission.request_id)))
        .select_from(models.BidSubmission)
    ) or 0
    
    return {
        "verification_rate": round((verified_requests / total_requests) * 100, 2),
        "publication_rate": round((published_requests / total_requests) * 100, 2),
        "bid_rate": round((requests_with_bids / published_requests) * 100, 2) if published_requests > 0 else 0
    }
