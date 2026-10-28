"""Dashboard, share links, org comparison, guided demo."""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from constants import PILLAR_LABELS, PILLAR_WEIGHTS
from elipsis_api import models, security
from elipsis_api.services_core import (
    DEMO_DEPARTMENTS,
    _now,
    compute,
    get_bank,
    get_questions,
    list_assessments,
    save,
)


def dashboard_data(db: Session, limit: int = 8) -> dict[str, Any]:
    rows = list_assessments(db)
    completed = [r for r in rows if r.get("status") == "completed"
                 and r.get("readiness_index") is not None]

    pillar_totals = {}
    for row in completed:
        metrics = db.scalars(select(models.MetricScore).where(
            models.MetricScore.assessment_id == row["id"])).all()
        for m in metrics:
            if m.score is None:
                continue
            bucket = pillar_totals.setdefault(m.pillar, [0.0, 0])
            bucket[0] += m.score
            bucket[1] += 1

    portfolio_pillars = {code: round(total / count, 1)
                         for code, (total, count) in pillar_totals.items() if count}

    scores = [r["readiness_index"] for r in completed]
    summary = dict(
        total=len(rows),
        completed=len(completed),
        in_progress=len(rows) - len(completed),
        average=round(sum(scores) / len(scores), 1) if scores else None,
        best=max(scores) if scores else None,
        lowest=min(scores) if scores else None,
        bands=_band_counts(completed),
    )
    return dict(summary=summary, rows=rows[:limit],
                portfolio_pillars=portfolio_pillars, all_completed=completed)


def _band_counts(completed: list[dict[str, Any]]) -> dict[str, int]:
    counts = {}
    for row in completed:
        band = row.get("maturity_band") or "Unknown"
        counts[band] = counts.get(band, 0) + 1
    return counts


def reset_demo_data(db: Session, org_ids: list[int] | None = None):
    stmt = select(models.Assessment.id)
    if org_ids is not None:
        if not org_ids:
            return 0
        stmt = stmt.where(models.Assessment.organization_id.in_(org_ids))
    assessment_ids = list(db.scalars(stmt))
    removed = 0
    if assessment_ids:
        for model in (models.Answer, models.MetricScore, models.PillarScore,
                      models.SubdomainScore, models.PainPoint,
                      models.Recommendation, models.FinancialModel, models.Report,
                      models.ShareLink, models.AssessmentAssumption,
                      models.EvidenceAttachment, models.RoadmapItem,
                      models.AuditEvent):
            try:
                if hasattr(model, "assessment_id"):
                    db.execute(delete(model).where(model.assessment_id.in_(assessment_ids)))
            except Exception:
                pass
        db.execute(delete(models.ShareLink).where(
            models.ShareLink.assessment_id.in_(assessment_ids)))
        db.execute(delete(models.Assessment).where(models.Assessment.id.in_(assessment_ids)))
        removed = len(assessment_ids)
    db.commit()
    return removed


def create_share_link(db: Session, assessment_id: int, user_id: int | None = None,
                      label: str | None = None, expires_days: int | None = 30) -> models.ShareLink:
    assessment = db.get(models.Assessment, assessment_id)
    if assessment is None:
        raise ValueError("assessment not found")
    if assessment.status != "completed":
        raise ValueError("only completed assessments can be shared")
    token = security.new_token()
    expires_at = None
    if expires_days:
        from datetime import UTC, datetime, timedelta
        expires_at = (datetime.now(UTC) + timedelta(days=max(1, min(365, int(expires_days))))).strftime("%Y-%m-%d %H:%M:%S")
    link = models.ShareLink(
        token=token,
        assessment_id=assessment_id,
        created_by=user_id,
        label=label or "Board pack",
        expires_at=expires_at,
        created_at=_now(),
    )
    db.add(link)
    db.commit()
    return link


def resolve_share_token(db: Session, token: str):
    link = db.get(models.ShareLink, token)
    if link is None:
        return None, None, None
    if link.expires_at:
        from datetime import UTC, datetime
        try:
            if datetime.strptime(link.expires_at, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC) < datetime.now(UTC):
                return None, None, None
        except ValueError:
            pass
    assessment, result = compute(db, link.assessment_id)
    return link, assessment, result


def list_organizations(db: Session) -> list[models.Organization]:
    return list(db.scalars(select(models.Organization).order_by(models.Organization.name)))


def department_comparison(db: Session, organization_id: int) -> dict[str, Any]:
    """Side-by-side view of completed assessments by department for one org."""
    org = db.get(models.Organization, organization_id)
    if org is None:
        return {"organization": None, "rows": [], "pillars": [], "average": None}

    rows = db.execute(
        select(models.Assessment, models.Department.name)
        .join(models.Department, models.Department.id == models.Assessment.department_id,
              isouter=True)
        .where(
            models.Assessment.organization_id == organization_id,
            models.Assessment.status == "completed",
        )
        .order_by(models.Assessment.readiness_index.desc())
    ).all()

    units = []
    pillar_codes = list(PILLAR_WEIGHTS.keys())
    for assessment, dept_name in rows:
        pillars = {
            p.pillar: p.score
            for p in db.scalars(select(models.PillarScore).where(
                models.PillarScore.assessment_id == assessment.id))
        }
        financial = db.scalar(select(models.FinancialModel).where(
            models.FinancialModel.assessment_id == assessment.id))
        weakest = min(pillars.items(), key=lambda kv: kv[1])[0] if pillars else None
        units.append({
            "assessment_id": assessment.id,
            "department": dept_name or "Organisation-wide",
            "respondent": assessment.respondent,
            "readiness_index": assessment.readiness_index,
            "maturity_band": assessment.maturity_band,
            "confidence_index": assessment.confidence_index,
            "completed_at": assessment.completed_at,
            "annual_savings": financial.annual_savings if financial else None,
            "payback_months": financial.payback_months if financial else None,
            "investment": financial.investment if financial else None,
            "pillars": pillars,
            "weakest_pillar": weakest,
            "weakest_pillar_label": PILLAR_LABELS.get(weakest, weakest) if weakest else None,
        })

    scores = [u["readiness_index"] for u in units if u["readiness_index"] is not None]
    average = round(sum(scores) / len(scores), 1) if scores else None
    ranked = [u for u in units if u["readiness_index"] is not None]
    strongest = max(ranked, key=lambda u: u["readiness_index"]) if ranked else None
    weakest_unit = min(ranked, key=lambda u: u["readiness_index"]) if ranked else None
    rollup = {
        "units": len(units),
        "average": average,
        "spread": (round(strongest["readiness_index"] - weakest_unit["readiness_index"], 1)
                   if strongest and weakest_unit else None),
        "strongest": strongest["department"] if strongest else None,
        "strongest_score": strongest["readiness_index"] if strongest else None,
        "weakest": weakest_unit["department"] if weakest_unit else None,
        "weakest_score": weakest_unit["readiness_index"] if weakest_unit else None,
        "total_savings": round(sum(u["annual_savings"] or 0 for u in units), 1),
        "total_investment": round(sum(u["investment"] or 0 for u in units), 1),
        "org_wide": next((u for u in units if u["department"] == "Organisation-wide"), None),
    }
    return {
        "organization": org,
        "rows": units,
        "pillars": pillar_codes,
        "average": average,
        "rollup": rollup,
    }


def _demo_score(position: int, bias: int) -> int:
    base = 2 + ((position * 7 + bias) % 3)
    return max(1, min(5, base))


def run_guided_demo(db: Session) -> models.Assessment:
    """Create a multi-department demo org, pre-fill answers, and complete them."""
    bank = get_bank(db)
    if bank is None:
        raise ValueError("questionnaire not seeded")

    org = models.Organization(
        name="Guided Demo Co",
        industry="Logistics",
        sub_industry="Freight & Distribution",
        employee_count=180,
        revenue_band="SME",
        country="Kenya",
        city="Nairobi",
    )
    db.add(org)
    db.flush()

    questions = get_questions(db, bank.id)
    primary = None
    for dept_name, bias in DEMO_DEPARTMENTS:
        dept = models.Department(organization_id=org.id, name=dept_name)
        db.add(dept)
        db.flush()
        assessment = models.Assessment(
            organization_id=org.id,
            department_id=dept.id,
            questionnaire_id=bank.id,
            respondent=f"Demo {dept_name} Lead",
            status="in_progress",
            started_at=_now(),
        )
        db.add(assessment)
        db.flush()
        for q in questions:
            score = _demo_score(q.position or 1, bias)
            db.add(models.Answer(
                assessment_id=assessment.id,
                question_id=q.id,
                score=score,
                evidence="documented",
            ))
        db.commit()
        _, result = compute(db, assessment.id)
        if result is not None:
            save(db, assessment.id, result)
        if primary is None:
            primary = assessment

    db.refresh(primary)
    return primary
