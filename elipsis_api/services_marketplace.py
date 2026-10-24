"""Marketplace domain rules, entitlements, and access helpers."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from elipsis_api import models, permissions

REQUEST_PENDING = "pending_review"
REQUEST_APPROVED = "approved"
REQUEST_REJECTED = "rejected"
REQUEST_AWARDED = "awarded"
REQUEST_CLOSED = "closed"

BID_PENDING = "pending_review"
BID_APPROVED = "approved"
BID_AWARDED = "awarded"
BID_NOT_SELECTED = "not_selected"
BID_WITHDRAWN = "withdrawn"
BID_REJECTED = "rejected"

VERIFY_DRAFT = "draft"
VERIFY_SUBMITTED = "submitted"
VERIFY_MORE_INFO = "more_info"
VERIFY_APPROVED = "approved"
VERIFY_REJECTED = "rejected"
VERIFY_SUSPENDED = "suspended"
VERIFY_EXPIRED = "expired"

ACTIVE_REQUEST_STATUSES = (REQUEST_APPROVED, REQUEST_AWARDED)
VISIBLE_REQUEST_STATUSES = (REQUEST_APPROVED, REQUEST_AWARDED, REQUEST_CLOSED)
CONVERSATION_HOURS = 24
DEFAULT_SWITCHES = 3
TOPUP_SWITCHES = 3


def _now_dt() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def now_iso() -> str:
    return _now_dt().strftime("%Y-%m-%d %H:%M:%S")


def parse_dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value)).replace(tzinfo=None)
    except (TypeError, ValueError):
        return None


def calculate_company_size(employee_count: int | None, annual_revenue_avg: float | None) -> str:
    if employee_count is None and annual_revenue_avg is None:
        return "small"
    if employee_count is not None:
        if employee_count > 500:
            return "big"
        if employee_count >= 50:
            return "medium"
        return "small"
    if annual_revenue_avg is not None:
        if annual_revenue_avg > 50_000_000:
            return "big"
        if annual_revenue_avg >= 5_000_000:
            return "medium"
    return "small"


def get_company_badge_color(size: str) -> str:
    return {"small": "green", "medium": "maroon", "big": "red"}.get(size, "green")


def update_organization_size(db: Session, org_id: int):
    org = db.get(models.Organization, org_id)
    if org is None:
        return
    revenue_avg = None
    if org.annual_revenue_min is not None and org.annual_revenue_max is not None:
        revenue_avg = (org.annual_revenue_min + org.annual_revenue_max) / 2
    elif org.annual_revenue_min is not None:
        revenue_avg = org.annual_revenue_min
    elif org.annual_revenue_max is not None:
        revenue_avg = org.annual_revenue_max
    org.company_size = calculate_company_size(org.employee_count, revenue_avg)
    db.commit()


def get_user_organizations(db: Session, user_id: int) -> list[dict]:
    orgs = db.scalars(select(models.Organization).where(
        models.Organization.user_id == user_id
    )).all()
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
            "company_size": org.company_size or "small",
            "city": org.city,
            "country": org.country,
        }
        for org in orgs
    ]


def get_organization_departments(db: Session, org_id: int) -> list[dict]:
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


def bidder_slug(db: Session, name: str, bidder_id: int | None = None) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (name or "partner").lower()).strip("-") or "partner"
    base = base[:60].strip("-")
    candidate = base
    suffix = 2
    while True:
        existing = db.scalar(select(models.BidderCompany).where(
            models.BidderCompany.slug == candidate))
        if existing is None or existing.id == bidder_id:
            return candidate
        candidate = f"{base}-{suffix}"
        suffix += 1


def get_bidder_company(db: Session, user_id: int):
    return db.scalar(select(models.BidderCompany).where(
        models.BidderCompany.user_id == user_id
    ))


def is_bidder_subscribed(db: Session, user_id: int) -> bool:
    bidder = get_bidder_company(db, user_id)
    if not bidder or bidder.subscription_status != "active":
        return False
    expires = parse_dt(bidder.subscription_expires_at)
    return expires is None or expires >= _now_dt()


def is_bidder_approved(db: Session, user_id: int) -> bool:
    bidder = get_bidder_company(db, user_id)
    return bool(bidder and bidder.verification_status == VERIFY_APPROVED)


def is_active_bidder(db: Session, user_id: int) -> bool:
    return is_bidder_approved(db, user_id) and is_bidder_subscribed(db, user_id)


def bidder_verification_label(status: str | None) -> str:
    return {
        VERIFY_DRAFT: "Draft",
        VERIFY_SUBMITTED: "Under review",
        VERIFY_MORE_INFO: "More information needed",
        VERIFY_APPROVED: "Verified",
        VERIFY_REJECTED: "Not approved",
        VERIFY_SUSPENDED: "Suspended",
        VERIFY_EXPIRED: "Verification expired",
    }.get(status or "", "Not submitted")


def is_request_owner(db: Session, user, req: models.PhysicalAssessmentRequest) -> bool:
    if user is None or req is None:
        return False
    if getattr(req, "user_id", None) == user.id:
        return True
    return permissions.can_access_org(db, user, req.organization_id)


def can_view_request(db: Session, user, req: models.PhysicalAssessmentRequest) -> bool:
    if user is None or req is None:
        return False
    if permissions.is_admin(user):
        return True
    if is_request_owner(db, user, req):
        return True
    if req.status not in ACTIVE_REQUEST_STATUSES:
        return False
    return is_active_bidder(db, user.id)


def can_view_full_request(db: Session, user, req: models.PhysicalAssessmentRequest) -> bool:
    if user is None or req is None:
        return False
    if permissions.is_admin(user):
        return True
    if is_request_owner(db, user, req):
        return True
    return req.status in ACTIVE_REQUEST_STATUSES and is_active_bidder(db, user.id)


def can_view_contact_details(db: Session, user, req: models.PhysicalAssessmentRequest) -> bool:
    if user is None or req is None:
        return False
    if permissions.is_admin(user) or is_request_owner(db, user, req):
        return True
    if req.status != REQUEST_AWARDED or req.awarded_bid_id is None:
        return False
    bidder = get_bidder_company(db, user.id)
    if bidder is None:
        return False
    awarded = db.get(models.BidSubmission, req.awarded_bid_id)
    return bool(awarded and awarded.bidder_company_id == bidder.id)


def can_bid(db: Session, user, req: models.PhysicalAssessmentRequest) -> bool:
    if user is None or req is None:
        return False
    if (getattr(user, "user_type", "") or "") != "bidder":
        return False
    return req.status == REQUEST_APPROVED and is_active_bidder(db, user.id)


def can_view_bid(db: Session, user, bid: models.BidSubmission) -> bool:
    if user is None or bid is None:
        return False
    if permissions.is_admin(user):
        return True
    bidder = get_bidder_company(db, user.id)
    if bidder and bid.bidder_company_id == bidder.id:
        return True
    req = db.get(models.PhysicalAssessmentRequest, bid.request_id)
    if req is None or not is_request_owner(db, user, req):
        return False
    return bid.status in (BID_APPROVED, BID_AWARDED)


def can_view_conversation(db: Session, user, conv: models.MarketplaceConversation) -> bool:
    if user is None or conv is None:
        return False
    if user.id in (conv.requester_id, conv.bidder_user_id):
        return True
    return bool(conv.admin_involved and (permissions.is_admin(user)))


def visible_bid_status(bid: models.BidSubmission) -> bool:
    return (bid.status or "") in (BID_APPROVED, BID_AWARDED)


def assessment_is_unlocked(db: Session, user_id: int, assessment_id: int) -> bool:
    purchase = db.scalar(select(models.AssessmentPurchase).where(
        models.AssessmentPurchase.assessment_id == assessment_id,
        models.AssessmentPurchase.user_id == user_id,
        models.AssessmentPurchase.active.is_(True),
    ))
    if purchase is not None:
        return True
    user = db.get(models.User, user_id)
    return bool(user and permissions.is_pro_user(db, user))


def switches_remaining(req: models.PhysicalAssessmentRequest) -> int:
    granted = req.switches_granted if req.switches_granted is not None else DEFAULT_SWITCHES
    used = req.switches_used or 0
    return max(0, granted - used)


def conversation_deadline(now: datetime | None = None) -> str:
    base = now or _now_dt()
    return (base + timedelta(hours=CONVERSATION_HOURS)).strftime("%Y-%m-%d %H:%M:%S")


def notify_user(db: Session, user_id: int | None, event: str, title: str,
                body: str | None = None, url: str | None = None):
    if not user_id:
        return
    db.add(models.MarketplaceNotification(
        user_id=user_id, event=event, title=title, body=body, url=url,
        created_at=now_iso()))


def refresh_conversation(db: Session, conv: models.MarketplaceConversation) -> bool:
    """Lazily close a conversation 24 hours after its last message."""
    if conv is None or conv.status != "open":
        return False
    deadline = parse_dt(conv.closes_at)
    if deadline is None or deadline > _now_dt():
        return False
    conv.status = "closed"
    conv.closed_at = now_iso()
    conv.close_reason = "expired"
    notify_user(db, conv.requester_id, "conversation.closed",
                "Implementation conversation closed",
                "The 24-hour reply window has ended. Record the outcome to close the loop.",
                f"/marketplace/conversations/{conv.id}")
    notify_user(db, conv.bidder_user_id, "conversation.closed",
                "Implementation conversation closed",
                "The 24-hour reply window has ended. Record the outcome to close the loop.",
                f"/marketplace/conversations/{conv.id}")
    db.commit()
    return True


def request_conversation(db: Session, req: models.PhysicalAssessmentRequest):
    if req is None or req.awarded_bid_id is None:
        return None
    return db.scalar(select(models.MarketplaceConversation).where(
        models.MarketplaceConversation.bid_id == req.awarded_bid_id))


def switch_candidates(db: Session, req: models.PhysicalAssessmentRequest):
    if req is None or req.status != REQUEST_AWARDED:
        return []
    rows = db.scalars(select(models.BidSubmission).where(
        models.BidSubmission.request_id == req.id,
        models.BidSubmission.id != req.awarded_bid_id,
        models.BidSubmission.status.in_((BID_APPROVED, BID_NOT_SELECTED)),
    ).order_by(models.BidSubmission.id.asc())).all()
    out = []
    for bid in rows:
        bidder = db.get(models.BidderCompany, bid.bidder_company_id)
        if bidder is None or bidder.verification_status != VERIFY_APPROVED:
            continue
        if not is_bidder_subscribed(db, bidder.user_id):
            continue
        out.append((bid, bidder))
    return out


def switch_request(db: Session, req: models.PhysicalAssessmentRequest,
                   bid_id: int, actor_id: int):
    """Move an awarded request to another previously approved bid."""
    if req is None or req.status != REQUEST_AWARDED:
        raise ValueError("Only an awarded request can switch partners.")
    if switches_remaining(req) <= 0:
        raise ValueError("No switches remain. Add a three-switch top-up first.")
    new_bid = db.get(models.BidSubmission, bid_id)
    if new_bid is None or new_bid.request_id != req.id:
        raise ValueError("That bid does not belong to this request.")
    if new_bid.id == req.awarded_bid_id:
        raise ValueError("That partner already holds the award.")
    if new_bid.status not in (BID_APPROVED, BID_NOT_SELECTED):
        raise ValueError("Only an admin-approved bid can be selected.")
    new_bidder = db.get(models.BidderCompany, new_bid.bidder_company_id)
    if new_bidder is None or new_bidder.verification_status != VERIFY_APPROVED:
        raise ValueError("The selected bidder is not verified.")
    if not is_bidder_subscribed(db, new_bidder.user_id):
        raise ValueError("The selected bidder does not have an active subscription.")

    old_bid = db.get(models.BidSubmission, req.awarded_bid_id) if req.awarded_bid_id else None
    old_bidder = (db.get(models.BidderCompany, old_bid.bidder_company_id)
                  if old_bid is not None else None)
    old_conv = request_conversation(db, req)
    if old_conv is not None and old_conv.status == "open":
        old_conv.status = "closed"
        old_conv.closed_at = now_iso()
        old_conv.close_reason = "switched"
        old_conv.outcome = "no_agreement"

    if old_bid is not None:
        old_bid.status = BID_NOT_SELECTED
    new_bid.status = BID_AWARDED
    new_bid.awarded_at = now_iso()
    req.awarded_bid_id = new_bid.id
    req.awarded_at = now_iso()
    req.switches_used = (req.switches_used or 0) + 1
    req.preferred_bid_id = None
    req.preferred_at = None

    conv = db.scalar(select(models.MarketplaceConversation).where(
        models.MarketplaceConversation.bid_id == new_bid.id))
    if conv is None:
        conv = models.MarketplaceConversation(
            request_id=req.id, bid_id=new_bid.id, requester_id=req.user_id,
            bidder_user_id=new_bidder.user_id, status="open",
            admin_involved=False, opened_at=now_iso(), last_message_at=now_iso(),
            closes_at=conversation_deadline())
        db.add(conv)
        db.flush()
    else:
        conv.status = "open"
        conv.closed_at = None
        conv.close_reason = None
        conv.outcome = None
        conv.last_message_at = now_iso()
        conv.closes_at = conversation_deadline()

    if old_bidder is not None:
        notify_user(db, old_bidder.user_id, "request.switched",
                    "The client selected another partner",
                    f"{req.title} has moved to another implementation partner.",
                    f"/marketplace/{req.id}")
    notify_user(db, new_bidder.user_id, "request.switched",
                "You are now the selected partner",
                f"{req.title} was switched to your bid. The conversation is open.",
                f"/marketplace/conversations/{conv.id}")
    from elipsis_api.services_ops import record_audit
    record_audit(db, action="marketplace.request_switched",
                 organization_id=req.organization_id, assessment_id=req.assessment_id,
                 user_id=actor_id,
                 detail=f"request={req.id}; old_bid={old_bid.id if old_bid else None}; new_bid={new_bid.id}")
    db.commit()
    db.refresh(conv)
    from elipsis_api.services_email_events import send_user_event_sync
    if old_bidder is not None:
        send_user_event_sync(
            db, old_bidder.user_id, "request_switched_old",
            request_title=req.title, url=f"/marketplace/{req.id}")
    send_user_event_sync(
        db, new_bidder.user_id, "request_switched_new",
        request_title=req.title, url=f"/marketplace/conversations/{conv.id}")
    return conv
