"""Operating ledger, incident register, compliance calendar, and data exchange."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import secrets
from calendar import monthrange
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from elipsis_api import models

METRIC_CATALOG: dict[str, dict[str, Any]] = {
    "on_time_delivery": {
        "label": "On-time delivery", "unit": "percent", "target": 95,
        "direction": "higher", "lane": "dispatch",
        "help": "Jobs delivered inside the promise window, as a share of all jobs.",
    },
    "cost_per_shipment": {
        "label": "Cost per shipment", "unit": "kes", "target": 18000,
        "direction": "lower", "lane": "cash",
        "help": "Direct operating cost divided by completed shipments.",
    },
    "invoice_accuracy": {
        "label": "Invoice accuracy", "unit": "percent", "target": 98,
        "direction": "higher", "lane": "cash",
        "help": "Invoices that reach the customer right the first time.",
    },
    "fleet_utilization": {
        "label": "Fleet utilisation", "unit": "percent", "target": 80,
        "direction": "higher", "lane": "capacity",
        "help": "Active vehicle hours as a share of available vehicle hours.",
    },
    "cash_conversion_days": {
        "label": "Cash conversion", "unit": "days", "target": 30,
        "direction": "lower", "lane": "cash",
        "help": "Days from job completion to cash received.",
    },
    "incident_rate": {
        "label": "Incident rate", "unit": "per100", "target": 2,
        "direction": "lower", "lane": "documents",
        "help": "Service failures per 100 shipments in the period.",
    },
    "claims_ratio": {
        "label": "Claims ratio", "unit": "percent", "target": 1,
        "direction": "lower", "lane": "customer",
        "help": "Claims value as a share of revenue for the period.",
    },
    "warehouse_accuracy": {
        "label": "Warehouse accuracy", "unit": "percent", "target": 99,
        "direction": "higher", "lane": "warehouse",
        "help": "Stock picks and counts that match the system without correction.",
    },
}

LANE_LABELS = {
    "dispatch": "Dispatch & handoffs",
    "documents": "Documents & systems",
    "capacity": "Fleet & capacity",
    "warehouse": "Warehouse & data",
    "cash": "Order-to-cash",
    "customer": "Customer & controls",
}

SEVERITIES = ("low", "medium", "high", "critical")
INCIDENT_STATUSES = ("open", "investigating", "resolved")
DOC_STATUSES = ("active", "renewing", "archived")
DOC_TYPES = ("licence", "insurance", "contract", "sop", "inspection", "other")
IMPORT_KINDS = ("metrics", "incidents", "documents")
MAX_IMPORT_ROWS = 500


def _today() -> date:
    return datetime.now(UTC).date()


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def _clean(value: Any, limit: int = 240) -> str | None:
    text = str(value or "").strip()
    return text[:limit] or None


def parse_day(raw: str | None, *, required: bool = False) -> date | None:
    text = (raw or "").strip()
    if not text:
        if required:
            raise ValueError("A date is required.")
        return None
    text = text[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Could not read date: {raw}")


def format_value(key: str, value: float | None) -> str:
    if value is None:
        return "—"
    unit = METRIC_CATALOG.get(key, {}).get("unit", "")
    if unit == "percent":
        return f"{value:,.1f}%"
    if unit == "kes":
        return f"KES {value:,.0f}"
    if unit == "days":
        return f"{value:,.1f} days"
    if unit == "per100":
        return f"{value:,.1f} / 100"
    return f"{value:,.1f}"


def metric_status(key: str, value: float | None) -> str:
    spec = METRIC_CATALOG.get(key)
    if spec is None or value is None or spec.get("target") is None:
        return "measured"
    target = float(spec["target"])
    if spec.get("direction") == "lower":
        if value <= target:
            return "good"
        return "watch" if value <= target * 1.2 else "risk"
    if value >= target:
        return "good"
    return "watch" if value >= target * 0.9 else "risk"


def _movement(key: str, delta: float | None) -> str:
    if delta is None or abs(delta) < 0.05:
        return "flat"
    lower_is_better = METRIC_CATALOG.get(key, {}).get("direction") == "lower"
    improving = delta < 0 if lower_is_better else delta > 0
    return "up" if improving else "down"


def _metric_query(org_ids: list[int] | None, key: str | None = None):
    query = select(models.OperationalMetric).order_by(
        models.OperationalMetric.period_end.desc(),
        models.OperationalMetric.id.desc())
    if org_ids is not None:
        query = query.where(models.OperationalMetric.organization_id.in_(org_ids or [0]))
    if key:
        query = query.where(models.OperationalMetric.metric_key == key)
    return query


def latest_metrics(db: Session, org_ids: list[int] | None,
                   key: str | None = None) -> list[dict[str, Any]]:
    """Latest reading per metric and organisation, with movement and status."""
    newest: dict[tuple[int, str], models.OperationalMetric] = {}
    previous: dict[tuple[int, str], models.OperationalMetric] = {}
    for row in db.scalars(_metric_query(org_ids, key)):
        pair = (row.organization_id, row.metric_key)
        if pair not in newest:
            newest[pair] = row
        elif pair not in previous:
            previous[pair] = row
    out = []
    for pair, row in newest.items():
        prev = previous.get(pair)
        delta = round(row.value - prev.value, 2) if prev is not None else None
        out.append({
            "metric": row,
            "value": row.value,
            "formatted": format_value(row.metric_key, row.value),
            "label": METRIC_CATALOG.get(row.metric_key, {}).get("label", row.metric_key),
            "unit": METRIC_CATALOG.get(row.metric_key, {}).get("unit", ""),
            "target": METRIC_CATALOG.get(row.metric_key, {}).get("target"),
            "target_formatted": format_value(row.metric_key,
                                             METRIC_CATALOG.get(row.metric_key, {}).get("target")),
            "status": metric_status(row.metric_key, row.value),
            "delta": delta,
            "movement": _movement(row.metric_key, delta),
            "previous": prev.value if prev is not None else None,
        })
    out.sort(key=lambda item: (METRIC_CATALOG.get(item["metric"].metric_key, {}).get("label", ""),
                               item["metric"].organization_id))
    return out


def metric_history(db: Session, org_ids: list[int] | None,
                   key: str | None = None, limit: int = 80) -> list[models.OperationalMetric]:
    return list(db.scalars(_metric_query(org_ids, key)))[:limit]


def spark_points(values: list[float]) -> list[int]:
    if not values:
        return []
    low, high = min(values), max(values)
    if high == low:
        return [60 for _ in values]
    return [round(18 + ((value - low) / (high - low)) * 82) for value in values]


def metric_spark(db: Session, org_ids: list[int] | None) -> dict[str, list[float]]:
    buckets: dict[str, dict[str, list[float]]] = {}
    for row in db.scalars(_metric_query(org_ids)):
        bucket = buckets.setdefault(row.metric_key, {})
        bucket.setdefault(row.period_end, []).append(row.value)
    out: dict[str, list[float]] = {}
    for key, periods in buckets.items():
        ordered = sorted(periods.items())[-8:]
        out[key] = [round(sum(values) / len(values), 2) for _, values in ordered]
    return out


def record_metric(db: Session, org_id: int, metric_key: str, value: float,
                  period_end: str, *, source: str = "manual",
                  note: str | None = None, user_id: int | None = None) -> models.OperationalMetric:
    if metric_key not in METRIC_CATALOG:
        raise ValueError("Choose a supported operating metric.")
    day = parse_day(period_end, required=True)
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Metric value must be a number.") from exc
    if number < 0 or number > 1_000_000_000:
        raise ValueError("Metric value is outside the supported range.")
    row = db.scalar(select(models.OperationalMetric).where(
        models.OperationalMetric.organization_id == org_id,
        models.OperationalMetric.metric_key == metric_key,
        models.OperationalMetric.period_end == day.isoformat()))
    if row is None:
        row = models.OperationalMetric(
            organization_id=org_id, metric_key=metric_key, value=number,
            period_end=day.isoformat(), source=source,
            note=_clean(note, 500), created_by=user_id)
        db.add(row)
    else:
        row.value = number
        row.source = source
        row.note = _clean(note, 500) or row.note
        row.created_by = user_id or row.created_by
    db.flush()
    return row


def incidents(db: Session, org_ids: list[int] | None,
              status: str | None = None) -> list[models.OperationalIncident]:
    query = select(models.OperationalIncident).order_by(
        models.OperationalIncident.occurred_on.desc(),
        models.OperationalIncident.id.desc())
    if org_ids is not None:
        query = query.where(models.OperationalIncident.organization_id.in_(org_ids or [0]))
    if status and status != "all":
        query = query.where(models.OperationalIncident.status == status)
    return list(db.scalars(query))


def documents(db: Session, org_ids: list[int] | None,
              status: str | None = None) -> list[models.ComplianceDocument]:
    query = select(models.ComplianceDocument).order_by(
        models.ComplianceDocument.expires_on,
        models.ComplianceDocument.id.desc())
    if org_ids is not None:
        query = query.where(models.ComplianceDocument.organization_id.in_(org_ids or [0]))
    if status and status != "all":
        query = query.where(models.ComplianceDocument.status == status)
    return list(db.scalars(query))


def document_reading(row: models.ComplianceDocument) -> dict[str, Any]:
    expires = parse_day(row.expires_on)
    days = (expires - _today()).days if expires else None
    if row.status == "archived":
        state, label = "muted", "Archived"
    elif days is not None and days < 0:
        state, label = "danger", f"Expired {abs(days)}d ago"
    elif days is not None and days <= 14:
        state, label = "danger", f"{days}d left"
    elif days is not None and days <= 30:
        state, label = "warn", f"{days}d left"
    else:
        state, label = "good", f"{(days if days is not None else 0)}d left"
    return {"days": days, "state": state, "label": label, "expires": expires}


def incident_counts(db: Session, org_ids: list[int] | None) -> dict[str, int]:
    rows = incidents(db, org_ids, status=None)
    open_rows = [r for r in rows if (r.status or "open") != "resolved"]
    return {
        "total": len(rows),
        "open": len(open_rows),
        "critical": sum(1 for r in open_rows if r.severity == "critical"),
        "high": sum(1 for r in open_rows if r.severity == "high"),
        "resolved": sum(1 for r in rows if (r.status or "") == "resolved"),
    }


def document_counts(db: Session, org_ids: list[int] | None) -> dict[str, int]:
    rows = documents(db, org_ids, status=None)
    expiring = expired = 0
    for row in rows:
        if row.status == "archived":
            continue
        reading = document_reading(row)
        if reading["days"] is not None and reading["days"] < 0:
            expired += 1
        elif reading["days"] is not None and reading["days"] <= 30:
            expiring += 1
    return {"total": len(rows), "expiring": expiring, "expired": expired}


def summary(db: Session, org_ids: list[int] | None) -> dict[str, Any]:
    metrics = latest_metrics(db, org_ids)
    sparks = metric_spark(db, org_ids)
    for item in metrics:
        item["spark"] = sparks.get(item["metric"].metric_key, [])
    at_target = sum(1 for item in metrics if item["status"] == "good")
    at_risk = sum(1 for item in metrics if item["status"] == "risk")
    incident_data = incident_counts(db, org_ids)
    document_data = document_counts(db, org_ids)
    lanes = []
    for key, label in LANE_LABELS.items():
        lane_metrics = [item for item in metrics
                        if METRIC_CATALOG.get(item["metric"].metric_key, {}).get("lane") == key]
        states = [item["status"] for item in lane_metrics]
        state = "risk" if "risk" in states else "watch" if "watch" in states else (
            "good" if states else "measured")
        lanes.append({"key": key, "label": label, "state": state,
                      "measured": len(lane_metrics)})
    return {
        "metrics": metrics,
        "measured": len(metrics),
        "at_target": at_target,
        "at_risk": at_risk,
        "incidents": incident_data,
        "documents": document_data,
        "lanes": lanes,
        "imports": import_history(db, org_ids, limit=6),
        "last_updated": max((item["metric"].period_end for item in metrics), default=None),
    }


def recent_activity(db: Session, org_ids: list[int] | None,
                    limit: int = 8) -> list[dict[str, Any]]:
    query = (
        select(models.AuditEvent)
        .where(models.AuditEvent.action.like("operations.%"))
        .order_by(models.AuditEvent.id.desc())
        .limit(limit)
    )
    if org_ids is not None:
        if not org_ids:
            return []
        query = query.where(models.AuditEvent.organization_id.in_(org_ids))
    out = []
    for row in db.scalars(query):
        org = db.get(models.Organization, row.organization_id) if row.organization_id else None
        user = db.get(models.User, row.user_id) if row.user_id else None
        out.append({"event": row, "organization": org, "user": user,
                    "label": row.action.replace("operations.", "").replace(".", " ").title()})
    return out


def create_incident(db: Session, org_id: int, *, title: str, lane: str = "dispatch",
                    severity: str = "medium", occurred_on: str | None = None,
                    shipment_ref: str | None = None,
                    customer_impact: str | None = None,
                    root_cause: str | None = None,
                    corrective_action: str | None = None,
                    owner: str | None = None,
                    user_id: int | None = None) -> models.OperationalIncident:
    cleaned_title = _clean(title, 200)
    if not cleaned_title:
        raise ValueError("Give the incident a short title.")
    day = parse_day(occurred_on, required=False) or _today()
    row = models.OperationalIncident(
        organization_id=org_id,
        lane=lane if lane in LANE_LABELS else "dispatch",
        title=cleaned_title,
        severity=severity if severity in SEVERITIES else "medium",
        status="open", occurred_on=day.isoformat(),
        shipment_ref=_clean(shipment_ref, 80),
        customer_impact=_clean(customer_impact, 600),
        root_cause=_clean(root_cause, 600),
        corrective_action=_clean(corrective_action, 600),
        owner=_clean(owner, 120), created_by=user_id)
    db.add(row)
    db.flush()
    return row


def resolve_incident(db: Session, org_id: int, incident_id: int,
                     note: str | None = None) -> models.OperationalIncident | None:
    row = db.get(models.OperationalIncident, incident_id)
    if row is None or row.organization_id != org_id:
        return None
    row.status = "resolved"
    row.resolved_at = _now()
    if note:
        row.corrective_action = _clean(note, 600) or row.corrective_action
    db.flush()
    return row


def promote_incident(db: Session, org_id: int, incident_id: int,
                     user_id: int | None = None) -> tuple[models.RoadmapItem | None, str]:
    row = db.get(models.OperationalIncident, incident_id)
    if row is None or row.organization_id != org_id:
        return None, "Incident not found."
    if row.action_item_id:
        item = db.get(models.RoadmapItem, row.action_item_id)
        return item, "Already on the action board."
    assessment = db.scalar(select(models.Assessment).where(
        models.Assessment.organization_id == org_id,
        models.Assessment.status == "completed").order_by(models.Assessment.id.desc()))
    if assessment is None:
        return None, "Complete an assessment before promoting an incident to the action plan."
    due = (_today() + timedelta(days=14)).isoformat()
    item = models.RoadmapItem(
        assessment_id=assessment.id, phase=1,
        title=f"Resolve: {row.title[:150]}",
        solution=row.corrective_action or row.root_cause or "Agree and close the corrective action.",
        complexity="medium", priority=9.0, horizon="now",
        kpi="Incident recurrence", owner=row.owner or "Operations lead",
        due_date=due, status="not_started",
        notes=f"Promoted from incident #{row.id} on {row.occurred_on}.",
        created_at=_now(), updated_at=_now())
    db.add(item)
    db.flush()
    row.action_item_id = item.id
    return item, ""


def create_document(db: Session, org_id: int, *, title: str,
                    doc_type: str = "licence", reference: str | None = None,
                    owner: str | None = None, issued_on: str | None = None,
                    expires_on: str | None = None, note: str | None = None,
                    user_id: int | None = None) -> models.ComplianceDocument:
    cleaned = _clean(title, 200)
    if not cleaned:
        raise ValueError("Give the document a short title.")
    expiry = parse_day(expires_on, required=True)
    issued = parse_day(issued_on)
    row = models.ComplianceDocument(
        organization_id=org_id, title=cleaned,
        doc_type=doc_type if doc_type in DOC_TYPES else "other",
        reference=_clean(reference, 120), owner=_clean(owner, 120),
        issued_on=issued.isoformat() if issued else None,
        expires_on=expiry.isoformat(), status="active",
        note=_clean(note, 500), created_by=user_id)
    db.add(row)
    db.flush()
    return row


def renew_document(db: Session, org_id: int, document_id: int,
                   expires_on: str) -> models.ComplianceDocument | None:
    row = db.get(models.ComplianceDocument, document_id)
    if row is None or row.organization_id != org_id:
        return None
    row.expires_on = parse_day(expires_on, required=True).isoformat()
    row.status = "active"
    db.flush()
    return row


def archive_document(db: Session, org_id: int, document_id: int) -> bool:
    row = db.get(models.ComplianceDocument, document_id)
    if row is None or row.organization_id != org_id:
        return False
    row.status = "archived"
    return True


def _upsert_metric_row(db: Session, org_id: int, key: str, value: float,
                       period_end: str, note: str | None, source: str):
    if key not in METRIC_CATALOG:
        raise ValueError(f"unknown metric '{key}'")
    day = parse_day(period_end, required=True)
    number = float(value)
    if number < 0:
        raise ValueError("value must be positive")
    row = db.scalar(select(models.OperationalMetric).where(
        models.OperationalMetric.organization_id == org_id,
        models.OperationalMetric.metric_key == key,
        models.OperationalMetric.period_end == day.isoformat()))
    if row is None:
        row = models.OperationalMetric(
            organization_id=org_id, metric_key=key, value=number,
            period_end=day.isoformat(), source=source, note=_clean(note, 500))
        db.add(row)
    else:
        row.value = number
        row.source = source
        if note:
            row.note = _clean(note, 500)
    return row


def import_csv(db: Session, org_id: int, kind: str, filename: str | None,
               content: bytes, user_id: int | None = None) -> models.DataImport:
    if kind not in IMPORT_KINDS:
        raise ValueError("Choose metrics, incidents, or documents.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must be UTF-8 encoded.") from exc
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV has no header row.")
    rows = list(reader)[:MAX_IMPORT_ROWS]
    errors: list[dict[str, Any]] = []
    imported = 0
    for index, raw in enumerate(rows, start=2):
        try:
            if kind == "metrics":
                _upsert_metric_row(
                    db, org_id, (raw.get("metric_key") or "").strip(),
                    float((raw.get("value") or "").strip()),
                    (raw.get("period_end") or "").strip(), raw.get("note"), "csv")
            elif kind == "incidents":
                create_incident(
                    db, org_id, title=raw.get("title") or "",
                    lane=(raw.get("lane") or "dispatch").strip().lower(),
                    severity=(raw.get("severity") or "medium").strip().lower(),
                    occurred_on=raw.get("occurred_on"),
                    shipment_ref=raw.get("shipment_ref"),
                    customer_impact=raw.get("customer_impact"),
                    root_cause=raw.get("root_cause"),
                    corrective_action=raw.get("corrective_action"),
                    owner=raw.get("owner"), user_id=user_id)
            else:
                create_document(
                    db, org_id, title=raw.get("title") or "",
                    doc_type=(raw.get("doc_type") or "other").strip().lower(),
                    reference=raw.get("reference"), owner=raw.get("owner"),
                    issued_on=raw.get("issued_on"),
                    expires_on=raw.get("expires_on"), note=raw.get("note"),
                    user_id=user_id)
            imported += 1
        except (ValueError, TypeError) as exc:
            if len(errors) < 20:
                errors.append({"row": index, "error": str(exc)[:200]})
    batch = models.DataImport(
        organization_id=org_id, kind=kind, filename=_clean(filename, 180),
        row_count=len(rows), imported_count=imported,
        skipped_count=max(0, len(rows) - imported),
        status="imported" if imported else "failed",
        errors=json.dumps(errors) if errors else None,
        created_by=user_id)
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def import_history(db: Session, org_ids: list[int] | None,
                   limit: int = 20) -> list[models.DataImport]:
    query = select(models.DataImport).order_by(models.DataImport.id.desc()).limit(limit)
    if org_ids is not None:
        if not org_ids:
            return []
        query = query.where(models.DataImport.organization_id.in_(org_ids))
    return list(db.scalars(query))


def import_errors(batch: models.DataImport) -> list[dict[str, Any]]:
    try:
        return json.loads(batch.errors or "[]")
    except json.JSONDecodeError:
        return []


def ensure_sample_data(db: Session, org_id: int, user_id: int | None = None) -> dict[str, int]:
    """Add a coherent six-month operating history once, for demos and first-run pages."""
    created = {"metrics": 0, "incidents": 0, "documents": 0}
    existing_metrics = db.scalar(select(models.OperationalMetric.id).where(
        models.OperationalMetric.organization_id == org_id).limit(1))
    if existing_metrics is None:
        series = {
            "on_time_delivery": [80, 82, 84, 86, 88, 91],
            "cost_per_shipment": [26100, 25200, 24400, 23900, 23100, 22400],
            "invoice_accuracy": [89, 91, 93, 94, 95, 96],
            "fleet_utilization": [58, 61, 64, 68, 71, 74],
            "cash_conversion_days": [62, 58, 54, 49, 45, 42],
            "incident_rate": [6.4, 5.8, 5.1, 4.4, 3.8, 3.1],
            "claims_ratio": [2.8, 2.5, 2.2, 1.9, 1.6, 1.4],
            "warehouse_accuracy": [91, 92, 93, 94, 95, 96],
        }
        first = _today().replace(day=1)
        periods = []
        for back in range(5, -1, -1):
            year = first.year
            month = first.month - back
            while month <= 0:
                month += 12
                year -= 1
            periods.append(date(year, month, monthrange(year, month)[1]).isoformat())
        for key, values in series.items():
            for period, value in zip(periods, values, strict=True):
                _upsert_metric_row(db, org_id, key, value, period, "Sample operating ledger", "sample")
                created["metrics"] += 1
    if db.scalar(select(models.OperationalIncident.id).where(
            models.OperationalIncident.organization_id == org_id).limit(1)) is None:
        today = _today()
        samples = [
            ("Mombasa release delay", "dispatch", "high", "open", 2,
             "MBS-4821", "Two customer deliveries missed the morning window.",
             "Release papers arrived after the transporter cut-off.",
             "Pre-clear release documents the day before loading."),
            ("Invoice mismatch on consolidated load", "cash", "medium", "investigating", 6,
             "NBO-1187", "Customer held payment for nine days.",
             "Fuel surcharge added after the invoice was approved.",
             "Lock the quote before dispatch and check margin at invoicing."),
            ("Warehouse stock variance", "warehouse", "critical", "open", 1,
             "WH-220", "Pick shortage delayed a same-day order.",
             "Inbound count was not reconciled to the system.",
             "Introduce blind receiving and a daily variance review."),
        ]
        for title, lane, severity, status, days_ago, ref, impact, cause, action in samples:
            row = create_incident(
                db, org_id, title=title, lane=lane, severity=severity,
                occurred_on=(today - timedelta(days=days_ago)).isoformat(),
                shipment_ref=ref, customer_impact=impact, root_cause=cause,
                corrective_action=action, owner="Operations lead", user_id=user_id)
            row.status = status
            created["incidents"] += 1
    if db.scalar(select(models.ComplianceDocument.id).where(
            models.ComplianceDocument.organization_id == org_id).limit(1)) is None:
        today = _today()
        docs = [
            ("Goods-in-transit insurance", "insurance", "GIT-2026-14", 28, 365),
            ("NTSA fleet inspection", "inspection", "NTSA-FL-882", 74, 365),
            ("Transport operating licence", "licence", "TOL-NRB-441", 12, 365),
        ]
        for title, doc_type, ref, expires_in, issued_days in docs:
            create_document(
                db, org_id, title=title, doc_type=doc_type, reference=ref,
                owner="Compliance lead",
                issued_on=(today - timedelta(days=issued_days)).isoformat(),
                expires_on=(today + timedelta(days=expires_in)).isoformat(),
                note="Sample compliance calendar entry.", user_id=user_id)
            created["documents"] += 1
    db.commit()
    return created


def notifications(db: Session, org_ids: list[int] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in incidents(db, org_ids, status=None):
        if (row.status or "open") == "resolved":
            continue
        if row.severity not in {"critical", "high"}:
            continue
        org = db.get(models.Organization, row.organization_id)
        out.append({
            "kind": "incident", "severity": "danger" if row.severity == "critical" else "warn",
            "title": f"{row.severity.title()} incident: {row.title}",
            "detail": f"{org.name if org else 'Organisation'} · {row.occurred_on}",
            "url": "/operations/incidents",
            "ref": f"incident:{row.id}",
        })
    for row in documents(db, org_ids, status=None):
        if row.status == "archived":
            continue
        reading = document_reading(row)
        if reading["days"] is None or reading["days"] > 30:
            continue
        org = db.get(models.Organization, row.organization_id)
        out.append({
            "kind": "document", "severity": "danger" if reading["days"] < 0 else "warn",
            "title": f"{row.title} {reading['label']}",
            "detail": f"{org.name if org else 'Organisation'} · expires {row.expires_on}",
            "url": "/operations/documents",
            "ref": f"document:{row.id}",
        })
    return out[:10]


def export_bundle(db: Session, org_ids: list[int] | None) -> dict[str, Any]:
    orgs = []
    if org_ids:
        orgs = list(db.scalars(select(models.Organization).where(
            models.Organization.id.in_(org_ids)).order_by(models.Organization.name)))
    org_names = {org.id: org.name for org in orgs}
    metric_rows = list(db.scalars(_metric_query(org_ids)))
    incident_rows = incidents(db, org_ids, status=None)
    document_rows = documents(db, org_ids, status=None)
    return {
        "generated_at": _now(),
        "organizations": [{"id": org.id, "name": org.name} for org in orgs],
        "metrics": [{
            "id": row.id, "organization": org_names.get(row.organization_id),
            "metric_key": row.metric_key,
            "label": METRIC_CATALOG.get(row.metric_key, {}).get("label", row.metric_key),
            "value": row.value, "period_end": row.period_end,
            "source": row.source, "note": row.note,
        } for row in metric_rows],
        "incidents": [{
            "id": row.id, "organization": org_names.get(row.organization_id),
            "title": row.title, "lane": row.lane, "severity": row.severity,
            "status": row.status, "occurred_on": row.occurred_on,
            "shipment_ref": row.shipment_ref, "owner": row.owner,
            "root_cause": row.root_cause, "corrective_action": row.corrective_action,
            "action_item_id": row.action_item_id,
        } for row in incident_rows],
        "documents": [{
            "id": row.id, "organization": org_names.get(row.organization_id),
            "title": row.title, "doc_type": row.doc_type,
            "reference": row.reference, "owner": row.owner,
            "issued_on": row.issued_on, "expires_on": row.expires_on,
            "status": row.status,
        } for row in document_rows],
    }


def search_operations(db: Session, org_ids: list[int] | None, query_text: str,
                      limit: int = 6) -> list[dict[str, Any]]:
    q = (query_text or "").strip()
    if len(q) < 2 or org_ids == []:
        return []
    like = f"%{q}%"
    out: list[dict[str, Any]] = []
    incident_query = select(models.OperationalIncident).where(or_(
        models.OperationalIncident.title.ilike(like),
        models.OperationalIncident.shipment_ref.ilike(like),
        models.OperationalIncident.owner.ilike(like),
        models.OperationalIncident.root_cause.ilike(like),
    )).order_by(models.OperationalIncident.id.desc()).limit(limit)
    if org_ids is not None:
        incident_query = incident_query.where(
            models.OperationalIncident.organization_id.in_(org_ids))
    for row in db.scalars(incident_query):
        org = db.get(models.Organization, row.organization_id)
        out.append({"kind": "Incident", "title": row.title,
                    "detail": f"{org.name if org else ''} · {row.severity} · {row.status}",
                    "url": "/operations/incidents"})
    doc_query = select(models.ComplianceDocument).where(or_(
        models.ComplianceDocument.title.ilike(like),
        models.ComplianceDocument.reference.ilike(like),
        models.ComplianceDocument.owner.ilike(like),
    )).order_by(models.ComplianceDocument.expires_on).limit(limit)
    if org_ids is not None:
        doc_query = doc_query.where(models.ComplianceDocument.organization_id.in_(org_ids))
    for row in db.scalars(doc_query):
        org = db.get(models.Organization, row.organization_id)
        out.append({"kind": "Document", "title": row.title,
                    "detail": f"{org.name if org else ''} · expires {row.expires_on}",
                    "url": "/operations/documents"})
    return out[:limit]



def _token_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_api_token(db: Session, org_id: int, user_id: int | None,
                     name: str, scopes: str = "read,write") -> tuple[models.ApiToken, str]:
    cleaned = _clean(name, 120) or "Integration token"
    chosen = ",".join(scope for scope in ("read", "write") if scope in (scopes or ""))
    if not chosen:
        chosen = "read"
    raw = f"elps_{secrets.token_urlsafe(32)}"
    row = models.ApiToken(
        organization_id=org_id, user_id=user_id, name=cleaned,
        prefix=raw[:13], token_hash=_token_hash(raw), scopes=chosen,
        created_at=_now())
    db.add(row)
    db.flush()
    return row, raw


def api_tokens(db: Session, org_ids: list[int] | None) -> list[models.ApiToken]:
    query = select(models.ApiToken).where(
        models.ApiToken.revoked_at.is_(None)).order_by(models.ApiToken.id.desc())
    if org_ids is not None:
        if not org_ids:
            return []
        query = query.where(models.ApiToken.organization_id.in_(org_ids))
    return list(db.scalars(query))


def authenticate_api_token(db: Session, raw: str | None) -> models.ApiToken | None:
    token = (raw or "").strip()
    if not token.startswith("elps_"):
        return None
    row = db.scalar(select(models.ApiToken).where(
        models.ApiToken.token_hash == _token_hash(token),
        models.ApiToken.revoked_at.is_(None)))
    if row is None:
        return None
    row.last_used_at = _now()
    return row


def revoke_api_token(db: Session, org_id: int, token_id: int) -> bool:
    row = db.get(models.ApiToken, token_id)
    if row is None or row.organization_id != org_id:
        return False
    row.revoked_at = _now()
    return True
