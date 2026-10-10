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


@router.get("/admin")
def admin_pulse(request: Request, user=Depends(get_current_user),
                db: Session = Depends(get_db)):
    """Admin pulse overview — organisations, assessments, request pipeline."""
    if user is None:
        return login_redirect()
    if not _admin_ok(user):
        return _not_found(request, user)

    orgs_raw = db.scalars(
        select(models.Organization).order_by(models.Organization.id.desc()).limit(40)
    ).all()
    orgs = []
    for org in orgs_raw:
        a_count = db.scalar(
            select(func.count()).select_from(models.Assessment).where(
                models.Assessment.organization_id == org.id)
        ) or 0
        latest = db.scalar(
            select(models.Assessment)
            .where(models.Assessment.organization_id == org.id)
            .order_by(models.Assessment.id.desc())
            .limit(1)
        )
        orgs.append({
            "name": org.name,
            "industry": org.industry,
            "city": org.city,
            "country": org.country,
            "employee_count": org.employee_count,
            "assessment_count": int(a_count),
            "latest_at": getattr(latest, "started_at", None) or getattr(latest, "created_at", None) if latest else None,
        })

    assessments_raw = db.scalars(
        select(models.Assessment).order_by(models.Assessment.id.desc()).limit(25)
    ).all()
    assessments = []
    for a in assessments_raw:
        org = db.get(models.Organization, a.organization_id)
        dept = db.get(models.Department, a.department_id) if a.department_id else None
        score = None
        if hasattr(a, "readiness_index") and a.readiness_index is not None:
            try:
                score = round(float(a.readiness_index), 1)
            except (TypeError, ValueError):
                score = a.readiness_index
        assessments.append({
            "org_name": org.name if org else "—",
            "department": dept.name if dept else None,
            "status": a.status or "in_progress",
            "score": score,
            "created_at": getattr(a, "started_at", None) or getattr(a, "created_at", None),
        })

    reqs_raw = db.scalars(
        select(models.PhysicalAssessmentRequest).order_by(
            models.PhysicalAssessmentRequest.id.desc()).limit(20)
    ).all()
    requests = []
    for req in reqs_raw:
        org = db.get(models.Organization, req.organization_id)
        bid_count = db.scalar(
            select(func.count()).select_from(models.BidSubmission).where(
                models.BidSubmission.request_id == req.id)
        ) or 0
        requests.append({
            "title": req.title,
            "org_name": org.name if org else "—",
            "status": req.status,
            "bid_count": int(bid_count),
            "created_at": req.created_at,
        })

    all_orgs = db.scalar(select(func.count()).select_from(models.Organization)) or 0
    all_assess = db.scalar(select(func.count()).select_from(models.Assessment)) or 0
    all_req = db.scalars(select(models.PhysicalAssessmentRequest)).all()
    pending = sum(1 for r in all_req if r.status == "pending")
    published = sum(1 for r in all_req if r.status == "published")
    completed_a = db.scalar(
        select(func.count()).select_from(models.Assessment).where(
            models.Assessment.status == "completed")
    ) or 0
    bidders = 0
    try:
        bidders = db.scalar(select(func.count()).select_from(models.BidderCompany)) or 0
    except Exception:
        bidders = db.scalar(
            select(func.count()).select_from(models.User).where(
                models.User.user_type == "bidder")
        ) or 0

    stats = {
        "orgs": int(all_orgs),
        "assessments": int(all_assess),
        "pending_requests": pending,
        "published_requests": published,
        "bidders": int(bidders),
        "completed_assessments": int(completed_a),
    }
    max_v = max(stats["orgs"], stats["assessments"], stats["published_requests"], stats["pending_requests"], 1)
    bar_orgs = min(100, int(100 * stats["orgs"] / max_v))
    bar_assess = min(100, int(100 * stats["assessments"] / max_v))
    bar_pub = min(100, int(100 * stats["published_requests"] / max_v))
    bar_pend = min(100, int(100 * stats["pending_requests"] / max_v))

    return templates.TemplateResponse(
        request, "admin.html",
        {
            "user": user,
            "stats": stats,
            "orgs": orgs,
            "assessments": assessments,
            "requests": requests,
            "bar_orgs": bar_orgs,
            "bar_assess": bar_assess,
            "bar_pub": bar_pub,
            "bar_pend": bar_pend,
        },
    )


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
    active = [r for r in requests if r["status"] in ("pending", "verified", "published")]
    history = [r for r in requests if r["status"] not in ("pending", "verified", "published")]
    return templates.TemplateResponse(
        request, "admin_requests.html",
        {"user": user, "requests": requests, "active": active, "history": history, "stats": stats})


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
