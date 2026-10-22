"""Private company workspace: team invites, room, decisions, desk, and brief."""

from __future__ import annotations

import secrets
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from elipsis_api import (
    auth_extra,
    departments,
    models,
    ratelimit,
    services,
    services_ops,
    services_room,
    services_success,
)
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user, login_redirect, templates
from elipsis_api.routers.pages import _set_session_cookie

router = APIRouter()

SECTIONS = services_room.SECTIONS


def _not_found(request: Request | None, user):
    if request is None:
        return RedirectResponse("/company", status_code=303)
    return templates.TemplateResponse(request, "404.html", {"user": user}, status_code=404)


def _org(db: Session, user, organization_id: int):
    if not services.can_access_org(db, user, organization_id):
        return None
    return db.get(models.Organization, organization_id)


def _premium_redirect(organization_id: int):
    return RedirectResponse(
        f"/pro?locked=team&org={organization_id}", status_code=303)


def _msg(path: str, key: str, message: str):
    return RedirectResponse(f"{path}?{key}={quote(message)}", status_code=303)


def _context(db: Session, user, org: models.Organization) -> dict:
    role = services.org_role(db, user, org.id)
    is_pro = services.company_is_pro(db, org.id, user)
    return {
        "user": user, "org": org, "organization": org, "role": role,
        "role_label": services.ROLE_LABELS.get(role, "Member"),
        "is_pro": is_pro,
        "can_manage": services.can_manage_org(db, user, org.id),
        "can_contribute": services.can_contribute_org(db, user, org.id),
        "members": services_room.member_rows(db, org.id),
        "branding": services_room.branding(org),
        "notifications": services_ops.notifications(db, user),
        "departments": departments.DEPARTMENTS,
    }


def _touch(db: Session, user, org_id: int) -> None:
    link = services.org_membership(db, user, org_id)
    if link is None:
        return
    stamp = services_room._now()
    if not link.last_seen_at or link.last_seen_at[:10] != stamp[:10]:
        link.last_seen_at = stamp
        db.commit()


@router.get("/company/{organization_id}")
def company_workspace(organization_id: int, request: Request,
                      user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    org = _org(db, user, organization_id)
    if org is None:
        return _not_found(request, user)
    _touch(db, user, org.id)
    context = _context(db, user, org)
    context.update({
        "pulse": services_room.pulse(db, org.id),
        "schedule": services_room.desk(db, org, 14),
        "activity": services_room.activity(db, org.id, 8),
        "decisions": services_room.decisions(db, org.id, 6),
        "joined": request.query_params.get("joined") == "1",
        "locked": request.query_params.get("locked"),
        "company_context": services.company_context(org),
    })
    return templates.TemplateResponse(request, "company_room.html", context)


@router.get("/company/{organization_id}/desk")
def company_desk(organization_id: int, request: Request,
                 user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    org = _org(db, user, organization_id)
    if org is None:
        return _not_found(request, user)
    if not services.company_is_pro(db, org.id, user):
        return _premium_redirect(org.id)
    context = _context(db, user, org)
    context.update({"schedule": services_room.desk(db, org, 21), "pulse": services_room.pulse(db, org.id),
                    "company_context": services.company_context(org)})
    return templates.TemplateResponse(request, "company_desk.html", context)


@router.get("/company/{organization_id}/discussion")
def company_discussion(organization_id: int, request: Request,
                       user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    org = _org(db, user, organization_id)
    if org is None:
        return _not_found(request, user)
    if not services.company_is_pro(db, org.id, user):
        return _premium_redirect(org.id)
    context = _context(db, user, org)
    context.update({"posts": services_room.feed(db, org.id), "tags": services_room.POST_TAGS,
                    "message": request.query_params.get("message"),
                    "error": request.query_params.get("error"),
                    "company_context": services.company_context(org)})
    return templates.TemplateResponse(request, "company_discussion.html", context)


@router.get("/company/{organization_id}/decisions")
def company_decisions(organization_id: int, request: Request,
                      user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    org = _org(db, user, organization_id)
    if org is None:
        return _not_found(request, user)
    if not services.company_is_pro(db, org.id, user):
        return _premium_redirect(org.id)
    context = _context(db, user, org)
    context.update({
        "decisions": services_room.decisions(db, org.id, 100),
        "states": services_room.DECISION_STATES,
        "assessments": services.company_overview(db, org)["rows"],
        "message": request.query_params.get("message"),
        "error": request.query_params.get("error"),
        "company_context": services.company_context(org),
    })
    return templates.TemplateResponse(request, "company_decisions.html", context)


@router.get("/company/{organization_id}/brief")
def company_brief(organization_id: int, request: Request,
                  user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    org = _org(db, user, organization_id)
    if org is None:
        return _not_found(request, user)
    if not services.company_is_pro(db, org.id, user):
        return _premium_redirect(org.id)
    context = _context(db, user, org)
    context.update({
        "pulse": services_room.pulse(db, org.id),
        "schedule": services_room.desk(db, org, 14),
        "decisions": services_room.decisions(db, org.id, 8),
        "activity": services_room.activity(db, org.id, 10),
        "company_context": services.company_context(org),
        "brief": True,
    })
    return templates.TemplateResponse(request, "company_brief.html", context)


@router.get("/company/{organization_id}/schedule.ics")
def company_calendar(organization_id: int, request: Request,
                     user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    org = _org(db, user, organization_id)
    if org is None:
        return _not_found(request, user)
    if not services.company_is_pro(db, org.id, user):
        return _premium_redirect(org.id)
    body = services_room.calendar(org, services_room.desk(db, org, 60))
    return Response(body, media_type="text/calendar; charset=utf-8",
                    headers={"Content-Disposition":
                             f'attachment; filename="{org.id}-elipsis-desk.ics"'})


@router.post("/company/{organization_id}/settings")
def company_workspace_settings(organization_id: int,
                               accent_color: str = Form("#b45309"),
                               report_footer: str = Form(""),
                               report_cover_note: str = Form(""),
                               week_start: str = Form("monday"),
                               huddle_day: str = Form("monday"),
                               huddle_time: str = Form("08:30"),
                               next: str = Form(""),
                               user=Depends(get_current_user),
                               db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    org = _org(db, user, organization_id)
    if org is None:
        return _not_found(request=None, user=user)
    if not services.can_manage_org(db, user, org.id):
        return _msg(f"/company/{org.id}", "error", "Only owners and managers can change company settings.")
    ok, message = services_room.update_company_settings(
        db, org, user.id, accent_color=accent_color,
        report_footer=report_footer, report_cover_note=report_cover_note,
        week_start=week_start, huddle_day=huddle_day, huddle_time=huddle_time)
    if next == "/settings":
        if ok:
            return RedirectResponse("/settings?company=saved", status_code=303)
        return _msg("/settings", "company_error", message)
    return _msg(f"/company/{org.id}", "message" if ok else "error", message)


@router.post("/company/{organization_id}/posts")
def company_post(organization_id: int, body: str = Form(...), tag: str = Form("update"),
                 user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    org = _org(db, user, organization_id)
    if org is None:
        return _not_found(request=None, user=user)
    if not services.company_is_pro(db, org.id, user):
        return _premium_redirect(org.id)
    if not services.can_contribute_org(db, user, org.id):
        return _msg(f"/company/{org.id}/discussion", "error", "Your role can read but not post.")
    ok, message = services_room.create_post(db, org.id, user.id, body, tag)
    return _msg(f"/company/{org.id}/discussion", "message" if ok else "error", message)


@router.post("/company/{organization_id}/posts/{post_id}/reply")
def company_reply(organization_id: int, post_id: int, body: str = Form(...),
                  user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    org = _org(db, user, organization_id)
    post = db.get(models.CompanyPost, post_id)
    if org is None or post is None or post.organization_id != org.id:
        return _not_found(request=None, user=user)
    if not services.can_contribute_org(db, user, org.id):
        return _msg(f"/company/{org.id}/discussion", "error", "Your role can read but not reply.")
    ok, message = services_room.create_reply(db, post, user.id, body)
    return _msg(f"/company/{org.id}/discussion", "message" if ok else "error", message)


@router.post("/company/{organization_id}/posts/{post_id}/pin")
def company_pin(organization_id: int, post_id: int,
                user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    org = _org(db, user, organization_id)
    post = db.get(models.CompanyPost, post_id)
    if org is None or post is None or post.organization_id != org.id:
        return _not_found(request=None, user=user)
    if not services.can_manage_org(db, user, org.id):
        return _msg(f"/company/{org.id}/discussion", "error", "Only managers can pin posts.")
    services_room.toggle_pin(db, post, user.id)
    return _msg(f"/company/{org.id}/discussion", "message", "Pin updated.")


@router.post("/company/{organization_id}/decisions")
def company_decision_add(organization_id: int, title: str = Form(...),
                         detail: str = Form(""), owner_id: str = Form(""),
                         owner_name: str = Form(""), due_date: str = Form(""),
                         assessment_id: str = Form(""),
                         user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    org = _org(db, user, organization_id)
    if org is None:
        return _not_found(request=None, user=user)
    if not services.can_contribute_org(db, user, org.id):
        return _msg(f"/company/{org.id}/decisions", "error", "Your role can read but not record decisions.")
    owner = int(owner_id) if owner_id.strip().isdigit() else None
    link = int(assessment_id) if assessment_id.strip().isdigit() else None
    if link is not None:
        assessment = db.get(models.Assessment, link)
        if assessment is None or assessment.organization_id != org.id:
            link = None
    ok, message = services_room.create_decision(
        db, org.id, user.id, title=title, detail=detail, owner_id=owner,
        owner_name=owner_name, due_date=due_date, assessment_id=link)
    return _msg(f"/company/{org.id}/decisions", "message" if ok else "error", message)


@router.post("/company/{organization_id}/decisions/{decision_id}/status")
def company_decision_status(organization_id: int, decision_id: int,
                            status: str = Form("open"),
                            user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    org = _org(db, user, organization_id)
    row = db.get(models.CompanyDecision, decision_id)
    if org is None or row is None or row.organization_id != org.id:
        return _not_found(request=None, user=user)
    if not services.can_contribute_org(db, user, org.id):
        return _msg(f"/company/{org.id}/decisions", "error", "Your role cannot change decisions.")
    services_room.update_decision(db, row, user.id, status)
    return _msg(f"/company/{org.id}/decisions", "message", "Decision updated.")


@router.post("/assessment/{assessment_id}/notes")
def assessment_note(assessment_id: int, section: str = Form("Overall"),
                    body: str = Form(...), user=Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    assessment = db.get(models.Assessment, assessment_id)
    if assessment is None or not services.can_access_org(db, user, assessment.organization_id):
        return _not_found(request=None, user=user)
    if not services.can_contribute_org(db, user, assessment.organization_id):
        return _msg(f"/assessment/{assessment.id}/results", "note_error",
                    "Your role can read but not annotate.")
    section = section if section in SECTIONS else "Overall"
    ok, message = services_room.add_note(db, assessment, user.id, section, body)
    return _msg(f"/assessment/{assessment.id}/results",
                "note" if ok else "note_error", message)


@router.get("/company/{organization_id}/invite")
def invite_page(organization_id: int, request: Request,
                user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    org = _org(db, user, organization_id)
    if org is None:
        return _not_found(request, user)
    if not services.company_is_pro(db, org.id, user):
        return _premium_redirect(org.id)
    if not services.can_manage_org(db, user, org.id):
        return _msg(f"/company/{org.id}/team", "error", "Only owners and managers can invite people.")
    context = _context(db, user, org)
    context.update({
        "invites": services_room.invites(db, org.id),
        "invite_days": services_room.INVITE_DAYS,
        "created": services_room.find_invite(db, request.query_params.get("token") or ""),
        "message": request.query_params.get("message"),
        "error": request.query_params.get("error"),
        "roles": {k: v for k, v in services.ROLE_LABELS.items() if k != "owner"},
        "base_url": str(request.base_url).rstrip("/"),
    })
    return templates.TemplateResponse(request, "company_invite.html", context)


@router.post("/company/{organization_id}/invite")
def invite_create(organization_id: int, email: str = Form(""), role: str = Form("manager"),
                  title: str = Form(""), department: str = Form(""),
                  note: str = Form(""), days: int = Form(7), max_uses: int = Form(1),
                  user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    org = _org(db, user, organization_id)
    if org is None:
        return _not_found(request=None, user=user)
    if not services.company_is_pro(db, org.id, user):
        return _premium_redirect(org.id)
    if not services.can_manage_org(db, user, org.id):
        return _msg(f"/company/{org.id}/team", "error", "Only owners and managers can invite people.")
    invite, error = services_room.create_invite(
        db, org.id, user.id, email=email, role=role, title=title,
        department=department, note=note, days=days, max_uses=max_uses)
    if invite is None:
        return _msg(f"/company/{org.id}/invite", "error", error or "Could not create invite.")
    return _msg(f"/company/{org.id}/invite", "message",
                "Invite link ready. Copy it and send it privately.")


@router.post("/company/{organization_id}/invite/{invite_id}/revoke")
def invite_revoke(organization_id: int, invite_id: int,
                  user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    org = _org(db, user, organization_id)
    invite = db.get(models.OrgInvite, invite_id)
    if org is None or invite is None or invite.organization_id != org.id:
        return _not_found(request=None, user=user)
    if not services.can_manage_org(db, user, org.id):
        return _msg(f"/company/{org.id}/team", "error", "Only owners and managers can revoke invites.")
    services_room.revoke_invite(db, invite, user.id)
    return _msg(f"/company/{org.id}/invite", "message", "Invite revoked.")


@router.get("/invite/{token}")
def invite_accept_page(token: str, request: Request,
                       user=Depends(get_current_user), db: Session = Depends(get_db)):
    invite = services_room.find_invite(db, token)
    org = db.get(models.Organization, invite.organization_id) if invite else None
    error = services_room.invite_error(invite)
    if invite and org and error and user is not None:
        membership = services.org_membership(db, user, org.id)
        if membership is not None and invite.uses:
            error = ""
    return templates.TemplateResponse(request, "invite_accept.html", {
        "user": user, "invite": invite, "org": org, "error": error,
        "message": request.query_params.get("message"),
        "departments": departments.DEPARTMENTS,
        "form": {"name": (user.name if user else "") or "",
                 "email": (invite.email if invite and invite.email else
                           ((user.email if user else "") or ""))},
    })


@router.post("/invite/{token}")
async def invite_accept(token: str, request: Request,
                        name: str = Form(""), email: str = Form(""),
                        password: str = Form(""), password2: str = Form(""),
                        accept_terms: str = Form(""),
                        db: Session = Depends(get_db)):
    ratelimit.enforce(request, "invite", limit=10, window=60)
    invite = services_room.find_invite(db, token)
    org = db.get(models.Organization, invite.organization_id) if invite else None
    error = services_room.invite_error(invite)
    if invite is None or org is None or error:
        return templates.TemplateResponse(request, "invite_accept.html", {
            "user": None, "invite": invite, "org": org,
            "error": error or "This invite is not available.",
            "form": {"name": name, "email": email}, "departments": departments.DEPARTMENTS,
        }, status_code=400)
    current = get_current_user(request, db)
    if current is not None:
        ok, message = services_room.accept_invite(db, invite, current)
        if not ok:
            return templates.TemplateResponse(request, "invite_accept.html", {
                "user": current, "invite": invite, "org": org, "error": message,
                "form": {"name": current.name or "", "email": current.email},
                "departments": departments.DEPARTMENTS}, status_code=400)
        return RedirectResponse(f"/company/{org.id}?joined=1", status_code=303)
    email = (email or invite.email or "").strip().lower()
    if invite.email and email != invite.email.lower():
        error = f"This invite is reserved for {invite.email}."
    elif password != password2:
        error = "Passwords do not match."
    elif len(password or "") < 8:
        error = "Use at least eight characters for the password."
    elif not accept_terms:
        error = "Accept the terms to create an account."
    if error:
        return templates.TemplateResponse(request, "invite_accept.html", {
            "user": None, "invite": invite, "org": org, "error": error,
            "form": {"name": name, "email": email}, "departments": departments.DEPARTMENTS,
        }, status_code=400)
    existing = db.scalar(select(models.User).where(models.User.email == email))
    if existing is not None:
        return templates.TemplateResponse(request, "invite_accept.html", {
            "user": None, "invite": invite, "org": org,
            "error": "An account with this email already exists. Sign in to accept.",
            "form": {"name": name, "email": email}, "departments": departments.DEPARTMENTS,
        }, status_code=400)
    try:
        account = auth_extra.register_user(db, email, password, name=name)
    except ValueError as exc:
        return templates.TemplateResponse(request, "invite_accept.html", {
            "user": None, "invite": invite, "org": org, "error": str(exc),
            "form": {"name": name, "email": email}, "departments": departments.DEPARTMENTS,
        }, status_code=400)
    services_success.record_acceptance(
        db, account, document="terms",
        version=services_success.LEGAL_VERSION, request=request)
    from elipsis_api.services_email import is_email_configured, send_email
    if is_email_configured():
        account.email_verified = False
        account.verification_token = secrets.token_urlsafe(32)
        db.commit()
        base = str(request.base_url).rstrip("/")
        await send_email(
            account.email, "Verify your Elipsis email",
            f'<p>Confirm your email: <a href="{base}/verify-email?token={account.verification_token}">Verify email</a></p>')
    ok, message = services_room.accept_invite(db, invite, account)
    if not ok:
        return templates.TemplateResponse(request, "invite_accept.html", {
            "user": None, "invite": invite, "org": org, "error": message,
            "form": {"name": name, "email": email}, "departments": departments.DEPARTMENTS,
        }, status_code=400)
    session = services.create_session(db, account.id)
    response = RedirectResponse(f"/company/{org.id}?joined=1", status_code=303)
    _set_session_cookie(response, session)
    return response
