"""Anonymised cohort snapshots and verifiable readiness badges."""

from __future__ import annotations

import base64
import hashlib
import hmac
import html
import json
from datetime import date
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from elipsis_api import benchmarks, models, security


def cohort_snapshot(db: Session, organization) -> dict:
    if organization is None:
        return {"available": False, "sample": 0, "minimum": benchmarks.MIN_COHORT}
    industry = (organization.industry or "").strip()
    if not industry:
        return {"available": False, "sample": 0, "minimum": benchmarks.MIN_COHORT,
                "industry": None, "band": None}
    band = benchmarks.size_band(organization.employee_count)
    rows = list(db.scalars(select(models.Assessment).where(
        models.Assessment.status == "completed",
        models.Assessment.readiness_index.is_not(None),
    )))
    values = []
    for row in rows:
        org = db.get(models.Organization, row.organization_id)
        if not org or (org.industry or "").strip().lower() != industry.lower():
            continue
        if band and benchmarks.size_band(org.employee_count) != band:
            continue
        values.append(float(row.readiness_index))
    values.sort()
    if len(values) < benchmarks.MIN_COHORT:
        return {"available": False, "sample": len(values),
                "minimum": benchmarks.MIN_COHORT, "industry": industry, "band": band}
    buckets = [
        {"label": "0–34 · fragile", "count": sum(1 for v in values if v < 35)},
        {"label": "35–54 · person-dependent", "count": sum(1 for v in values if 35 <= v < 55)},
        {"label": "55–74 · systematising", "count": sum(1 for v in values if 55 <= v < 75)},
        {"label": "75–100 · structurally ready", "count": sum(1 for v in values if v >= 75)},
    ]
    p25 = values[max(0, int(len(values) * 0.25) - 1)]
    p75 = values[min(len(values) - 1, int(len(values) * 0.75))]
    return {
        "available": True, "sample": len(values), "minimum": benchmarks.MIN_COHORT,
        "industry": industry, "band": band,
        "median": round(median(values), 1), "p25": round(p25, 1),
        "p75": round(p75, 1), "best": round(max(values), 1),
        "lowest": round(min(values), 1), "buckets": buckets,
    }


def _secret() -> bytes:
    return security._session_secret().encode("utf-8")


def _sign(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    body = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    sig = hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).hexdigest()[:32]
    return f"{body}.{sig}"


def _unsign(token: str) -> dict | None:
    if not token or token.count(".") != 1:
        return None
    body, sig = token.rsplit(".", 1)
    expected = hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(expected, sig):
        return None
    try:
        padded = body + "=" * (-len(body) % 4)
        return json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
    except (ValueError, TypeError):
        return None


def badge_for(organization, assessment, result: dict, benchmark: dict | None) -> dict:
    score = float(result.get("readiness_index") or 0)
    answered = int(result.get("answered") or 0)
    total = int(result.get("total") or 0)
    confidence = float(result.get("confidence_index") or 0)
    eligible = bool(
        assessment is not None
        and (assessment.status or "") == "completed"
        and total > 0 and answered >= total
        and confidence >= 60
    )
    percentile = benchmark.get("percentile") if benchmark and benchmark.get("available") else None
    if not eligible:
        tier = "Not yet eligible"
    elif percentile is not None and percentile >= 75 and score >= 60:
        tier = "Cohort leader"
    elif benchmark and benchmark.get("available") and score >= float(benchmark.get("median") or 0):
        tier = "Above peer median"
    else:
        tier = "Baseline recorded"
    payload = {
        "v": 1,
        "org": getattr(organization, "name", None) or "Organisation",
        "score": round(score, 1),
        "tier": tier,
        "percentile": percentile,
        "sample": benchmark.get("sample") if benchmark else None,
        "issued": date.today().isoformat(),
        "assessment": getattr(assessment, "id", None),
    }
    return {
        "eligible": eligible, "tier": tier, "score": round(score, 1),
        "percentile": percentile, "sample": benchmark.get("sample") if benchmark else None,
        "token": _sign(payload) if eligible else None,
        "payload": payload,
        "criteria": [
            "Completed assessment with every question answered.",
            "Confidence index of at least 60.",
            "Peer tier uses only cohorts with at least five comparable assessments.",
        ],
    }


def verify_token(token: str) -> dict | None:
    return _unsign(token)


def badge_svg(payload: dict) -> str:
    org = html.escape(str(payload.get("org") or "Organisation"))
    score = html.escape(str(payload.get("score") or "—"))
    tier = html.escape(str(payload.get("tier") or "Baseline"))
    issued = html.escape(str(payload.get("issued") or ""))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="720" height="240" viewBox="0 0 720 240" role="img" aria-label="Elipsis readiness badge for {org}">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#10243e"/><stop offset="1" stop-color="#0a1729"/>
    </linearGradient>
  </defs>
  <rect width="720" height="240" rx="24" fill="url(#g)"/>
  <rect x="1" y="1" width="718" height="238" rx="23" fill="none" stroke="#d9b45b" stroke-opacity=".55"/>
  <circle cx="96" cy="120" r="52" fill="none" stroke="#d9b45b" stroke-width="6"/>
  <text x="96" y="130" text-anchor="middle" fill="#f8fafc" font-family="Georgia,serif" font-size="34" font-weight="700">{score}</text>
  <text x="172" y="78" fill="#d9b45b" font-family="Arial,sans-serif" font-size="13" letter-spacing="3">ELIPSIS READINESS</text>
  <text x="172" y="122" fill="#f8fafc" font-family="Georgia,serif" font-size="30">{org}</text>
  <text x="172" y="157" fill="#cbd5e1" font-family="Arial,sans-serif" font-size="17">{tier}</text>
  <text x="172" y="190" fill="#94a3b8" font-family="Arial,sans-serif" font-size="12">Issued {issued} · Verify at elipsis.ai/verify</text>
</svg>'''
