"""Execution workspace: action board, trends, audit, team, reviews, sharing."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from elipsis_api import models, services, services_ops, services_webhooks
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


def _back(raw: str | None, fallback: str) -> str:
    raw = (raw or "").strip()
    if raw.startswith("/") and not raw.startswith("//"):
        return raw
    return fallback


@router.get("/actions")
def action_board(request: Request, user=Depends(get_current_user),
                 db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    visible = services.visible_org_ids(db, user)
    status = request.query_params.get("status") or "open"
    owner = request.query_params.get("owner") or ""
    overdue = request.query_params.get("overdue") == "1"
    items = services_ops.action_items(
        db, visible, status=None if status == "all" else status,
        owner=owner or None, overdue_only=overdue)
    return templates.TemplateResponse(
        request, "actions.html",
        {"user": user, "items": items, "status": status, "owner": owner,
         "overdue": overdue, "summary": services_ops.action_summary(db, visible),
         "workload": services_ops.owner_workload(db, visible),
         "views": services_ops.saved_views(db, user),
         "notifications": services_ops.notifications(db, user),
         "organizations": services.list_organizations(db, visible),
         "updated": request.query_params.get("updated") == "1"})


@router.post("/actions/bulk")
async def action_bulk(request: Request, background_tasks: BackgroundTasks,
                      user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    form = await request.form()
    ids = [int(value) for value in form.getlist("item_ids") if str(value).isdigit()]
    status = str(form.get("status") or "keep")
    owner = str(form.get("owner") or "").strip()
    due_date = str(form.get("due_date") or "").strip()
    changed = 0
    for item_id in ids[:500]:
        item = db.get(models.RoadmapItem, item_id)
        if item is None:
            continue
        assessment = db.get(models.Assessment, item.assessment_id)
        if assessment is None or not services.can_access_org(db, user, assessment.organization_id):
            continue
        services.update_plan_item(
            db, assessment.id, item.id,
            owner=owner if owner else (item.owner or ""),
            due_date=due_date or (item.due_date or ""),
            status=(item.status or "not_started") if status == "keep" else status,
            notes=item.notes or "")
        changed += 1
        for hook in services_webhooks.matching_endpoints(
                db, assessment.organization_id, "action.updated"):
            background_tasks.add_task(
                services_webhooks.deliver_event, hook.id, "action.updated",
                {"event": "action.updated", "item_id": item.id,
                 "title": item.title, "status": item.status, "owner": item.owner,
                 "assessment_id": assessment.id})
    if changed:
        services_ops.record_audit(
            db, action="plan.bulk_update", user_id=user.id,
            detail=f"{changed} actions → {status}")
        db.commit()
    return RedirectResponse(f"/actions?updated=1&bulk={changed}", status_code=303)


@router.post("/views")
def view_save(name: str = Form(...), query: str = Form(""),
              user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    services_ops.save_view(db, user, name, query)
    return RedirectResponse("/actions?view=saved", status_code=303)


@router.post("/views/{view_id}/delete")
def view_delete(view_id: int, user=Depends(get_current_user),
                db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    services_ops.delete_view(db, user, view_id)
    return RedirectResponse("/actions?view=deleted", status_code=303)


@router.get("/views/{view_id}")
def view_open(view_id: int, user=Depends(get_current_user),
              db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    row = db.get(models.SavedView, view_id)
    if row is None or row.user_id != user.id:
        return RedirectResponse("/actions", status_code=303)
    query = (row.query or "").lstrip("?")
    return RedirectResponse(f"/actions?{query}" if query else "/actions", status_code=303)


@router.post("/actions/{item_id}")
def action_update(item_id: int, request: Request, background_tasks: BackgroundTasks,
                  owner: str = Form(""), due_date: str = Form(""),
                  status: str = Form("not_started"), notes: str = Form(""),
                  next: str = Form("/actions"),
                  user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    item = db.get(models.RoadmapItem, item_id)
    if item is None:
        return _not_found(request, user)
    assessment = db.get(models.Assessment, item.assessment_id)
    if assessment is None or not services.can_access_org(db, user, assessment.organization_id):
        return _not_found(request, user)
    services.update_plan_item(
        db, assessment.id, item.id, owner=owner, due_date=due_date,
        status=status, notes=notes)
    services_ops.record_audit(
        db, action="plan.update", organization_id=assessment.organization_id,
        assessment_id=assessment.id, user_id=user.id,
        detail=f"{item.title}: {status}")
    db.commit()
    for hook in services_webhooks.matching_endpoints(
            db, assessment.organization_id, "action.updated"):
        background_tasks.add_task(
            services_webhooks.deliver_event, hook.id, "action.updated",
            {"event": "action.updated", "item_id": item.id,
             "title": item.title, "status": status, "owner": owner,
             "assessment_id": assessment.id})
    target = _back(next, "/actions")
    sep = "&" if "?" in target else "?"
    return RedirectResponse(f"{target}{sep}updated=1", status_code=303)


@router.get("/trends")
def trends(request: Request, user=Depends(get_current_user),
           db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    visible = services.visible_org_ids(db, user)
    return templates.TemplateResponse(
        request, "trends.html",
        {"user": user, "trends": services_ops.org_trends(db, visible),
         "summary": services_ops.action_summary(db, visible),
         "notifications": services_ops.notifications(db, user)})


@router.get("/audit")
def audit_log(request: Request, user=Depends(get_current_user),
              db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    visible = services.visible_org_ids(db, user)
    return templates.TemplateResponse(
        request, "audit.html",
        {"user": user, "events": services_ops.audit_events(db, visible, limit=200),
         "notifications": services_ops.notifications(db, user)})


@router.get("/search")
def search(request: Request, user=Depends(get_current_user),
           db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    visible = services.visible_org_ids(db, user)
    q = (request.query_params.get("q") or "").strip()[:120]
    results = services_ops.search_workspace(db, visible, q)
    return templates.TemplateResponse(
        request, "search.html",
        {"user": user, "q": q, "results": results,
         "notifications": services_ops.notifications(db, user)})


@router.get("/company/{organization_id}/team")
def team_page(organization_id: int, request: Request,
              user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not services.can_access_org(db, user, organization_id):
        return _not_found(request, user)
    org = db.get(models.Organization, organization_id)
    if org is None:
        return _not_found(request, user)
    return templates.TemplateResponse(
        request, "team.html",
        {"user": user, "org": org, "organization": org,
         "members": services_ops.team_members(db, organization_id),
         "message": request.query_params.get("message"),
         "error": request.query_params.get("error")})


@router.post("/company/{organization_id}/team")
def team_add(organization_id: int, request: Request,
             email: str = Form(...),
             user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not services.can_access_org(db, user, organization_id):
        return _not_found(request, user)
    ok, message = services_ops.add_team_member(db, organization_id, email, user.id)
    key = "message" if ok else "error"
    from urllib.parse import quote
    return RedirectResponse(
        f"/company/{organization_id}/team?{key}={quote(message)}", status_code=303)


@router.post("/company/{organization_id}/team/{member_id}/remove")
def team_remove(organization_id: int, member_id: int, request: Request,
                user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    if not services.can_access_org(db, user, organization_id):
        return _not_found(request, user)
    ok, message = services_ops.remove_team_member(db, organization_id, member_id, user.id)
    key = "message" if ok else "error"
    from urllib.parse import quote
    return RedirectResponse(
        f"/company/{organization_id}/team?{key}={quote(message)}", status_code=303)


@router.post("/assessment/{assessment_id}/review")
def set_review(assessment_id: int, request: Request,
               review_due_at: str = Form(""), review_note: str = Form(""),
               user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    assessment = _owned(db, user, assessment_id)
    if assessment is None:
        return _not_found(request, user)
    services_ops.set_review(db, assessment, review_due_at, review_note, user.id)
    return RedirectResponse(f"/assessment/{assessment_id}/results?review=saved",
                            status_code=303)


@router.post("/assessment/{assessment_id}/shares/{token}/revoke")
def revoke_share(assessment_id: int, token: str, request: Request,
                 user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    assessment = _owned(db, user, assessment_id)
    if assessment is None:
        return _not_found(request, user)
    if services_ops.revoke_share_link(db, assessment_id, token):
        services_ops.record_audit(
            db, action="share.revoke", organization_id=assessment.organization_id,
            assessment_id=assessment.id, user_id=user.id, detail=token[:8])
        db.commit()
    return RedirectResponse(f"/assessment/{assessment_id}/results?share=revoked",
                            status_code=303)


class ScenarioIn(BaseModel):
    staff: int | None = None
    hourly_rate: float | None = None
    working_hours_per_month: float | None = None
    max_savings_share: float | None = None
    annual_revenue: str | None = None


@router.post("/assessment/{assessment_id}/scenario")
def scenario(assessment_id: int, payload: ScenarioIn, request: Request,
             user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return JSONResponse({"error": "login required"}, status_code=401)
    if _owned(db, user, assessment_id) is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    overrides = {}
    if payload.staff is not None:
        overrides["staff"] = max(1, min(100_000, int(payload.staff)))
    if payload.hourly_rate is not None:
        overrides["hourly_rate"] = max(1.0, min(1_000_000.0, float(payload.hourly_rate)))
    if payload.working_hours_per_month is not None:
        overrides["working_hours_per_month"] = max(1.0, min(744.0, float(payload.working_hours_per_month)))
    if payload.max_savings_share is not None:
        pct = max(0.0, min(50.0, float(payload.max_savings_share)))
        overrides["max_savings_share"] = pct / 100.0
    if payload.annual_revenue is not None:
        overrides["annual_revenue"] = payload.annual_revenue.strip()[:40]
    _, result = services.compute_scenario(db, assessment_id, overrides)
    if result is None:
        return JSONResponse({"error": "not ready"}, status_code=404)
    fin = result.get("financial") or {}
    return JSONResponse({
        "readiness_index": result.get("readiness_index"),
        "financial": {
            "annual_savings": fin.get("annual_savings"),
            "investment": fin.get("investment"),
            "roi": fin.get("roi"),
            "payback_months": fin.get("payback_months"),
            "current_cost": fin.get("current_cost"),
            "future_cost": fin.get("future_cost"),
            "assumptions": fin.get("assumptions"),
        },
    })
