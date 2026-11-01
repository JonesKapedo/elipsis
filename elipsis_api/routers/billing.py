"""Billing history, receipts, and subscription state."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from elipsis_api import catalog, models, paystack, permissions
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user, login_redirect, templates

router = APIRouter()

PURPOSE_LABELS = {
    "assessment": "Constraint Report",
    "pro": "Operator pass",
    "premium": "Operator pass",
    "facilitated": "Facilitated Report",
    "physical": "Physical assessment request",
    "switch_topup": "Switch top-up",
    "bidder_plan": "Partner plan",
}


def _order_for(db: Session, payment: models.Payment) -> models.Order | None:
    if not payment.reference:
        return None
    return db.scalar(select(models.Order).where(
        models.Order.provider_reference == payment.reference))


def _label(payment: models.Payment, order: models.Order | None) -> str:
    if order is not None:
        if order.description:
            return order.description
        try:
            return catalog.label(order.sku)
        except KeyError:
            pass
    return PURPOSE_LABELS.get(payment.purpose or "", "Elipsis payment")


def _amount(minor: int | None) -> str:
    return f"{(minor or 0) / 100:,.2f}"


@router.get("/billing")
def billing_page(request: Request, user=Depends(get_current_user),
                 db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    payments = db.scalars(
        select(models.Payment)
        .where(models.Payment.user_id == user.id)
        .order_by(models.Payment.id.desc())).all()
    orders = db.scalars(
        select(models.Order)
        .where(models.Order.user_id == user.id)
        .order_by(models.Order.id.desc())).all()
    entitlements = db.scalars(
        select(models.Entitlement)
        .where(models.Entitlement.user_id == user.id,
               models.Entitlement.status == "active")
        .order_by(models.Entitlement.id.desc())).all()
    rows = []
    for payment in payments:
        order = _order_for(db, payment)
        rows.append({
            "payment": payment,
            "order": order,
            "label": _label(payment, order),
            "amount": _amount(payment.amount_minor),
            "currency": payment.currency or catalog.CURRENCY,
            "status": payment.status or "pending",
        })
    prefs = db.get(models.UserPref, user.id)
    subscription = db.scalar(
        select(models.BillingSubscription)
        .where(models.BillingSubscription.user_id == user.id,
               models.BillingSubscription.status == "active")
        .order_by(models.BillingSubscription.id.desc()))
    return templates.TemplateResponse(request, "billing.html", {
        "user": user, "rows": rows, "orders": orders,
        "entitlements": entitlements, "subscription": subscription,
        "is_operator": permissions.is_pro_user(db, user),
        "operator_until": (prefs.pro_until if prefs and prefs.pro_until != "active"
                           else None),
        "sku_report": catalog.SKUS["report"],
        "sku_operator": catalog.SKUS["operator_monthly"],
        "cancelled": request.query_params.get("cancelled") == "1",
        "cancel_error": request.query_params.get("cancel") == "error",
    })


@router.post("/billing/cancel")
def cancel_renewal(request: Request, user=Depends(get_current_user),
                   db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    row = db.scalar(
        select(models.BillingSubscription)
        .where(models.BillingSubscription.user_id == user.id,
               models.BillingSubscription.status == "active")
        .order_by(models.BillingSubscription.id.desc()))
    if row is None or row.cancel_at_period_end:
        return RedirectResponse("/billing?cancelled=1", status_code=303)
    try:
        paystack.disable_subscription(
            row.provider_subscription_code or "", row.provider_email_token)
    except RuntimeError:
        return RedirectResponse("/billing?cancel=error", status_code=303)
    row.cancel_at_period_end = True
    row.updated_at = datetime.now(UTC).replace(tzinfo=None).isoformat(timespec="seconds")
    db.commit()
    return RedirectResponse("/billing?cancelled=1", status_code=303)


@router.get("/billing/receipt/{reference}")
def billing_receipt(reference: str, request: Request,
                    user=Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    payment = db.scalar(select(models.Payment).where(
        models.Payment.reference == reference))
    if payment is None or payment.user_id != user.id or payment.status != "success":
        return RedirectResponse("/billing", status_code=303)
    order = _order_for(db, payment)
    org = None
    if payment.related_id and payment.purpose in {"assessment", "facilitated"}:
        assessment = db.get(models.Assessment, payment.related_id)
        if assessment is not None:
            org = db.get(models.Organization, assessment.organization_id)
    return templates.TemplateResponse(request, "receipt.html", {
        "user": user, "payment": payment, "order": order, "org": org,
        "label": _label(payment, order),
        "amount": _amount(payment.amount_minor),
        "tax": _amount(order.tax_minor if order is not None else 0),
        "currency": payment.currency or catalog.CURRENCY,
        "paid_on": (payment.paid_at or payment.created_at or "")[:10],
    })
