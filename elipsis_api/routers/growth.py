"""Growth loops: assessment invites, WhatsApp/SMS nudges, and partner console."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from elipsis_api import (
    benchmarks,
    models,
    security,
    services,
    services_certification,
    services_digest,
    services_ops,
    services_outreach,
)
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user, login_redirect, templates

router = APIRouter()


def _not_found(request, user):
    return templates.TemplateResponse(request, "404.html", {"user": user}, status_code=404)


def _owned(db: Session, user, assessment_id: int):
    assessment = db.get(models.Assessment, assessment_id)
    if assessment is None or not services.can_access_org(db, user, assessment.organization_id):
        return None
    return assessment


def _orgs_for(db: Session, user):
    ids = None if services.is_admin(user) else services.visible_org_ids(db, user)
    return services.list_organizations(db, ids)


def _prefs(db: Session, user):
    prefs = db.get(models.UserPref, user.id)
    if prefs is None:
        prefs = models.UserPref(user_id=user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


def _campaign_for_assessment(db: Session, assessment: models.Assessment, user,
                             days: int = 14, min_respondents: int = 1,
                             allow_anonymous: bool = False) -> models.CollectCampaign:
    org = db.get(models.Organization, assessment.organization_id)
    token = security.new_token()[:24]
    deadline = f"{(date.today() + timedelta(days=max(1, min(90, days)))).isoformat()}T17:00"
    camp = models.CollectCampaign(
        token=token,
        organization_id=assessment.organization_id,
        department_id=assessment.department_id,
        created_by=user.id,
        title=f"{org.name if org else 'Organisation'} readiness pulse",
        deadline=deadline,
        min_respondents=max(1, min(500, min_respondents)),
        allow_anonymous=1 if allow_anonymous else 0,
        status="collecting",
        note="Created from an existing assessment for a re-assessment pulse.",
    )
    db.add(camp)
    db.commit()
    db.refresh(camp)
    services_ops.record_audit(
        db, action="invite.create", organization_id=assessment.organization_id,
        assessment_id=assessment.id, user_id=user.id, detail=f"campaign {token[:8]}")
    db.commit()
    return camp


@router.get("/assessment/{assessment_id}/invite")
def invite_page(assessment_id: int, request: Request,
                user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    assessment = _owned(db, user, assessment_id)
    if assessment is None:
        return _not_found(request, user)
    org = db.get(models.Organization, assessment.organization_id)
    dept = db.get(models.Department, assessment.department_id) if assessment.department_id else None
    token = (request.query_params.get("token") or "").strip()
    camp = db.get(models.CollectCampaign, token) if token else None
    if camp is not None and camp.organization_id != assessment.organization_id:
        camp = None
    share_url = ""
    message = ""
    whatsapp = ""
    sms = ""
    if camp is not None:
        share_url = str(request.base_url).rstrip("/") + f"/q/{camp.token}"
        message = services_outreach.assessment_invite_message(org, assessment, share_url, camp.deadline)
        whatsapp = services_outreach.whatsapp_url(request.query_params.get("phone"), message)
        sms = services_outreach.sms_url(request.query_params.get("phone"), message)
    return templates.TemplateResponse(request, "invite.html", {
        "user": user, "assessment": assessment, "organization": org, "department": dept,
        "campaign": camp, "share_url": share_url, "message": message,
        "whatsapp_url": whatsapp, "sms_url": sms,
        "phone": request.query_params.get("phone") or "",
        "is_pro": services.is_pro_user(db, user),
        "notifications": services_ops.notifications(db, user),
    })


@router.post("/assessment/{assessment_id}/invite")
def invite_create(assessment_id: int, request: Request,
                  days: int = Form(14), min_respondents: int = Form(1),
                  allow_anonymous: str = Form(""), phone: str = Form(""),
                  user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    assessment = _owned(db, user, assessment_id)
    if assessment is None:
        return _not_found(request, user)
    if not services.company_is_pro(db, assessment.organization_id, user):
        return RedirectResponse("/pro?locked=team", status_code=303)
    camp = _campaign_for_assessment(
        db, assessment, user, days=days, min_respondents=min_respondents,
        allow_anonymous=bool(allow_anonymous))
    return RedirectResponse(
        f"/assessment/{assessment_id}/invite?token={camp.token}&phone={phone}",
        status_code=303)


@router.get("/actions/{item_id}/nudge")
def nudge_page(item_id: int, request: Request,
               user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    item = db.get(models.RoadmapItem, item_id)
    if item is None:
        return _not_found(request, user)
    assessment = db.get(models.Assessment, item.assessment_id)
    if assessment is None or not services.can_access_org(db, user, assessment.organization_id):
        return _not_found(request, user)
    org = db.get(models.Organization, assessment.organization_id)
    phone = request.query_params.get("phone") or item.owner_phone or ""
    message = services_outreach.action_nudge_message(item, org.name if org else None)
    return templates.TemplateResponse(request, "nudge.html", {
        "user": user, "item": item, "assessment": assessment, "organization": org,
        "phone": phone, "message": message,
        "whatsapp_url": services_outreach.whatsapp_url(phone, message),
        "sms_url": services_outreach.sms_url(phone, message),
        "notifications": services_ops.notifications(db, user),
    })


@router.post("/actions/{item_id}/nudge")
def nudge_save(item_id: int, request: Request,
               phone: str = Form(""),
               user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    item = db.get(models.RoadmapItem, item_id)
    if item is None:
        return _not_found(request, user)
    assessment = db.get(models.Assessment, item.assessment_id)
    if assessment is None or not services.can_access_org(db, user, assessment.organization_id):
        return _not_found(request, user)
    item.owner_phone = services_outreach.normalize_phone(phone) or None
    db.commit()
    return RedirectResponse(f"/actions/{item_id}/nudge?phone={item.owner_phone or ''}", status_code=303)


@router.get("/partner")
def partner_console(request: Request, user=Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    orgs = _orgs_for(db, user)
    rows = []
    for org in orgs:
        overview = services.company_overview(db, org)
        latest = overview.get("latest")
        rows.append({
            "org": org,
            "latest": latest,
            "open_actions": len([
                a for a in services_ops.action_items(db, [org.id], status="open", limit=500)
            ]),
            "overdue": len([
                a for a in services_ops.action_items(db, [org.id], overdue_only=True, limit=500)
            ]),
        })
    return templates.TemplateResponse(request, "partner.html", {
        "user": user, "rows": rows, "prefs": _prefs(db, user),
        "notifications": services_ops.notifications(db, user),
    })


@router.post("/partner/brand")
def partner_brand(name: str = Form(""), footer: str = Form(""), accent: str = Form("#d9b45b"),
                  user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    prefs = _prefs(db, user)
    prefs.partner_name = (name or "").strip()[:80] or None
    prefs.partner_footer = (footer or "").strip()[:160] or None
    accent = (accent or "").strip()
    prefs.partner_accent = accent if accent.startswith("#") and len(accent) in (4, 7) else "#d9b45b"
    db.commit()
    return RedirectResponse("/partner?saved=1", status_code=303)


@router.get("/benchmarks")
def benchmark_page(request: Request, user=Depends(get_current_user),
                   db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    rows = []
    for org in _orgs_for(db, user):
        assessment = db.scalar(select(models.Assessment).where(
            models.Assessment.organization_id == org.id,
            models.Assessment.status == "completed",
        ).order_by(models.Assessment.id.desc()))
        result = services.compute(db, assessment.id)[1] if assessment else None
        benchmark = benchmarks.cohort_benchmark(
            db, org, score=result.get("readiness_index") if result else None)
        cert = services_certification.badge_for(org, assessment, result, benchmark) if result else None
        rows.append({
            "org": org, "latest": {"id": assessment.id} if assessment else None,
            "snapshot": services_certification.cohort_snapshot(db, org),
            "benchmark": benchmark, "certification": cert,
        })
    return templates.TemplateResponse(request, "benchmarks.html", {
        "user": user, "rows": rows,
        "notifications": services_ops.notifications(db, user),
    })


@router.get("/assessment/{assessment_id}/badge")
def badge_page(assessment_id: int, request: Request,
               user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    assessment = _owned(db, user, assessment_id)
    if assessment is None:
        return _not_found(request, user)
    _, result = services.compute(db, assessment_id)
    if result is None:
        return RedirectResponse(f"/assessment/{assessment_id}/step/1", status_code=303)
    org = db.get(models.Organization, assessment.organization_id)
    benchmark = benchmarks.cohort_benchmark(
        db, org, score=result.get("readiness_index"))
    cert = services_certification.badge_for(org, assessment, result, benchmark)
    base = str(request.base_url).rstrip("/")
    verify_url = f"{base}/verify/{cert['token']}" if cert.get("token") else ""
    return templates.TemplateResponse(request, "badge.html", {
        "user": user, "assessment": assessment, "organization": org,
        "result": result, "benchmark": benchmark, "certification": cert,
        "verify_url": verify_url,
        "embed_code": f'<a href="{verify_url}"><img src="{base}/verify/{cert["token"]}.svg" alt="Elipsis readiness badge" width="360"></a>' if verify_url else "",
        "notifications": services_ops.notifications(db, user),
    })


@router.get("/verify/{token}.svg")
def verify_svg(token: str):
    payload = services_certification.verify_token(token)
    if payload is None:
        return Response(status_code=404)
    return Response(
        content=services_certification.badge_svg(payload),
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/notifications")
def notification_centre(request: Request, user=Depends(get_current_user),
                        db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    notes = services_ops.notifications(db, user)
    read = services_ops.read_fingerprints(db, user)
    for note in notes:
        note["fingerprint"] = services_ops.notification_fingerprint(note)
        note["read"] = note["fingerprint"] in read
    prefs = _prefs(db, user)
    return templates.TemplateResponse(request, "notifications.html", {
        "user": user, "notifications": notes, "prefs": prefs,
        "unread": sum(1 for n in notes if not n["read"]),
    })


@router.post("/notifications/read")
async def notification_read(request: Request, user=Depends(get_current_user),
                            db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    form = await request.form()
    fingerprints = [str(v) for v in form.getlist("fingerprint")]
    services_ops.mark_notifications_read(db, user, fingerprints)
    return RedirectResponse("/notifications?read=1", status_code=303)


@router.post("/notifications/digest")
def notification_digest(frequency: str = Form("weekly"),
                        user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    prefs = _prefs(db, user)
    prefs.digest_frequency = frequency if frequency in {"off", "daily", "weekly"} else "weekly"
    db.commit()
    return RedirectResponse("/notifications?digest=saved", status_code=303)


@router.post("/notifications/digest/send")
async def notification_digest_send(request: Request, user=Depends(get_current_user),
                                   db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    result = await services_digest.send_digest(
        db, user, base_url=str(request.base_url).rstrip("/"), force=True)
    key = "sent" if result.get("sent") else result.get("reason", "not_sent")
    return RedirectResponse(f"/notifications?digest={key}", status_code=303)


@router.get("/verify/{token}")
def verify_page(token: str, request: Request):
    payload = services_certification.verify_token(token)
    if payload is None:
        return templates.TemplateResponse(request, "404.html", {"user": None}, status_code=404)
    return templates.TemplateResponse(request, "verify.html", {
        "user": None, "payload": payload,
    })
