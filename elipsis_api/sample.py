"""Deterministic sample assessment result for marketing and demos.

Does not touch the database. Uses the same readiness engine as live assessments
so the sample report is structurally identical to a real one.
"""

from __future__ import annotations

from typing import Any

from constants import SUBDOMAIN_PILLAR
from elipsis_questions import QUESTIONS
from readiness import compute as _compute

SAMPLE_ORG = {
    "name": "Demo Logistics Ltd",
    "industry": "Logistics",
    "department": "Operations",
    "country": "Kenya",
    "city": "Nairobi",
    "employee_count": 120,
}


def sample_result(staff: int | None = None) -> dict[str, Any]:
    """Full compute() payload for a realistic mid-maturity organisation."""
    headcount = staff if staff is not None else SAMPLE_ORG["employee_count"]
    questions: list[dict[str, Any]] = []
    answers: dict[int, dict[str, Any]] = {}

    for idx, item in enumerate(QUESTIONS, start=1):
        questions.append(
            dict(
                id=idx,
                code=item["code"],
                subdomain=item["subdomain"],
                pillar=SUBDOMAIN_PILLAR[item["subdomain"]],
                weight=item["weight"],
                evidence_required=bool(item["evidence_required"]),
            )
        )
        # Pattern produces a mixed but believable profile (mostly 2–4).
        score = 2 + ((idx * 7) % 3)
        answers[idx] = {"score": score, "evidence": "documented"}

    result = _compute(questions, answers, staff=headcount)
    result["sample"] = True
    result["organization"] = dict(SAMPLE_ORG)
    return result
