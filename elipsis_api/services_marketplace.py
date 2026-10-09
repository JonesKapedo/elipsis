"""Marketplace helper services for company sizing and utilities."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from elipsis_api import models


def calculate_company_size(employee_count: int | None, annual_revenue_avg: float | None) -> str:
    """
    Calculate company size based on employees and revenue.
    Returns: 'small', 'medium', or 'big'
    
    Criteria:
    - Small: <50 employees OR <$5M revenue
    - Medium: 50-500 employees OR $5M-$50M revenue  
    - Big: >500 employees OR >$50M revenue
    """
    if employee_count is None and annual_revenue_avg is None:
        return 'small'  # Default
    
    # Check employee count (priority)
    if employee_count is not None:
        if employee_count > 500:
            return 'big'
        elif employee_count >= 50:
            return 'medium'
        else:
            return 'small'
    
    # Check revenue
    if annual_revenue_avg is not None:
        if annual_revenue_avg > 50_000_000:  # >$50M
            return 'big'
        elif annual_revenue_avg >= 5_000_000:  # $5M-$50M
            return 'medium'
        else:
            return 'small'
    
    return 'small'


def get_company_badge_color(size: str) -> str:
    """Return badge color for company size."""
    return {
        'small': 'green',
        'medium': 'maroon',
        'big': 'red'
    }.get(size, 'green')


def update_organization_size(db: Session, org_id: int):
    """Update company size for an organization based on current data."""
    org = db.get(models.Organization, org_id)
    if org is None:
        return
    
    # Calculate average revenue
    revenue_avg = None
    if org.annual_revenue_min is not None and org.annual_revenue_max is not None:
        revenue_avg = (org.annual_revenue_min + org.annual_revenue_max) / 2
    elif org.annual_revenue_min is not None:
        revenue_avg = org.annual_revenue_min
    elif org.annual_revenue_max is not None:
        revenue_avg = org.annual_revenue_max
    
    # Calculate and update size
    org.company_size = calculate_company_size(org.employee_count, revenue_avg)
    db.commit()


def get_user_organizations(db: Session, user_id: int) -> list[dict]:
    """Get all organizations owned by or accessible to a user."""
    # Get directly owned organizations
    orgs = db.scalars(select(models.Organization).where(
        models.Organization.user_id == user_id
    )).all()
    
    # Also get organizations linked through OrgOwner
    org_owners = db.scalars(select(models.OrgOwner).where(
        models.OrgOwner.user_id == user_id
    )).all()
    
    org_ids = {org.id for org in orgs}
    for owner in org_owners:
        if owner.organization_id not in org_ids:
            org = db.get(models.Organization, owner.organization_id)
            if org:
                orgs.append(org)
                org_ids.add(org.id)
    
    return [
        {
            "id": org.id,
            "name": org.name,
            "industry": org.industry,
            "employee_count": org.employee_count,
            "company_size": org.company_size or 'small',
            "city": org.city,
            "country": org.country,
        }
        for org in orgs
    ]


def get_organization_departments(db: Session, org_id: int) -> list[dict]:
    """Get all departments for an organization."""
    depts = db.scalars(select(models.Department).where(
        models.Department.organization_id == org_id
    )).all()
    
    return [
        {
            "id": dept.id,
            "name": dept.name,
            "head": dept.head,
            "staff_count": dept.staff_count,
        }
        for dept in depts
    ]


def is_bidder_subscribed(db: Session, user_id: int) -> bool:
    """Check if a bidder user has an active subscription."""
    bidder = db.scalar(select(models.BidderCompany).where(
        models.BidderCompany.user_id == user_id
    ))
    
    if not bidder:
        return False
    
    return bidder.subscription_status == "active"


def get_bidder_company(db: Session, user_id: int):
    """Get bidder company for a user."""
    return db.scalar(select(models.BidderCompany).where(
        models.BidderCompany.user_id == user_id
    ))
