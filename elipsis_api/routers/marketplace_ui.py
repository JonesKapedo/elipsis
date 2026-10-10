"""Server-rendered marketplace + admin request desk pages."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from elipsis_api import models, services
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user, login_redirect, templates

router = APIRouter()


def _not_found(request, user):
    return templates.TemplateResponse(request, "404.html", {"user": user}, status_code=404)


def _admin_ok(user) -> bool:
    if user is None:
        return False
    if services.is_admin(user):
        return True
    if getattr(user, "is_admin", False):
        return True
    return (getattr(user, "role", "") or "") == "admin"


@router.get("/marketplace")
def marketplace_list(request: Request, user=Depends(get_current_user),
                     db: Session = Depends(get_db)):
    """Public marketplace of published engagement requests."""
    rows = db.scalars(
        select(models.PhysicalAssessmentRequest)
        .where(models.PhysicalAssessmentRequest.status == "published")
        .order_by(models.PhysicalAssessmentRequest.id.desc())
    ).all()
    requests = []
    for req in rows:
        org = db.get(models.Organization, req.organization_id)
        bid_count = db.scalar(
            select(func.count()).select_from(models.BidSubmission).where(
                models.BidSubmission.request_id == req.id)
        ) or 0
        requests.append({
            "id": req.id,
            "title": req.title,
            "message": req.message,
            "requirements": req.requirements,
            "status": req.status,
            "created_at": req.created_at,
            "bid_count": int(bid_count),
            "organization": org,
        })
    return templates.TemplateResponse(
        request, "marketplace.html",
        {"user": user, "requests": requests, "count": len(requests)})


@router.get("/marketplace/{request_id}")
def marketplace_detail(request_id: int, request: Request,
                       user=Depends(get_current_user), db: Session = Depends(get_db)):
    req = db.get(models.PhysicalAssessmentRequest, request_id)
    if req is None:
        return _not_found(request, user)
    if req.status not in ("published", "in_progress", "completed") and not _admin_ok(user):
        return _not_found(request, user)
    org = db.get(models.Organization, req.organization_id)
    documents = list(db.scalars(
        select(models.RequestDocument).where(
            models.RequestDocument.request_id == request_id)
    ).all())
    bid_count = db.scalar(
        select(func.count()).select_from(models.BidSubmission).where(
            models.BidSubmission.request_id == request_id)
    ) or 0
    return templates.TemplateResponse(
        request, "marketplace_detail.html",
        {"user": user, "request_row": req, "organization": org,
         "documents": documents, "bid_count": int(bid_count)})


@router.get("/admin/requests")
def admin_requests_page(request: Request, user=Depends(get_current_user),
                        db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not _admin_ok(user):
        return _not_found(request, user)
    status_filter = (request.query_params.get("status") or "").strip()
    query = select(models.PhysicalAssessmentRequest).order_by(
        models.PhysicalAssessmentRequest.id.desc())
    if status_filter:
        query = query.where(models.PhysicalAssessmentRequest.status == status_filter)
    rows = db.scalars(query).all()
    requests = []
    for req in rows:
        org = db.get(models.Organization, req.organization_id)
        bid_count = db.scalar(
            select(func.count()).select_from(models.BidSubmission).where(
                models.BidSubmission.request_id == req.id)
        ) or 0
        requests.append({
            "id": req.id,
            "title": req.title,
            "message": req.message,
            "status": req.status,
            "created_at": req.created_at,
            "bid_count": int(bid_count),
            "organization": org,
        })
    all_rows = db.scalars(select(models.PhysicalAssessmentRequest)).all()
    stats = {
        "total": len(all_rows),
        "pending": sum(1 for r in all_rows if r.status == "pending"),
        "published": sum(1 for r in all_rows if r.status == "published"),
        "rejected": sum(1 for r in all_rows if r.status == "rejected"),
    }
    return templates.TemplateResponse(
        request, "admin_requests.html",
        {"user": user, "requests": requests, "stats": stats})


@router.post("/admin/requests/{request_id}/publish")
def admin_publish_request(request_id: int, request: Request,
                          user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not _admin_ok(user):
        return _not_found(request, user)
    req = db.get(models.PhysicalAssessmentRequest, request_id)
    if req is None:
        return _not_found(request, user)
    if req.status not in ("pending", "verified"):
        return RedirectResponse("/admin/requests", status_code=303)
    req.status = "published"
    if hasattr(req, "published_at"):
        from elipsis_api.services_core import _now
        req.published_at = _now()
    db.commit()
    return RedirectResponse("/admin/requests", status_code=303)


@router.post("/admin/requests/{request_id}/reject")
def admin_reject_request(request_id: int, request: Request,
                         reason: str = Form(""),
                         user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not _admin_ok(user):
        return _not_found(request, user)
    req = db.get(models.PhysicalAssessmentRequest, request_id)
    if req is None:
        return _not_found(request, user)
    if req.status not in ("pending", "verified"):
        return RedirectResponse("/admin/requests", status_code=303)
    req.status = "rejected"
    note = (reason or "").strip()[:500]
    if note:
        req.admin_notes = f"Rejected: {note}"
    db.commit()
    return RedirectResponse("/admin/requests", status_code=303)
