"""Customer-facing service, support, trust and data-rights routes."""

from __future__ import annotations

import html
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from elipsis_api import models, ratelimit, services, services_success
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user, login_redirect, templates
from elipsis_api.routers.admin import require_admin

router = APIRouter()


def _prefs(db: Session, user):
    if user is None:
        return None
    return db.get(models.UserPref, user.id)


def _zone(db: Session, user) -> str:
    prefs = _prefs(db, user)
    return (prefs.timezone if prefs and prefs.timezone else "UTC")


def _base(db: Session, user) -> dict:
    return {
        "user": user,
        "timezone": _zone(db, user),
        "timezone_choices": services_success.TIMEZONE_CHOICES,
        "support_email": services_success.SUPPORT_EMAIL,
        "security_email": services_success.SECURITY_EMAIL,
        "privacy_email": services_success.PRIVACY_EMAIL,
        "legal_version": services_success.LEGAL_VERSION,
        "format_dt": services_success.format_dt,
        "human_due": services_success.human_due,
    }


async def _send_ticket_email(*, to: str, subject: str, body: str) -> None:
    from elipsis_api.services_email import is_email_configured, send_email
    if not is_email_configured() or not to:
        return
    try:
        await send_email(to, subject, body)
    except Exception as exc:  # noqa: BLE001
        print(f"[elipsis] support email failed: {exc}", flush=True)


async def _send_status_email(*, to: str, subject: str, body: str) -> None:
    from elipsis_api.services_email import is_email_configured, send_email
    if not is_email_configured() or not to:
        return
    try:
        await send_email(to, subject, body)
    except Exception as exc:  # noqa: BLE001
        print(f"[elipsis] status email failed: {exc}", flush=True)


def _status_recipients(db: Session) -> list[str]:
    return list(db.scalars(select(models.StatusSubscriber.email).where(
        models.StatusSubscriber.active == 1)))


@router.get("/status")
def status_page(request: Request, user=Depends(get_current_user),
                db: Session = Depends(get_db)):
    rows = services_success.incidents(db)
    timeline = {
        row.id: services_success.incident_updates(db, row.id)
        for row in rows
    }
    return templates.TemplateResponse(request, "service_status.html", {
        **_base(db, user),
        "availability": services_success.availability_30d(db),
        "components": services_success.status_components(db),
        "incidents": rows,
        "timeline": timeline,
        "incident_status_labels": services_success.INCIDENT_STATUS_LABELS,
        "incident_impact_labels": services_success.INCIDENT_IMPACT_LABELS,
        "subscribed": request.query_params.get("subscribed") == "1",
        "error": request.query_params.get("error"),
    })


@router.post("/status/subscribe")
def status_subscribe(request: Request, email: str = Form(...),
                     db: Session = Depends(get_db)):
    ratelimit.enforce(request, "status-subscribe", limit=5, window=300)
    address = (email or "").strip().lower()
    if "@" not in address or len(address) > 254:
        return RedirectResponse("/status?error=Enter+a+valid+email", status_code=303)
    existing = db.scalar(select(models.StatusSubscriber).where(
        models.StatusSubscriber.email == address))
    if existing is None:
        db.add(models.StatusSubscriber(email=address, active=1))
    else:
        existing.active = 1
    db.commit()
    return RedirectResponse("/status?subscribed=1", status_code=303)


@router.get("/trust")
def trust_centre(request: Request, user=Depends(get_current_user),
                 db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "trust_centre.html", {
        **_base(db, user),
        "subprocessors": services_success.SUBPROCESSORS,
        "retention": services_success.RETENTION,
        "availability": services_success.availability_30d(db),
        "articles": services_success.HELP_ARTICLES[:6],
    })


@router.get("/dpa")
def dpa(request: Request, user=Depends(get_current_user),
        db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "dpa.html", {
        **_base(db, user),
        "subprocessors": services_success.SUBPROCESSORS,
        "retention": services_success.RETENTION,
    })


@router.get("/subprocessors")
def subprocessors(request: Request, user=Depends(get_current_user),
                  db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "subprocessors.html", {
        **_base(db, user),
        "subprocessors": services_success.SUBPROCESSORS,
        "retention": services_success.RETENTION,
    })


@router.get("/accessibility")
def accessibility(request: Request, user=Depends(get_current_user),
                  db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "accessibility.html", _base(db, user))


@router.get("/service-standards")
def service_standards(request: Request, user=Depends(get_current_user),
                      db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "service_standards.html", {
        **_base(db, user),
        "sla": services_success.SLA,
        "priority_labels": services_success.PRIORITY_LABELS,
        "availability": services_success.availability_30d(db),
        "retention": services_success.RETENTION,
    })


@router.get("/changelog")
def changelog(request: Request, user=Depends(get_current_user),
              db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "changelog.html", {
        **_base(db, user),
        "entries": services_success.CHANGELOG,
    })


@router.get("/help")
def help_centre(request: Request, q: str = "", user=Depends(get_current_user),
                db: Session = Depends(get_db)):
    query = (q or "").strip()
    return templates.TemplateResponse(request, "help_centre.html", {
        **_base(db, user),
        "query": query,
        "articles": services_success.help_search(query),
        "categories": sorted({item["category"] for item in services_success.HELP_ARTICLES}),
    })


@router.get("/help/{slug}")
def help_article(slug: str, request: Request, user=Depends(get_current_user),
                 db: Session = Depends(get_db)):
    article = services_success.help_article(slug)
    if article is None:
        return templates.TemplateResponse(request, "404.html",
                                          {"user": user}, status_code=404)
    related = [item for item in services_success.HELP_ARTICLES
               if item["category"] == article["category"] and item["slug"] != slug][:3]
    return templates.TemplateResponse(request, "help_article.html", {
        **_base(db, user), "article": article, "related": related,
    })


@router.get("/support")
def support_centre(request: Request, user=Depends(get_current_user),
                   db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    tickets = services_success.tickets_for(db, user)
    rows = [{"ticket": row, "state": services_success.ticket_state(row)}
            for row in tickets]
    return templates.TemplateResponse(request, "support.html", {
        **_base(db, user),
        "tickets": rows,
        "created": request.query_params.get("created"),
        "error": request.query_params.get("error"),
        "support_email": services_success.SUPPORT_EMAIL,
        "sla": services_success.SLA,
        "priority_labels": services_success.PRIORITY_LABELS,
    })


@router.post("/support")
def support_create(request: Request, background_tasks: BackgroundTasks,
                   subject: str = Form(...), body: str = Form(...),
                   category: str = Form("general"),
                   priority: str = Form("normal"),
                   user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    ratelimit.enforce(request, "support-create", limit=8, window=300)
    clean_subject = (subject or "").strip()
    clean_body = (body or "").strip()
    if len(clean_subject) < 4 or len(clean_body) < 15:
        return RedirectResponse(
            "/support?error=Add+a+clear+subject+and+enough+detail+to+reproduce+the+issue",
            status_code=303)
    ticket = services_success.create_ticket(
        db, user, subject=clean_subject, body=clean_body, category=category,
        priority=priority, source_path=request.headers.get("referer"),
        timezone=_zone(db, user))
    background_tasks.add_task(
        _send_ticket_email, to=ticket.requester_email,
        subject=f"Elipsis support {ticket.reference}: {ticket.subject}",
        body=(f"<p>We received your request <strong>{ticket.reference}</strong>.</p>"
              f"<p>Priority: {ticket.priority}. First response target: "
              f"{services_success.SLA.get(ticket.priority or 'normal', {}).get('coverage', '')}.</p>"
              f"<p>Track it at /support/{ticket.reference}.</p>"))
    background_tasks.add_task(
        _send_ticket_email, to=services_success.SUPPORT_EMAIL,
        subject=f"New {ticket.priority} ticket {ticket.reference}",
        body=(f"<p>{html.escape(ticket.subject)}</p>"
              f"<p>{html.escape(ticket.body[:1500])}</p>"
              f"<p>Requester: {html.escape(ticket.requester_email)}</p>"))
    return RedirectResponse(f"/support/{ticket.reference}?created=1", status_code=303)


@router.get("/support/{reference}")
def support_ticket(reference: str, request: Request,
                   user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    ticket = services_success.ticket_for(db, user, reference)
    if ticket is None:
        return templates.TemplateResponse(request, "404.html",
                                          {"user": user}, status_code=404)
    messages = services_success.messages_for(db, ticket.id, public_only=True)
    return templates.TemplateResponse(request, "support_ticket.html", {
        **_base(db, user),
        "ticket": ticket,
        "state": services_success.ticket_state(ticket),
        "messages": messages,
        "created": request.query_params.get("created") == "1",
        "replied": request.query_params.get("replied") == "1",
        "csat_saved": request.query_params.get("csat") == "1",
        "priority_labels": services_success.PRIORITY_LABELS,
        "status_labels": services_success.STATUS_LABELS,
        "format_dt": services_success.format_dt,
    })


@router.post("/support/{reference}/reply")
def support_reply(reference: str, request: Request,
                  background_tasks: BackgroundTasks, body: str = Form(...),
                  user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    ticket = services_success.ticket_for(db, user, reference)
    if ticket is None:
        return templates.TemplateResponse(request, "404.html",
                                          {"user": user}, status_code=404)
    clean = (body or "").strip()
    if len(clean) < 2:
        return RedirectResponse(f"/support/{reference}?error=Add+a+message",
                                status_code=303)
    services_success.add_message(
        db, ticket, body=clean, author_id=user.id, author_name=user.name or user.email,
        from_staff=False)
    background_tasks.add_task(
        _send_ticket_email, to=services_success.SUPPORT_EMAIL,
        subject=f"Customer reply {ticket.reference}",
        body=(f"<p>{html.escape(user.name or user.email)} replied to "
              f"<strong>{ticket.reference}</strong>.</p><p>{html.escape(clean[:1500])}</p>"))
    return RedirectResponse(f"/support/{reference}?replied=1", status_code=303)


@router.post("/support/{reference}/csat")
def support_csat(reference: str, request: Request, score: int = Form(...),
                 comment: str = Form(""), user=Depends(get_current_user),
                 db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    ticket = services_success.ticket_for(db, user, reference)
    if ticket is None:
        return templates.TemplateResponse(request, "404.html",
                                          {"user": user}, status_code=404)
    ticket.csat_score = max(1, min(5, int(score)))
    ticket.csat_comment = (comment or "").strip()[:2000] or None
    db.commit()
    return RedirectResponse(f"/support/{reference}?csat=1", status_code=303)


@router.get("/feedback")
def feedback_page(request: Request, user=Depends(get_current_user),
                  db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    recent = list(db.scalars(select(models.Feedback).where(
        models.Feedback.user_id == user.id).order_by(
        models.Feedback.id.desc()).limit(8)))
    return templates.TemplateResponse(request, "feedback.html", {
        **_base(db, user), "recent": recent,
        "sent": request.query_params.get("sent") == "1",
    })


@router.post("/feedback")
def feedback_submit(request: Request, kind: str = Form("nps"),
                    score: int = Form(...), comment: str = Form(""),
                    context: str = Form(""), user=Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    ratelimit.enforce(request, "feedback", limit=6, window=3600)
    safe_kind = kind if kind in {"nps", "csat", "ces", "feature"} else "nps"
    services_success.create_feedback(
        db, user, kind=safe_kind, score=score, comment=comment,
        context=context, path=request.headers.get("referer", "/feedback"))
    return RedirectResponse("/feedback?sent=1", status_code=303)


@router.get("/getting-started")
def getting_started(request: Request, user=Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    orgs = services.owned_orgs(db, user)
    if not orgs:
        return RedirectResponse("/setup", status_code=303)
    focus = request.query_params.get("org", "")
    selected = next((org for org in orgs if str(org.id) == focus), None)
    if selected is None:
        prefs = _prefs(db, user)
        preferred = prefs.default_organization_id if prefs else None
        selected = next((org for org in orgs if org.id == preferred), orgs[0])
    return templates.TemplateResponse(request, "getting_started.html", {
        **_base(db, user),
        "organizations": orgs,
        "company": selected,
        "activation": services_success.activation(db, user, selected),
        "health": services_success.customer_health(db, selected),
    })


@router.get("/account/data")
def account_data(request: Request, user=Depends(get_current_user),
                 db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    return templates.TemplateResponse(request, "account_data.html", {
        **_base(db, user),
        "requests": services_success.data_requests_for(db, user),
        "legal": services_success.legal_state(db, user),
        "retention": services_success.RETENTION,
        "created": request.query_params.get("created"),
        "accepted": request.query_params.get("accepted") == "1",
        "error": request.query_params.get("error"),
    })


@router.post("/account/data/export")
def account_export(request: Request, user=Depends(get_current_user),
                   db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    ratelimit.enforce(request, "data-export", limit=3, window=3600)
    record, _ = services_success.create_data_request(db, user, kind="export",
                                                     note="Self-service JSON export")
    services_success.complete_data_request(db, record, note="Delivered immediately as JSON.")
    payload = services_success.export_payload(db, user)
    filename = f"elipsis-export-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.json"
    return JSONResponse(
        payload,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/account/data/request")
def account_data_request(request: Request, kind: str = Form("erasure"),
                         note: str = Form(""), user=Depends(get_current_user),
                         db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    ratelimit.enforce(request, "data-request", limit=5, window=3600)
    record, created = services_success.create_data_request(
        db, user, kind=kind, note=note)
    status = "created" if created else "existing"
    return RedirectResponse(
        f"/account/data?created={quote(status)}&ref={quote(record.reference)}",
        status_code=303)


@router.post("/legal/accept")
def legal_accept(request: Request, terms: str = Form(""),
                 privacy: str = Form(""), user=Depends(get_current_user),
                 db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not terms and not privacy:
        return RedirectResponse(
            "/account/data?error=Choose+at+least+one+document+to+record",
            status_code=303)
    if terms:
        services_success.record_acceptance(
            db, user, document="terms",
            version=services_success.LEGAL_VERSION, request=request)
    if privacy:
        services_success.record_acceptance(
            db, user, document="privacy",
            version=services_success.LEGAL_VERSION, request=request)
    return RedirectResponse("/account/data?accepted=1", status_code=303)


@router.get("/.well-known/security.txt", response_class=PlainTextResponse)
def security_txt():
    expires = (datetime.now(UTC) + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return (
        f"Contact: mailto:{services_success.SECURITY_EMAIL}\n"
        f"Expires: {expires}\n"
        "Preferred-Languages: en\n"
        "Canonical: https://elipsis.co.ke/.well-known/security.txt\n"
        "Policy: https://elipsis.co.ke/security\n"
        "Acknowledgments: https://elipsis.co.ke/security\n"
    )


@router.get("/admin/service")
def admin_service(request: Request, user=Depends(require_admin),
                  db: Session = Depends(get_db)):
    data_requests = list(db.scalars(select(models.DataRequest).where(
        models.DataRequest.status.in_(("received", "in_progress"))
    ).order_by(models.DataRequest.id.desc())))
    tickets = services_success.support_metrics(db)
    rows = [{"ticket": row, "state": services_success.ticket_state(row)}
            for row in tickets["tickets"]]
    return templates.TemplateResponse(request, "admin_service.html", {
        **_base(db, user),
        "metrics": tickets,
        "ticket_rows": rows,
        "incidents": services_success.incidents(db),
        "data_requests": data_requests,
        "feedback": services_success.feedback_summary(db),
        "availability": services_success.availability_30d(db),
        "health_queue": services_success.health_queue(db),
        "message": request.query_params.get("message"),
        "incident_status_labels": services_success.INCIDENT_STATUS_LABELS,
        "incident_impact_labels": services_success.INCIDENT_IMPACT_LABELS,
        "priority_labels": services_success.PRIORITY_LABELS,
        "status_labels": services_success.STATUS_LABELS,
    })


@router.post("/admin/service/tickets/{ticket_id}")
def admin_ticket_update(ticket_id: int, request: Request, body: str = Form(""),
                        status: str = Form(""), priority: str = Form(""),
                        internal: str = Form(""),
                        user=Depends(require_admin), db: Session = Depends(get_db)):
    ticket = db.get(models.SupportTicket, ticket_id)
    if ticket is None:
        return RedirectResponse("/admin/service?message=Ticket+not+found",
                                status_code=303)
    if priority in services_success.PRIORITY_LABELS:
        ticket.priority = priority
    if (body or "").strip():
        services_success.add_message(
            db, ticket, body=body, author_id=user.id,
            author_name=user.name or user.email,
            internal=bool(internal), from_staff=True)
    if status in services_success.STATUS_LABELS:
        if status == "resolved":
            services_success.resolve_ticket(db, ticket)
        else:
            ticket.status = status
            if status in {"open", "in_progress"}:
                ticket.resolved_at = None
            db.commit()
    return RedirectResponse("/admin/service?message=Ticket+updated", status_code=303)


@router.post("/admin/service/incidents")
def admin_incident_create(background_tasks: BackgroundTasks,
                          title: str = Form(...), summary: str = Form(""),
                          impact: str = Form("minor"),
                          components: str = Form("web,api"),
                          user=Depends(require_admin), db: Session = Depends(get_db)):
    incident = services_success.create_incident(
        db, title=title, summary=summary, impact=impact,
        components=[part.strip() for part in components.split(",") if part.strip()],
        created_by=user.id)
    for email in _status_recipients(db):
        background_tasks.add_task(
            _send_status_email, to=email,
            subject=f"[{incident.reference}] {incident.title}",
            body=(f"<p><strong>{html.escape(incident.title)}</strong></p>"
                  f"<p>{html.escape(summary or 'We are investigating.')}</p>"
                  f"<p>Status: investigating. Updates: /status</p>"))
    return RedirectResponse("/admin/service?message=Incident+published", status_code=303)


@router.post("/admin/service/incidents/{incident_id}/update")
def admin_incident_update(incident_id: int, background_tasks: BackgroundTasks,
                          status: str = Form(...), body: str = Form(...),
                          postmortem: str = Form(""),
                          user=Depends(require_admin),
                          db: Session = Depends(get_db)):
    row = db.get(models.ServiceIncident, incident_id)
    if row is None:
        return RedirectResponse("/admin/service?message=Incident+not+found",
                                status_code=303)
    services_success.update_incident(db, row, status=status, body=body,
                                     created_by=user.id, postmortem=postmortem)
    label = services_success.INCIDENT_STATUS_LABELS.get(status, status)
    for email in _status_recipients(db):
        background_tasks.add_task(
            _send_status_email, to=email,
            subject=f"[{row.reference}] {label}: {row.title}",
            body=(f"<p><strong>{html.escape(row.title)}</strong></p>"
                  f"<p>{html.escape(body)}</p>"
                  f"<p>Status: {html.escape(label)}. Updates: /status</p>"))
    return RedirectResponse("/admin/service?message=Incident+updated", status_code=303)


@router.post("/admin/service/data-requests/{request_id}/complete")
def admin_data_request_complete(request_id: int, note: str = Form(""),
                                user=Depends(require_admin),
                                db: Session = Depends(get_db)):
    row = db.get(models.DataRequest, request_id)
    if row is None:
        return RedirectResponse("/admin/service?message=Request+not+found",
                                status_code=303)
    services_success.complete_data_request(db, row, note=note)
    return RedirectResponse("/admin/service?message=Data+request+completed",
                            status_code=303)
