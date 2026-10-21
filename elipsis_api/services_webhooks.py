"""Signed, best-effort webhook delivery for workspace events."""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import socket
from datetime import UTC, datetime
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from elipsis_api import models, security

ALLOWED_EVENTS = {
    "action.updated", "assessment.completed", "review.due", "webhook.test",
    "metric.recorded", "incident.opened", "data.imported",
}


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    if host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".local"):
        return False
    try:
        for info in socket.getaddrinfo(host, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
    except (socket.gaierror, ValueError):
        return False
    return True


def endpoints(db: Session, org_ids: list[int]) -> list[models.WebhookEndpoint]:
    if not org_ids:
        return []
    return list(db.scalars(select(models.WebhookEndpoint).where(
        models.WebhookEndpoint.organization_id.in_(org_ids)
    ).order_by(models.WebhookEndpoint.id.desc())))


def create_endpoint(db: Session, org_id: int, url: str, events: list[str],
                    user_id: int | None) -> tuple[models.WebhookEndpoint | None, str]:
    url = (url or "").strip()
    if not valid_url(url):
        return None, "Enter a public http(s) URL."
    chosen = sorted({e for e in events if e in ALLOWED_EVENTS}) or ["action.updated"]
    row = models.WebhookEndpoint(
        organization_id=org_id, url=url, secret=security.new_token()[:40],
        events=",".join(chosen), active=True, created_by=user_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row, ""


def delete_endpoint(db: Session, org_ids: list[int], endpoint_id: int) -> bool:
    row = db.get(models.WebhookEndpoint, endpoint_id)
    if row is None or row.organization_id not in org_ids:
        return False
    db.delete(row)
    db.commit()
    return True


def matching_endpoints(db: Session, org_id: int, event: str) -> list[models.WebhookEndpoint]:
    rows = endpoints(db, [org_id])
    return [r for r in rows if r.active and event in (r.events or "").split(",")]


def _signature(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


async def deliver_event(endpoint_id: int, event: str, payload: dict) -> None:
    from elipsis_api.database import SessionLocal
    db = SessionLocal()
    try:
        endpoint = db.get(models.WebhookEndpoint, endpoint_id)
        if endpoint is None or not endpoint.active:
            return
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        delivery = models.WebhookDelivery(
            endpoint_id=endpoint.id, event=event, payload=body.decode(),
            status="sending")
        db.add(delivery)
        db.commit()
        db.refresh(delivery)
        try:
            import httpx

            async with httpx.AsyncClient(timeout=6.0, follow_redirects=False) as client:
                response = await client.post(
                    endpoint.url, content=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-Elipsis-Event": event,
                        "X-Elipsis-Signature": _signature(endpoint.secret, body),
                        "User-Agent": "Elipsis-Webhooks/1",
                    })
            delivery.response_code = response.status_code
            delivery.status = "delivered" if 200 <= response.status_code < 300 else "failed"
            delivery.error = None if delivery.status == "delivered" else response.text[:400]
            delivery.delivered_at = _now() if delivery.status == "delivered" else None
        except Exception as exc:
            delivery.status = "failed"
            delivery.error = str(exc)[:400]
        db.commit()
    finally:
        db.close()
