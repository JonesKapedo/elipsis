"""Logistics operating lens over the 21 Elipsis subdomains."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from constants import SUBDOMAIN_LABELS
from elipsis_api import models

LANES = (
    {
        "key": "dispatch",
        "label": "Dispatch & handoffs",
        "question": "Do jobs move between people without rework?",
        "subdomains": ("OPS", "WFL", "RSU"),
    },
    {
        "key": "documents",
        "label": "Documents & systems",
        "question": "Can a document follow the shipment without chasing?",
        "subdomains": ("ADO", "DWF", "INM", "ECO", "INC"),
    },
    {
        "key": "capacity",
        "label": "Fleet & capacity",
        "question": "Can you see capacity before you commit to a job?",
        "subdomains": ("SCA", "KPD", "GCA"),
    },
    {
        "key": "warehouse",
        "label": "Warehouse & data",
        "question": "Is stock and job data trusted at the point of use?",
        "subdomains": ("COL", "DQU", "RPM"),
    },
    {
        "key": "cash",
        "label": "Order-to-cash",
        "question": "Does every job turn into a clean invoice and payment?",
        "subdomains": ("MAN", "REP", "RUL"),
    },
    {
        "key": "customer",
        "label": "Customer & controls",
        "question": "Do customers get status updates without calling?",
        "subdomains": ("CSV", "KMA", "PRD", "SEC"),
    },
)


def _reading(score: float | None) -> str:
    if score is None:
        return "No completed assessment yet"
    if score < 40:
        return "Fragile — fix before growth"
    if score < 60:
        return "Patchy — standardise the handoff"
    if score < 75:
        return "Working — tighten the exceptions"
    return "Strong — protect and measure"


def _lane_consequence(key: str) -> str:
    return {
        "dispatch": "Jobs wait for people instead of moving on their own.",
        "documents": "Proof is chased after the fact instead of following the load.",
        "capacity": "Commitments are made before the available capacity is visible.",
        "warehouse": "Stock and job data are doubted at the point of decision.",
        "cash": "Completed work leaks margin before it becomes cash.",
        "customer": "Customers call for status that should already be visible.",
    }.get(key, "The handoff is still person-dependent.")


def _lane_reading(lane: dict, values: list[tuple[str, float]], score: float | None) -> str:
    if score is None or not values:
        return "No completed assessment yet"
    code, weakest = min(values, key=lambda row: row[1])
    label = SUBDOMAIN_LABELS.get(code, code)
    return (f"Weakest link: {label} at {weakest:.0f}/100. "
            f"{_lane_consequence(lane['key'])}")


def latest_completed_ids(db: Session, org_ids: list[int] | None = None) -> list[int]:
    rows = db.scalars(select(models.Assessment).where(
        models.Assessment.status == "completed").order_by(
        models.Assessment.id.desc())).all()
    seen: set[int] = set()
    ids: list[int] = []
    for assessment in rows:
        if org_ids is not None and assessment.organization_id not in org_ids:
            continue
        if assessment.organization_id in seen:
            continue
        seen.add(assessment.organization_id)
        ids.append(assessment.id)
    return ids


def snapshot(db: Session, assessment_ids: list[int] | None = None,
             org_ids: list[int] | None = None) -> dict:
    ids = assessment_ids
    if ids is None:
        ids = latest_completed_ids(db, org_ids)
    totals: dict[str, list[float]] = {}
    if ids:
        for row in db.scalars(select(models.SubdomainScore).where(
                models.SubdomainScore.assessment_id.in_(ids))):
            if row.score is None:
                continue
            bucket = totals.setdefault(row.subdomain, [0.0, 0])
            bucket[0] += row.score
            bucket[1] += 1
    scores = {code: round(total / count, 1)
              for code, (total, count) in totals.items() if count}

    lanes = []
    for lane in LANES:
        values = [(code, scores[code]) for code in lane["subdomains"] if code in scores]
        score = round(sum(value for _, value in values) / len(values), 1) if values else None
        lanes.append({**lane, "score": score,
                      "reading": _lane_reading(lane, values, score)})
    measured = [lane for lane in lanes if lane["score"] is not None]
    weakest = min(measured, key=lambda lane: lane["score"]) if measured else None
    return {"lanes": lanes, "weakest": weakest, "measured": len(measured)}
