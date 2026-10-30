"""Operations ecosystem: KPI ledger, incidents, compliance, and data exchange."""

from __future__ import annotations

import csv
import io
import json
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from elipsis_api import models, services, services_operations, services_ops, services_webhooks
from elipsis_api.config import SESSION_COOKIE
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user, login_redirect, templates
from elipsis_api.document_storage import (
    AttachmentError,
    attachment_url,
    local_path,
    remove_attachment,
    store_attachment,
)

router = APIRouter()
api_router = APIRouter(prefix="/api/v1/operations", tags=["operations"])

MAX_IMPORT_BYTES = 512 * 1024


def _not_found(request, user):
    return templates.TemplateResponse(request, "404.html", {"user": user}, status_code=404)


def _scope(db: Session, user, request: Request):
    visible = services.visible_org_ids(db, user)
    orgs = services.list_organizations(db, visible)
    selected = None
    raw = (request.query_params.get("org") or "").strip()
    if raw.isdigit():
        wanted = int(raw)
        if visible is None or wanted in visible:
            selected = next((org for org in orgs if org.id == wanted), None)
    if selected is None and len(orgs) == 1:
        selected = orgs[0]
    if selected is not None:
        scope = [selected.id]
    else:
        scope = visible
    return scope, orgs, selected


def _context(db: Session, user, request: Request) -> dict:
    scope, orgs, selected = _scope(db, user, request)
    return {
        "user": user,
        "organizations": orgs,
        "selected_org": selected,
        "scope": scope,
        "org_names": {org.id: org.name for org in orgs},
        "notifications": services_ops.notifications(db, user),
        "error": request.query_params.get("error") or "",
        "saved": request.query_params.get("saved") == "1",
        "catalog": services_operations.METRIC_CATALOG,
        "lane_labels": services_operations.LANE_LABELS,
        "severities": services_operations.SEVERITIES,
        "incident_statuses": services_operations.INCIDENT_STATUSES,
        "doc_types": services_operations.DOC_TYPES,
        "doc_statuses": services_operations.DOC_STATUSES,
        "export_kinds": services_operations.IMPORT_KINDS,
    }


def _org_or_none(db: Session, user, raw: str | int | None):
    try:
        org_id = int(raw)
    except (TypeError, ValueError):
        return None
    if not services.can_access_org(db, user, org_id):
        return None
    return db.get(models.Organization, org_id)


def _redirect(path: str, *, error: str = "", saved: bool = False) -> RedirectResponse:
    sep = "&" if "?" in path else "?"
    if error:
        path = f"{path}{sep}error={quote(error[:180])}"
    elif saved:
        path = f"{path}{sep}saved=1"
    return RedirectResponse(path, status_code=303)


def _fire(db: Session, background_tasks: BackgroundTasks, org_id: int,
          event: str, payload: dict) -> None:
    for hook in services_webhooks.matching_endpoints(db, org_id, event):
        background_tasks.add_task(services_webhooks.deliver_event,
                                  hook.id, event, {"event": event, **payload})


@router.get("/operations")
def operations_home(request: Request, user=Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    ctx = _context(db, user, request)
    data = services_operations.summary(db, ctx["scope"])
    recent_incidents = services_operations.incidents(
        db, ctx["scope"], status=None)[:6]
    doc_rows = []
    for row in services_operations.documents(db, ctx["scope"], status=None)[:6]:
        doc_rows.append({"row": row, **services_operations.document_reading(row)})
    return templates.TemplateResponse(
        request, "operations.html",
        {**ctx, "ops": data, "recent_incidents": recent_incidents,
         "doc_rows": doc_rows,
         "activity": services_operations.recent_activity(db, ctx["scope"]),
         "sample_loaded": request.query_params.get("sample") == "1"})


@router.get("/operations/metrics")
def metrics_page(request: Request, user=Depends(get_current_user),
                 db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    ctx = _context(db, user, request)
    key = (request.query_params.get("key") or "").strip() or None
    if key and key not in services_operations.METRIC_CATALOG:
        key = None
    rows = services_operations.latest_metrics(db, ctx["scope"], key=key)
    sparks = services_operations.metric_spark(db, ctx["scope"])
    for row in rows:
        row["spark"] = sparks.get(row["metric"].metric_key, [])
        row["spark_points"] = services_operations.spark_points(row["spark"])
    readings = []
    for row in services_operations.metric_history(db, ctx["scope"], key, limit=80):
        readings.append({"row": row, **{
            "label": services_operations.METRIC_CATALOG.get(
                row.metric_key, {}).get("label", row.metric_key),
            "formatted": services_operations.format_value(row.metric_key, row.value),
            "status": services_operations.metric_status(row.metric_key, row.value),
        }})
    return templates.TemplateResponse(
        request, "operations_metrics.html",
        {**ctx, "rows": rows, "readings": readings, "selected_key": key})


@router.post("/operations/metrics")
def metric_create(background_tasks: BackgroundTasks,
                  organization_id: int = Form(...),
                  metric_key: str = Form(...), value: str = Form(...),
                  period_end: str = Form(...), note: str = Form(""),
                  user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    org = _org_or_none(db, user, organization_id)
    if org is None:
        return _redirect("/operations/metrics", error="Organisation not found.")
    try:
        row = services_operations.record_metric(
            db, org.id, metric_key, float(value), period_end,
            source="manual", note=note, user_id=user.id)
        services_ops.record_audit(
            db, action="operations.metric.recorded", organization_id=org.id,
            user_id=user.id,
            detail=f"{metric_key}={row.value} for {row.period_end}")
        db.commit()
    except ValueError as exc:
        db.rollback()
        return _redirect(f"/operations/metrics?org={org.id}", error=str(exc))
    _fire(db, background_tasks, org.id, "metric.recorded", {
        "metric_key": row.metric_key, "value": row.value,
        "period_end": row.period_end})
    return _redirect(f"/operations/metrics?org={org.id}", saved=True)


@router.get("/operations/metrics/export.csv")
def metrics_csv(request: Request, user=Depends(get_current_user),
                db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    ctx = _context(db, user, request)
    bundle = services_operations.export_bundle(db, ctx["scope"])
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["organization", "metric_key", "label", "value", "period_end", "source", "note"])
    for row in bundle["metrics"]:
        writer.writerow([row["organization"], row["metric_key"], row["label"],
                         row["value"], row["period_end"], row["source"],
                         row["note"] or ""])
    return Response(output.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=elipsis-operating-metrics.csv"})


@router.get("/operations/incidents")
def incidents_page(request: Request, user=Depends(get_current_user),
                   db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    ctx = _context(db, user, request)
    status = (request.query_params.get("status") or "open").strip()
    rows = services_operations.incidents(db, ctx["scope"], status=status)
    return templates.TemplateResponse(
        request, "operations_incidents.html",
        {**ctx, "rows": rows, "status_filter": status,
         "counts": services_operations.incident_counts(db, ctx["scope"])})


@router.post("/operations/sample")
def load_sample(organization_id: int = Form(...), user=Depends(get_current_user),
                db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    org = _org_or_none(db, user, organization_id)
    if org is None:
        return _redirect("/operations", error="Organisation not found.")
    counts = services_operations.ensure_sample_data(db, org.id, user.id)
    services_ops.record_audit(
        db, action="operations.sample_loaded", organization_id=org.id,
        user_id=user.id, detail=json.dumps(counts))
    db.commit()
    return _redirect(f"/operations?org={org.id}", saved=True)


@router.post("/operations/incidents")
def incident_create(background_tasks: BackgroundTasks,
                    organization_id: int = Form(...), title: str = Form(...),
                    lane: str = Form("dispatch"), severity: str = Form("medium"),
                    occurred_on: str = Form(""), shipment_ref: str = Form(""),
                    customer_impact: str = Form(""), root_cause: str = Form(""),
                    corrective_action: str = Form(""), owner: str = Form(""),
                    user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    org = _org_or_none(db, user, organization_id)
    if org is None:
        return _redirect("/operations/incidents", error="Organisation not found.")
    try:
        row = services_operations.create_incident(
            db, org.id, title=title, lane=lane, severity=severity,
            occurred_on=occurred_on or None, shipment_ref=shipment_ref,
            customer_impact=customer_impact, root_cause=root_cause,
            corrective_action=corrective_action, owner=owner, user_id=user.id)
        services_ops.record_audit(
            db, action="operations.incident.opened", organization_id=org.id,
            user_id=user.id, detail=f"{row.severity}: {row.title}")
        db.commit()
    except ValueError as exc:
        db.rollback()
        return _redirect(f"/operations/incidents?org={org.id}", error=str(exc))
    _fire(db, background_tasks, org.id, "incident.opened", {
        "incident_id": row.id, "title": row.title,
        "severity": row.severity, "lane": row.lane})
    return _redirect(f"/operations/incidents?org={org.id}", saved=True)


@router.post("/operations/incidents/{incident_id}/resolve")
def incident_resolve(incident_id: int, organization_id: int = Form(...),
                     note: str = Form(""), user=Depends(get_current_user),
                     db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    org = _org_or_none(db, user, organization_id)
    if org is None:
        return _redirect("/operations/incidents", error="Organisation not found.")
    row = services_operations.resolve_incident(db, org.id, incident_id, note)
    if row is None:
        return _redirect(f"/operations/incidents?org={org.id}", error="Incident not found.")
    services_ops.record_audit(
        db, action="operations.incident.resolved", organization_id=org.id,
        user_id=user.id, detail=row.title)
    db.commit()
    return _redirect(f"/operations/incidents?org={org.id}&status=all", saved=True)


@router.post("/operations/incidents/{incident_id}/promote")
def incident_promote(incident_id: int, organization_id: int = Form(...),
                     user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    org = _org_or_none(db, user, organization_id)
    if org is None:
        return _redirect("/operations/incidents", error="Organisation not found.")
    item, error = services_operations.promote_incident(db, org.id, incident_id, user.id)
    if error and item is None:
        return _redirect(f"/operations/incidents?org={org.id}", error=error)
    services_ops.record_audit(
        db, action="operations.incident.promoted", organization_id=org.id,
        assessment_id=item.assessment_id, user_id=user.id,
        detail=f"Incident {incident_id} → action {item.id}")
    db.commit()
    return _redirect(f"/actions?org={org.id}", saved=True)


@router.get("/operations/documents")
def documents_page(request: Request, user=Depends(get_current_user),
                   db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    ctx = _context(db, user, request)
    status = (request.query_params.get("status") or "active").strip()
    rows = []
    for row in services_operations.documents(db, ctx["scope"], status=status):
        rows.append({"row": row, **services_operations.document_reading(row)})
    return templates.TemplateResponse(
        request, "operations_documents.html",
        {**ctx, "rows": rows, "status_filter": status,
         "counts": services_operations.document_counts(db, ctx["scope"])})


@router.post("/operations/documents")
async def document_create(organization_id: int = Form(...), title: str = Form(...),
                          doc_type: str = Form("licence"), reference: str = Form(""),
                          owner: str = Form(""), issued_on: str = Form(""),
                          expires_on: str = Form(""), note: str = Form(""),
                          file: UploadFile | None = File(None),
                          user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    org = _org_or_none(db, user, organization_id)
    if org is None:
        return _redirect("/operations/documents", error="Organisation not found.")
    stored = None
    try:
        if file is not None and file.filename:
            stored = await store_attachment(file)
        row = services_operations.create_document(
            db, org.id, title=title, doc_type=doc_type, reference=reference,
            owner=owner, issued_on=issued_on or None, expires_on=expires_on,
            note=note, user_id=user.id)
        if stored is not None:
            services_operations.attach_document_file(db, org.id, row.id, stored)
        services_ops.record_audit(
            db, action="operations.document.added", organization_id=org.id,
            user_id=user.id,
            detail=f"{row.title} expires {row.expires_on}"
                   + (" with attachment" if stored else ""))
        db.commit()
    except Exception as exc:  # noqa: BLE001 - surface storage/DB failure in the flash
        db.rollback()
        if stored is not None:
            await remove_attachment(stored["key"], stored["backend"])
        return _redirect(f"/operations/documents?org={org.id}", error=str(exc))
    return _redirect(f"/operations/documents?org={org.id}", saved=True)


@router.post("/operations/documents/{document_id}/attachment")
async def document_attachment_upload(document_id: int,
                                     organization_id: int = Form(...),
                                     file: UploadFile = File(...),
                                     user=Depends(get_current_user),
                                     db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    org = _org_or_none(db, user, organization_id)
    if org is None:
        return _redirect("/operations/documents", error="Organisation not found.")
    row = db.get(models.ComplianceDocument, document_id)
    if row is None or row.organization_id != org.id:
        return _redirect(f"/operations/documents?org={org.id}", error="Document not found.")
    stored = None
    old_key, old_backend = row.attachment_key, row.attachment_backend
    try:
        stored = await store_attachment(file)
        services_operations.attach_document_file(db, org.id, document_id, stored)
        services_ops.record_audit(
            db, action="operations.document.attached", organization_id=org.id,
            user_id=user.id, detail=f"{row.title} attachment {stored['name']}")
        db.commit()
    except Exception as exc:  # noqa: BLE001 - surface storage/DB failure in the flash
        db.rollback()
        if stored is not None:
            await remove_attachment(stored["key"], stored["backend"])
        return _redirect(f"/operations/documents?org={org.id}", error=str(exc))
    if old_key and old_key != stored["key"]:
        await remove_attachment(old_key, old_backend)
    return _redirect(f"/operations/documents?org={org.id}", saved=True)


@router.get("/operations/documents/{document_id}/attachment")
def document_attachment_download(document_id: int,
                                 user=Depends(get_current_user),
                                 db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    row = db.get(models.ComplianceDocument, document_id)
    if row is None or _org_or_none(db, user, row.organization_id) is None:
        return Response("not found", status_code=404, media_type="text/plain")
    if not row.attachment_key:
        return Response("no attachment", status_code=404, media_type="text/plain")
    remote = attachment_url(row.attachment_key, row.attachment_backend)
    if remote:
        return RedirectResponse(remote, status_code=307)
    try:
        path = local_path(row.attachment_key)
    except AttachmentError:
        return Response("not found", status_code=404, media_type="text/plain")
    if not path.is_file():
        return Response("not found", status_code=404, media_type="text/plain")
    return FileResponse(
        path, filename=row.attachment_name,
        media_type=row.attachment_type or "application/octet-stream")


@router.post("/operations/documents/{document_id}/renew")
def document_renew(document_id: int, organization_id: int = Form(...),
                   expires_on: str = Form(...), user=Depends(get_current_user),
                   db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    org = _org_or_none(db, user, organization_id)
    if org is None:
        return _redirect("/operations/documents", error="Organisation not found.")
    try:
        row = services_operations.renew_document(db, org.id, document_id, expires_on)
    except ValueError as exc:
        return _redirect(f"/operations/documents?org={org.id}", error=str(exc))
    if row is None:
        return _redirect(f"/operations/documents?org={org.id}", error="Document not found.")
    db.commit()
    return _redirect(f"/operations/documents?org={org.id}", saved=True)


@router.post("/operations/documents/{document_id}/archive")
def document_archive(document_id: int, organization_id: int = Form(...),
                     user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    org = _org_or_none(db, user, organization_id)
    if org is None:
        return _redirect("/operations/documents", error="Organisation not found.")
    if not services_operations.archive_document(db, org.id, document_id):
        return _redirect(f"/operations/documents?org={org.id}", error="Document not found.")
    db.commit()
    return _redirect(f"/operations/documents?org={org.id}&status=all", saved=True)


def _render_data(request: Request, user, db: Session, *,
                 new_token: str | None = None, status_code: int = 200):
    ctx = _context(db, user, request)
    hooks = services_webhooks.endpoints(
        db, ctx["scope"] if ctx["scope"] is not None
        else [org.id for org in ctx["organizations"]])
    bundle = services_operations.export_bundle(db, ctx["scope"])
    return templates.TemplateResponse(
        request, "operations_data.html",
        {**ctx, "hooks": hooks, "bundle": bundle, "new_token": new_token,
         "tokens": services_operations.api_tokens(db, ctx["scope"]),
         "history": services_operations.import_history(db, ctx["scope"], limit=20)},
        status_code=status_code)


@router.get("/operations/data")
def data_page(request: Request, user=Depends(get_current_user),
              db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    return _render_data(request, user, db)


@router.post("/operations/tokens")
def token_create(request: Request, organization_id: int = Form(...),
                 name: str = Form(...), scopes: str = Form("read,write"),
                 user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    org = _org_or_none(db, user, organization_id)
    if org is None:
        return _redirect("/operations/data", error="Organisation not found.")
    row, raw = services_operations.create_api_token(
        db, org.id, user.id, name, scopes)
    services_ops.record_audit(
        db, action="operations.token.created", organization_id=org.id,
        user_id=user.id, detail=f"{row.name} ({row.scopes})")
    db.commit()
    return _render_data(request, user, db, new_token=raw, status_code=201)


@router.post("/operations/tokens/{token_id}/revoke")
def token_revoke(token_id: int, organization_id: int = Form(...),
                 user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    org = _org_or_none(db, user, organization_id)
    if org is None:
        return _redirect("/operations/data", error="Organisation not found.")
    if not services_operations.revoke_api_token(db, org.id, token_id):
        return _redirect(f"/operations/data?org={org.id}", error="Token not found.")
    services_ops.record_audit(
        db, action="operations.token.revoked", organization_id=org.id,
        user_id=user.id, detail=f"token {token_id}")
    db.commit()
    return _redirect(f"/operations/data?org={org.id}", saved=True)


@router.get("/operations/templates/{kind}.csv")
def import_template(kind: str, user=Depends(get_current_user)):
    if user is None:
        return login_redirect()
    samples = {
        "metrics": (
            "metric_key,value,period_end,note\n"
            "on_time_delivery,91.5,2026-09-30,September dispatch review\n"
            "cash_conversion_days,42,2026-09-30,Finance close\n"),
        "incidents": (
            "title,lane,severity,occurred_on,shipment_ref,customer_impact,root_cause,corrective_action,owner\n"
            "Late Mombasa release,dispatch,high,2026-09-28,MBS-4821,Two deliveries missed,Documents arrived late,Pre-clear the day before,Ops lead\n"),
        "documents": (
            "title,doc_type,reference,owner,issued_on,expires_on,note\n"
            "Goods-in-transit insurance,insurance,GIT-2026-14,Compliance lead,2026-01-01,2026-12-31,Annual cover\n"),
    }
    body = samples.get(kind)
    if body is None:
        return Response("not found", status_code=404, media_type="text/plain")
    return Response(body, media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=elipsis-{kind}-template.csv"})


@router.post("/operations/import")
async def data_import(background_tasks: BackgroundTasks,
                      organization_id: int = Form(...), kind: str = Form(...),
                      file: UploadFile = File(...),
                      user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    org = _org_or_none(db, user, organization_id)
    if org is None:
        return _redirect("/operations/data", error="Organisation not found.")
    content = await file.read(MAX_IMPORT_BYTES + 1)
    if len(content) > MAX_IMPORT_BYTES:
        return _redirect(f"/operations/data?org={org.id}", error="CSV is larger than 512 KB.")
    try:
        batch = services_operations.import_csv(
            db, org.id, kind, file.filename, content, user.id)
    except ValueError as exc:
        db.rollback()
        return _redirect(f"/operations/data?org={org.id}", error=str(exc))
    services_ops.record_audit(
        db, action="operations.import.completed", organization_id=org.id,
        user_id=user.id,
        detail=f"{batch.kind}: {batch.imported_count}/{batch.row_count} rows")
    db.commit()
    _fire(db, background_tasks, org.id, "data.imported", {
        "import_id": batch.id, "kind": batch.kind,
        "imported": batch.imported_count, "rows": batch.row_count})
    return _redirect(f"/operations/imports/{batch.id}")


@router.get("/operations/imports/{batch_id}")
def import_detail(batch_id: int, request: Request, user=Depends(get_current_user),
                  db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    batch = db.get(models.DataImport, batch_id)
    if batch is None or not services.can_access_org(db, user, batch.organization_id):
        return _not_found(request, user)
    ctx = _context(db, user, request)
    return templates.TemplateResponse(
        request, "operations_import.html",
        {**ctx, "batch": batch,
         "errors": services_operations.import_errors(batch)})


@router.get("/operations/export.json")
def export_json(request: Request, user=Depends(get_current_user),
                db: Session = Depends(get_db)):
    if user is None:
        return login_redirect()
    ctx = _context(db, user, request)
    return JSONResponse(services_operations.export_bundle(db, ctx["scope"]))


# --- Programmatic interface -------------------------------------------------

def _api_principal(db: Session, request: Request):
    header = (request.headers.get("authorization") or "").strip()
    if header.lower().startswith("bearer "):
        token = services_operations.authenticate_api_token(db, header[7:].strip())
        if token is None:
            return None, None
        user = db.get(models.User, token.user_id) if token.user_id else None
        if user is None:
            return None, None
        db.commit()
        return user, token
    return services.user_for_token(db, request.cookies.get(SESSION_COOKIE)), None


def _api_scope(db: Session, user, request: Request, token=None):
    if token is not None:
        return [token.organization_id]
    visible = services.visible_org_ids(db, user)
    raw = (request.query_params.get("org_id") or "").strip()
    if raw.isdigit():
        org_id = int(raw)
        return [org_id] if services.can_access_org(db, user, org_id) else []
    return visible


def _api_can_write(token) -> bool:
    return token is None or "write" in (token.scopes or "")


def _api_summary(db: Session, scope) -> dict:
    data = services_operations.summary(db, scope)
    return {
        "measured": data["measured"], "at_target": data["at_target"],
        "at_risk": data["at_risk"], "incidents": data["incidents"],
        "documents": data["documents"], "last_updated": data["last_updated"],
        "metrics": [{
            "organization_id": item["metric"].organization_id,
            "metric_key": item["metric"].metric_key,
            "label": item["label"], "value": item["value"],
            "formatted": item["formatted"], "target": item["target"],
            "status": item["status"], "delta": item["delta"],
            "movement": item["movement"], "period_end": item["metric"].period_end,
        } for item in data["metrics"]],
        "lanes": data["lanes"],
    }


@api_router.get("")
@api_router.get("/")
def api_summary(request: Request, db: Session = Depends(get_db)):
    user, token = _api_principal(db, request)
    if user is None:
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    return _api_summary(db, _api_scope(db, user, request, token))


@api_router.get("/metrics")
def api_metrics(request: Request, db: Session = Depends(get_db)):
    user, token = _api_principal(db, request)
    if user is None:
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    scope = _api_scope(db, user, request, token)
    key = (request.query_params.get("metric_key") or "").strip() or None
    rows = services_operations.latest_metrics(db, scope, key=key)
    return {"metrics": [{
        "organization_id": item["metric"].organization_id,
        "metric_key": item["metric"].metric_key, "label": item["label"],
        "value": item["value"], "formatted": item["formatted"],
        "target": item["target"], "status": item["status"],
        "delta": item["delta"], "movement": item["movement"],
        "period_end": item["metric"].period_end,
    } for item in rows]}


@api_router.post("/metrics")
async def api_metric_create(request: Request, db: Session = Depends(get_db)):
    user, token = _api_principal(db, request)
    if user is None:
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    if not _api_can_write(token):
        return JSONResponse({"detail": "token is read-only"}, status_code=403)
    body = await request.json()
    try:
        org_id = token.organization_id if token is not None else int(body.get("organization_id"))
    except (TypeError, ValueError):
        return JSONResponse({"detail": "organization_id is required"}, status_code=400)
    if not services.can_access_org(db, user, org_id):
        return JSONResponse({"detail": "organization not found"}, status_code=404)
    try:
        row = services_operations.record_metric(
            db, org_id, str(body.get("metric_key") or ""), body.get("value"),
            str(body.get("period_end") or ""), source="api",
            note=body.get("note"), user_id=user.id)
    except ValueError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)
    services_ops.record_audit(
        db, action="operations.metric.recorded", organization_id=org_id,
        user_id=user.id, detail=f"{row.metric_key}={row.value} via API")
    db.commit()
    return JSONResponse({"id": row.id, "metric_key": row.metric_key,
                         "value": row.value, "period_end": row.period_end}, status_code=201)


@api_router.get("/incidents")
def api_incidents(request: Request, db: Session = Depends(get_db)):
    user, token = _api_principal(db, request)
    if user is None:
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    scope = _api_scope(db, user, request, token)
    status = (request.query_params.get("status") or "").strip() or None
    return {"incidents": [{
        "id": row.id, "organization_id": row.organization_id,
        "title": row.title, "lane": row.lane, "severity": row.severity,
        "status": row.status, "occurred_on": row.occurred_on,
        "shipment_ref": row.shipment_ref, "owner": row.owner,
        "root_cause": row.root_cause, "corrective_action": row.corrective_action,
        "action_item_id": row.action_item_id,
    } for row in services_operations.incidents(db, scope, status=status)]}


@api_router.post("/incidents")
async def api_incident_create(request: Request, db: Session = Depends(get_db)):
    user, token = _api_principal(db, request)
    if user is None:
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    if not _api_can_write(token):
        return JSONResponse({"detail": "token is read-only"}, status_code=403)
    body = await request.json()
    try:
        org_id = token.organization_id if token is not None else int(body.get("organization_id"))
    except (TypeError, ValueError):
        return JSONResponse({"detail": "organization_id is required"}, status_code=400)
    if not services.can_access_org(db, user, org_id):
        return JSONResponse({"detail": "organization not found"}, status_code=404)
    try:
        row = services_operations.create_incident(
            db, org_id, title=str(body.get("title") or ""),
            lane=str(body.get("lane") or "dispatch"),
            severity=str(body.get("severity") or "medium"),
            occurred_on=body.get("occurred_on"),
            shipment_ref=body.get("shipment_ref"),
            customer_impact=body.get("customer_impact"),
            root_cause=body.get("root_cause"),
            corrective_action=body.get("corrective_action"),
            owner=body.get("owner"), user_id=user.id)
    except ValueError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)
    services_ops.record_audit(
        db, action="operations.incident.opened", organization_id=org_id,
        user_id=user.id, detail=f"{row.severity}: {row.title} via API")
    db.commit()
    return JSONResponse({"id": row.id, "title": row.title,
                         "severity": row.severity, "status": row.status}, status_code=201)


@api_router.get("/documents")
def api_documents(request: Request, db: Session = Depends(get_db)):
    user, token = _api_principal(db, request)
    if user is None:
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    scope = _api_scope(db, user, request, token)
    status = (request.query_params.get("status") or "").strip() or None
    rows = services_operations.documents(db, scope, status=status)
    return {"documents": [{
        "id": row.id, "organization_id": row.organization_id,
        "title": row.title, "doc_type": row.doc_type,
        "reference": row.reference, "owner": row.owner,
        "issued_on": row.issued_on, "expires_on": row.expires_on,
        "status": row.status,
        **services_operations.document_reading(row),
    } for row in rows]}


@api_router.post("/documents")
async def api_document_create(request: Request, db: Session = Depends(get_db)):
    user, token = _api_principal(db, request)
    if user is None:
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    if not _api_can_write(token):
        return JSONResponse({"detail": "token is read-only"}, status_code=403)
    body = await request.json()
    try:
        org_id = token.organization_id if token is not None else int(body.get("organization_id"))
    except (TypeError, ValueError):
        return JSONResponse({"detail": "organization_id is required"}, status_code=400)
    if not services.can_access_org(db, user, org_id):
        return JSONResponse({"detail": "organization not found"}, status_code=404)
    try:
        row = services_operations.create_document(
            db, org_id, title=str(body.get("title") or ""),
            doc_type=str(body.get("doc_type") or "other"),
            reference=body.get("reference"), owner=body.get("owner"),
            issued_on=body.get("issued_on"), expires_on=body.get("expires_on"),
            note=body.get("note"), user_id=user.id)
    except ValueError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)
    services_ops.record_audit(
        db, action="operations.document.added", organization_id=org_id,
        user_id=user.id, detail=f"{row.title} expires {row.expires_on} via API")
    db.commit()
    return JSONResponse({"id": row.id, "title": row.title,
                         "expires_on": row.expires_on}, status_code=201)


@api_router.get("/export")
def api_export(request: Request, db: Session = Depends(get_db)):
    user, token = _api_principal(db, request)
    if user is None:
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    return services_operations.export_bundle(db, _api_scope(db, user, request, token))
