"""Order and entitlement primitives.

`AssessmentPurchase` remains the compatibility record for the original $499
unlock. New commerce writes an `Order` and an `Entitlement` so access no longer
depends on how the buyer paid.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from elipsis_api import catalog, models


def _now() -> str:
    from elipsis_api.models import _now as model_now

    return model_now()


def open_order(
    db: Session,
    *,
    user_id: int,
    sku: str,
    assessment_id: int | None = None,
    organization_id: int | None = None,
    provider: str = "paystack",
    provider_reference: str | None = None,
    amount_minor: int | None = None,
    description: str | None = None,
) -> models.Order:
    """Create a pending order for a catalog SKU."""
    meta = catalog.SKUS.get(sku, {})
    order = models.Order(
        user_id=user_id,
        assessment_id=assessment_id,
        organization_id=organization_id,
        sku=sku,
        description=description or meta.get("label"),
        amount_minor=(amount_minor if amount_minor is not None
                      else catalog.amount_minor(sku)),
        currency="USD",
        status="pending",
        provider=provider,
        provider_reference=provider_reference,
    )
    db.add(order)
    db.flush()
    return order


def order_for_reference(db: Session, reference: str) -> models.Order | None:
    if not reference:
        return None
    return db.scalar(select(models.Order).where(
        models.Order.provider_reference == reference))


def grant(
    db: Session,
    *,
    user_id: int,
    sku: str,
    order_id: int | None = None,
    assessment_id: int | None = None,
    organization_id: int | None = None,
    kind: str | None = None,
    expires_at: str | None = None,
) -> models.Entitlement:
    """Grant access once; repeated calls return the active entitlement."""
    stmt = select(models.Entitlement).where(
        models.Entitlement.user_id == user_id,
        models.Entitlement.sku == sku,
        models.Entitlement.status == "active",
    )
    stmt = (stmt.where(models.Entitlement.assessment_id.is_(None))
            if assessment_id is None
            else stmt.where(models.Entitlement.assessment_id == assessment_id))
    existing = db.scalar(stmt)
    if existing is not None:
        return existing
    entitlement = models.Entitlement(
        user_id=user_id,
        order_id=order_id,
        assessment_id=assessment_id,
        organization_id=organization_id,
        sku=sku,
        kind=kind or catalog.SKUS.get(sku, {}).get("kind") or sku,
        status="active",
        expires_at=expires_at,
    )
    db.add(entitlement)
    db.flush()
    return entitlement


def has(
    db: Session,
    user_id: int,
    sku: str,
    assessment_id: int | None = None,
) -> bool:
    stmt = select(models.Entitlement.id).where(
        models.Entitlement.user_id == user_id,
        models.Entitlement.sku == sku,
        models.Entitlement.status == "active",
    )
    if assessment_id is not None:
        stmt = stmt.where(models.Entitlement.assessment_id == assessment_id)
    return db.scalar(stmt) is not None


def settle_order(
    db: Session,
    payment: models.Payment,
    *,
    sku: str,
    kind: str | None = None,
) -> models.Entitlement | None:
    """Mark an assessment-linked order paid and grant its entitlement."""
    if not payment.user_id or not payment.related_id:
        return None
    assessment = db.get(models.Assessment, payment.related_id)
    if assessment is None:
        return None
    order = order_for_reference(db, payment.reference)
    if order is None:
        order = open_order(
            db,
            user_id=payment.user_id,
            sku=sku,
            assessment_id=assessment.id,
            organization_id=assessment.organization_id,
            provider="paystack",
            provider_reference=payment.reference,
            amount_minor=payment.amount_minor or catalog.amount_minor(sku),
            description=f"{catalog.label(sku)} for assessment {assessment.id}",
        )
    order.status = "paid"
    order.paid_at = _now()
    return grant(
        db,
        user_id=payment.user_id,
        sku=sku,
        order_id=order.id,
        assessment_id=assessment.id,
        organization_id=assessment.organization_id,
        kind=kind or sku,
    )


def settle_report(db: Session, payment: models.Payment) -> models.Entitlement | None:
    return settle_order(db, payment, sku="report", kind="report")


def settle_facilitated(db: Session, payment: models.Payment) -> models.Entitlement | None:
    """Facilitated includes the report, so grant both against one order."""
    entitlement = settle_order(db, payment, sku="facilitated", kind="facilitated")
    order = order_for_reference(db, payment.reference)
    if entitlement is not None and order is not None and payment.related_id:
        assessment = db.get(models.Assessment, payment.related_id)
        assessment_id = assessment.id if assessment else None
        organization_id = assessment.organization_id if assessment else None
        grant(
            db,
            user_id=payment.user_id,
            sku="report",
            order_id=order.id,
            assessment_id=assessment_id,
            organization_id=organization_id,
            kind="report",
        )
    return entitlement


def has_facilitated(db: Session, user_id: int, assessment_id: int) -> bool:
    return has(db, user_id, "facilitated", assessment_id)
