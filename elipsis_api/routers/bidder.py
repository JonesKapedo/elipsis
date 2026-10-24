"""Bidder API routes for shop profile and subscription management."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from elipsis_api import models
from elipsis_api.config import BILLING_ENABLED
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user
from elipsis_api.premium import BIDDER_PLANS
from elipsis_api.query_utils import isoformat
from elipsis_api.services_marketplace import (
    bidder_slug,
    bidder_verification_label,
    get_bidder_company,
    is_active_bidder,
    is_bidder_subscribed,
    now_iso,
)

router = APIRouter(prefix="/bidder", tags=["bidder"])


def _parse_dt(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


@router.get("/shop")
def get_bidder_shop(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Get bidder shop profile.
    
    Returns shop details including portfolio and subscription status.
    """
    if current_user.user_type != "bidder":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only bidder accounts can access shop"
        )
    
    bidder = get_bidder_company(db, current_user.id)
    
    if not bidder:
        # Return empty template for first-time setup
        return {
            "exists": False,
            "message": "Create your shop profile to get started"
        }
    
    # Get portfolio items
    portfolio = db.scalars(
        select(models.BidderPortfolio).where(
            models.BidderPortfolio.bidder_company_id == bidder.id
        )
    ).all()
    
    # Get feedback
    feedback = db.scalars(
        select(models.BidderFeedback).where(
            models.BidderFeedback.bidder_company_id == bidder.id
        )
    ).all()
    
    # Calculate average rating
    ratings = [f.rating for f in feedback if f.rating]
    avg_rating = sum(ratings) / len(ratings) if ratings else None
    
    return {
        "exists": True,
        "id": bidder.id,
        "company_name": bidder.company_name,
        "description": bidder.description,
        "services_offered": bidder.services_offered,
        "rate_card": bidder.rate_card,
        "website": bidder.website,
        "contact_email": bidder.contact_email,
        "contact_phone": bidder.contact_phone,
        "years_in_business": bidder.years_in_business,
        "team_size": bidder.team_size,
        "subscription_status": bidder.subscription_status,
        "subscription_tier": bidder.subscription_tier,
        "subscription_expires": isoformat(bidder.subscription_expires_at),
        "verification_status": bidder.verification_status,
        "verification_label": bidder_verification_label(bidder.verification_status),
        "verification_notes": bidder.verification_notes,
        "verified_at": isoformat(bidder.verified_at),
        "partner_tier": bidder.partner_tier,
        "pinned_rank": bidder.pinned_rank,
        "can_bid": is_active_bidder(db, current_user.id),
        "portfolio": [
            {
                "id": p.id,
                "project_name": p.project_name,
                "description": p.description,
                "image_url": p.image_url,
                "project_url": p.project_url,
            }
            for p in portfolio
        ],
        "feedback": [
            {
                "id": f.id,
                "rating": f.rating,
                "comment": f.comment,
                "created_at": isoformat(f.created_at),
            }
            for f in feedback
        ],
        "average_rating": avg_rating,
        "feedback_count": len(feedback),
    }


@router.put("/shop")
def update_bidder_shop(
    company_name: str,
    description: str | None = None,
    services_offered: str | None = None,
    website: str | None = None,
    contact_email: str | None = None,
    contact_phone: str | None = None,
    years_in_business: int | None = None,
    team_size: int | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Create or update bidder shop profile.
    
    - **company_name**: Your company name (required)
    - **description**: About your company
    - **services_offered**: Services you provide
    - **website**: Your website URL
    - **contact_email**: Contact email
    - **contact_phone**: Contact phone
    - **years_in_business**: Years of experience
    - **team_size**: Number of team members
    """
    if current_user.user_type != "bidder":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only bidder accounts can manage shop"
        )
    
    bidder = get_bidder_company(db, current_user.id)
    
    if not bidder:
        # Create new bidder profile
        bidder = models.BidderCompany(
            user_id=current_user.id,
            company_name=company_name,
            slug=bidder_slug(db, company_name),
            description=description,
            services_offered=services_offered,
            website=website,
            contact_email=contact_email,
            contact_phone=contact_phone,
            years_in_business=years_in_business,
            team_size=team_size,
            subscription_status="inactive",
            verification_status="submitted",
            verification_submitted_at=now_iso(),
            partner_tier="standard",
        )
        db.add(bidder)
    else:
        # Update existing
        bidder.company_name = company_name
        if not bidder.slug:
            bidder.slug = bidder_slug(db, company_name, bidder.id)
        bidder.description = description
        bidder.services_offered = services_offered
        bidder.website = website
        bidder.contact_email = contact_email
        bidder.contact_phone = contact_phone
        bidder.years_in_business = years_in_business
        bidder.team_size = team_size
    
    db.commit()
    db.refresh(bidder)
    
    return {
        "id": bidder.id,
        "company_name": bidder.company_name,
        "subscription_status": bidder.subscription_status,
        "verification_status": bidder.verification_status,
        "verification_label": bidder_verification_label(bidder.verification_status),
        "message": "Shop profile updated successfully"
    }


@router.post("/portfolio")
def add_portfolio_item(
    project_name: str,
    description: str | None = None,
    image_url: str | None = None,
    project_url: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Add a portfolio item to your shop.
    
    - **project_name**: Project title (required)
    - **description**: Project description
    - **image_url**: Project screenshot/image URL
    - **project_url**: Live project URL
    """
    if current_user.user_type != "bidder":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only bidder accounts can manage portfolio"
        )
    
    bidder = get_bidder_company(db, current_user.id)
    
    if not bidder:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Create your shop profile first"
        )
    
    portfolio = models.BidderPortfolio(
        bidder_company_id=bidder.id,
        project_name=project_name,
        description=description,
        image_url=image_url,
        project_url=project_url,
    )
    
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    
    return {
        "id": portfolio.id,
        "project_name": portfolio.project_name,
        "message": "Portfolio item added successfully"
    }


@router.delete("/portfolio/{portfolio_id}")
def delete_portfolio_item(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete a portfolio item."""
    if current_user.user_type != "bidder":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only bidder accounts can manage portfolio"
        )
    
    bidder = get_bidder_company(db, current_user.id)
    if not bidder:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shop profile not found"
        )
    
    portfolio = db.get(models.BidderPortfolio, portfolio_id)
    
    if not portfolio or portfolio.bidder_company_id != bidder.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio item not found"
        )
    
    db.delete(portfolio)
    db.commit()
    
    return {"message": "Portfolio item deleted"}


@router.get("/subscription")
def get_subscription_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Check subscription status.
    
    Returns current subscription tier, status, and expiration.
    """
    if current_user.user_type != "bidder":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only bidder accounts have subscriptions"
        )
    
    bidder = get_bidder_company(db, current_user.id)
    
    if not bidder:
        return {
            "has_profile": False,
            "is_active": False,
            "message": "Create your shop profile first"
        }
    
    is_active = is_bidder_subscribed(db, current_user.id)
    
    # Calculate days remaining
    days_remaining = None
    expires_at = _parse_dt(bidder.subscription_expires_at)
    if expires_at:
        delta = expires_at - datetime.now()
        days_remaining = max(0, delta.days)
    
    return {
        "has_profile": True,
        "is_active": is_active,
        "tier": bidder.subscription_tier,
        "status": bidder.subscription_status,
        "expires": isoformat(bidder.subscription_expires_at),
        "days_remaining": days_remaining,
        "verification_status": bidder.verification_status,
        "verification_label": bidder_verification_label(bidder.verification_status),
        "can_bid": is_active_bidder(db, current_user.id),
    }


@router.post("/subscription/activate")
def activate_subscription(
    tier: str = "monthly",  # monthly, six_months, yearly
    payment_reference: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Activate or renew subscription (after payment).
    
    - **tier**: monthly, six_months, or yearly
    - **payment_reference**: Payment transaction reference
    """
    if not BILLING_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Billing is not enabled")
    if current_user.user_type != "bidder":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only bidder accounts can subscribe"
        )
    
    if not payment_reference:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="A verified payment reference is required to activate a subscription"
        )
    reused = db.scalar(select(models.Subscription).where(
        models.Subscription.payment_reference == payment_reference))
    if reused is not None:
        raise HTTPException(status_code=409, detail="Payment reference already used")

    bidder = get_bidder_company(db, current_user.id)
    
    if not bidder:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Create your shop profile first"
        )

    from elipsis_api import paystack
    try:
        verified = paystack.verify(payment_reference)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail="Could not verify payment") from exc
    if (verified.get("status") != "success"
            or verified.get("reference") != payment_reference):
        raise HTTPException(status_code=402, detail="Payment has not succeeded")

    plan = BIDDER_PLANS.get(tier)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tier. Choose: monthly, six_months, or yearly",
        )
    if not verified.get("dummy"):
        if (verified.get("currency") or "").upper() != "USD":
            raise HTTPException(status_code=402, detail="Payment currency must be USD")
        if int(verified.get("amount") or 0) < int(plan["price"] * 100):
            raise HTTPException(status_code=402, detail="Payment amount does not cover this plan")

    # Calculate expiration based on tier
    now = datetime.now()
    expires = now + timedelta(days=plan["days"])
    
    # Update subscription
    bidder.subscription_tier = tier
    bidder.subscription_status = "active"
    bidder.subscription_expires_at = expires.isoformat(timespec="seconds")
    
    # Create subscription record
    subscription = models.Subscription(
        bidder_company_id=bidder.id,
        tier=tier,
        start_date=now.isoformat(timespec="seconds"),
        end_date=expires.isoformat(timespec="seconds"),
        payment_reference=payment_reference,
        status="active",
    )
    
    db.add(subscription)
    db.commit()
    db.refresh(bidder)
    
    return {
        "subscription_status": "active",
        "tier": tier,
        "expires": expires.isoformat(),
        "message": f"Subscription activated successfully ({tier})"
    }
