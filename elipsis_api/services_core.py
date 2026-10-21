"""Service layer: seeding and the assessment lifecycle (SQLAlchemy + shared engine)."""

import json
import os
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from constants import SUBDOMAIN_PILLAR
from elipsis_api import models, security
from elipsis_questions import QUESTIONNAIRE, QUESTIONS
from readiness import compute as _compute


def _now():
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


DEFAULT_ADMIN_EMAIL = "admin@elipsis.local"
DEFAULT_ADMIN_PASSWORD = "elipsis"

DEMO_DEPARTMENTS = [
    ("Operations", 3),
    ("Finance", 2),
    ("Customer Service", 4),
]


def _seed_admin(db: Session):
    email = os.getenv("ELIPSIS_ADMIN_EMAIL") or DEFAULT_ADMIN_EMAIL
    password = os.getenv("ELIPSIS_ADMIN_PASSWORD") or DEFAULT_ADMIN_PASSWORD
    if password == DEFAULT_ADMIN_PASSWORD:
        from elipsis_api.config import is_production
        if is_production():
            print("[elipsis] ERROR: ELIPSIS_ADMIN_PASSWORD is not set; skipping "
                  "administrator seed. Sign-up remains available.", flush=True)
            return
        print("[elipsis] WARNING: no ELIPSIS_ADMIN_PASSWORD set, so the first "
              "administrator uses the default password. Set ELIPSIS_ADMIN_EMAIL "
              "and ELIPSIS_ADMIN_PASSWORD before exposing this instance.",
              flush=True)
    db.add(models.User(email=email, name="Elipsis Admin", role="admin",
                       user_type="admin", is_admin=True, email_verified=True,
                       password_hash=security.hash_password(password)))


def seed(db: Session):
    bank = db.scalar(select(models.Questionnaire).where(
        models.Questionnaire.code == QUESTIONNAIRE["code"]))
    if bank is None:
        bank = models.Questionnaire(
            code=QUESTIONNAIRE["code"], name=QUESTIONNAIRE["name"],
            version=QUESTIONNAIRE["version"], department=QUESTIONNAIRE["department"],
            estimated_minutes=QUESTIONNAIRE["estimated_minutes"], active=1)
        db.add(bank)
        db.flush()

    existing = list(db.scalars(select(models.Question).where(
        models.Question.questionnaire_id == bank.id)))
    if len(existing) != len(QUESTIONS):
        if existing:
            db.execute(delete(models.Question).where(
                models.Question.questionnaire_id == bank.id))
            db.flush()
        for pos, item in enumerate(QUESTIONS, start=1):
            db.add(models.Question(
                questionnaire_id=bank.id, code=item["code"], scale=item.get("scale"),
                subdomain=item["subdomain"], pillar=SUBDOMAIN_PILLAR[item["subdomain"]],
                text=item["text"], why=item.get("why"), weight=item.get("weight") or 1.0,
                evidence_required=1 if item.get("evidence_required") else 0, position=pos))
    bank.name = QUESTIONNAIRE["name"]
    bank.version = QUESTIONNAIRE["version"]
    bank.department = QUESTIONNAIRE["department"]
    bank.estimated_minutes = QUESTIONNAIRE["estimated_minutes"]

    if db.scalar(select(models.Organization)) is None:
        org = models.Organization(name="Demo Logistics Ltd", industry="Logistics",
                                  sub_industry="Freight & Distribution", employee_count=120,
                                  revenue_band="SME", country="Kenya", city="Nairobi")
        db.add(org)
        db.flush()
        db.add(models.Department(organization_id=org.id, name="Operations",
                                 head="Operations Manager", staff_count=6))

    if db.scalar(select(models.User)) is None:
        _seed_admin(db)

    db.commit()
    return bank


def get_bank(db: Session) -> models.Questionnaire | None:
    return db.scalar(select(models.Questionnaire).where(
        models.Questionnaire.code == QUESTIONNAIRE["code"]))


def get_questions(db: Session, questionnaire_id: int) -> list[models.Question]:
    return list(db.scalars(select(models.Question).where(
        models.Question.questionnaire_id == questionnaire_id
    ).order_by(models.Question.position)))


def create_assessment(db: Session, payload) -> models.Assessment:
    org = db.get(models.Organization, payload.organization_id) if getattr(payload, "organization_id", None) else None
    if org is None and getattr(payload, "organization", None) is not None:
        o = payload.organization
        org = models.Organization(
            name=o.name, industry=getattr(o, "industry", None),
            employee_count=getattr(o, "employee_count", None),
            country=getattr(o, "country", None), city=getattr(o, "city", None))
        db.add(org)
        db.flush()
    if org is None:
        raise ValueError("organization required")

    dept = None
    dept_name = getattr(payload, "department", None) or "Operations"
    dept = db.scalar(select(models.Department).where(
        models.Department.organization_id == org.id,
        models.Department.name == dept_name))
    if dept is None:
        dept = models.Department(organization_id=org.id, name=dept_name)
        db.add(dept)
        db.flush()

    bank = get_bank(db)
    if bank is None:
        raise ValueError("questionnaire not seeded")

    assessment = models.Assessment(
        organization_id=org.id,
        department_id=dept.id,
        questionnaire_id=bank.id,
        respondent=getattr(payload, "respondent", None),
        status="in_progress",
        started_at=_now(),
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


def answers_map(db: Session, assessment_id: int):
    rows = db.scalars(select(models.Answer).where(
        models.Answer.assessment_id == assessment_id)).all()
    return {a.question_id: {"score": a.score, "evidence": a.evidence} for a in rows}


def _compute_for(db: Session, assessment_id: int,
                 overrides: dict[str, Any] | None = None
                 ) -> tuple[models.Assessment | None, dict[str, Any] | None]:
    assessment = db.get(models.Assessment, assessment_id)
    if assessment is None:
        return None, None
    questions = get_questions(db, assessment.questionnaire_id)
    q_dicts = [dict(id=q.id, code=q.code, subdomain=q.subdomain, pillar=q.pillar,
                    weight=q.weight, evidence_required=bool(q.evidence_required))
               for q in questions]
    answers = answers_map(db, assessment_id)
    org = db.get(models.Organization, assessment.organization_id)
    staff = (org.employee_count if org and org.employee_count else 50)
    assumptions = db.get(models.AssessmentAssumption, assessment_id)
    # A verified attachment is stronger evidence than a self-declared label.
    attached = {row.question_id for row in db.scalars(
        select(models.EvidenceAttachment).where(
            models.EvidenceAttachment.assessment_id == assessment_id))}
    for qid in attached:
        if qid in answers:
            answers[qid]["evidence"] = "verified"
    kwargs = {}
    if assumptions is not None:
        kwargs = dict(
            hourly_rate=assumptions.hourly_rate,
            working_hours_per_month=assumptions.working_hours_per_month,
            max_savings_share=assumptions.max_savings_share,
            annual_revenue=assumptions.annual_revenue,
        )
        if assumptions.staff:
            staff = assumptions.staff
    if overrides:
        staff = overrides.get("staff") or staff
        for key in ("hourly_rate", "working_hours_per_month",
                    "max_savings_share", "annual_revenue"):
            if overrides.get(key) is not None:
                kwargs[key] = overrides[key]
    result = _compute(q_dicts, answers, staff=staff, **kwargs)
    return assessment, result


def compute(db: Session, assessment_id: int) -> tuple[models.Assessment | None, dict[str, Any] | None]:
    return _compute_for(db, assessment_id)


def compute_scenario(db: Session, assessment_id: int, overrides: dict[str, Any]
                     ) -> tuple[models.Assessment | None, dict[str, Any] | None]:
    """Compute a what-if result without persisting assumptions or scores."""
    return _compute_for(db, assessment_id, overrides)


def save(db: Session, assessment_id: int, result):
    assessment = db.get(models.Assessment, assessment_id)
    if assessment is None or result is None:
        return
    assessment.status = "completed"
    assessment.completed_at = _now()
    assessment.readiness_index = result.get("readiness_index")
    assessment.maturity_band = result.get("maturity_band")
    assessment.confidence_index = result.get("confidence_index")

    for model in (models.PillarScore, models.SubdomainScore, models.MetricScore,
                  models.PainPoint, models.Recommendation, models.FinancialModel):
        db.execute(delete(model).where(model.assessment_id == assessment_id))

    for code, score in (result.get("pillars") or {}).items():
        db.add(models.PillarScore(assessment_id=assessment_id, pillar=code, score=score))
    for code, score in (result.get("subdomains") or {}).items():
        db.add(models.SubdomainScore(assessment_id=assessment_id, subdomain=code, score=score))

    for pcode, rows in (result.get("metrics_by_pillar") or {}).items():
        for m in rows:
            db.add(models.MetricScore(
                assessment_id=assessment_id, pillar=pcode,
                metric=m.get("code") or m.get("label", ""),
                score=m.get("value"), kind=m.get("kind")))

    for p in (result.get("pain_points") or []):
        db.add(models.PainPoint(
            assessment_id=assessment_id,
            trigger_code=p.get("trigger") or p.get("trigger_code"),
            severity=p.get("severity"),
            title=p.get("title"), detail=p.get("detail"),
            impact_score=p.get("impact")))

    for phase in (result.get("roadmap") or []):
        for r in phase.get("items") or []:
            db.add(models.Recommendation(
                assessment_id=assessment_id, phase=r.get("phase") or phase.get("number"),
                title=r.get("title"), solution=r.get("solution"),
                technology=r.get("technology"), complexity=r.get("complexity"),
                expected_roi=r.get("roi"), priority_score=r.get("priority"),
                horizon=r.get("horizon")))

    fin = result.get("financial") or {}
    db.add(models.FinancialModel(
        assessment_id=assessment_id,
        current_cost=fin.get("current_cost"),
        future_cost=fin.get("future_cost"),
        annual_savings=fin.get("annual_savings"),
        investment=fin.get("investment"),
        roi=fin.get("roi"),
        payback_months=fin.get("payback_months"),
        assumptions_json=json.dumps(fin.get("assumptions") or {}, sort_keys=True),
    ))
    db.commit()


def submit(db: Session, assessment_id: int, answers):
    items = []
    for a in answers:
        items.append(dict(
            question_id=a.question_id if hasattr(a, "question_id") else a["question_id"],
            score=a.score if hasattr(a, "score") else a["score"],
            evidence=(a.evidence if hasattr(a, "evidence") else a.get("evidence")) or "none",
        ))
    for item in items:
        existing = db.scalar(select(models.Answer).where(
            models.Answer.assessment_id == assessment_id,
            models.Answer.question_id == item["question_id"]))
        if existing is None:
            db.add(models.Answer(
                assessment_id=assessment_id, question_id=item["question_id"],
                score=item["score"], evidence=item["evidence"]))
        else:
            existing.score = item["score"]
            existing.evidence = item["evidence"]
    db.commit()
    assessment, result = compute(db, assessment_id)
    if result is not None:
        save(db, assessment_id, result)
        ensure_plan_items(db, assessment_id, result)
    return assessment, result


def list_assessments(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(
        select(models.Assessment, models.Organization.name, models.Department.name)
        .join(models.Organization, models.Organization.id == models.Assessment.organization_id)
        .join(models.Department, models.Department.id == models.Assessment.department_id, isouter=True)
        .order_by(models.Assessment.id.desc())
    ).all()
    out = []
    for a, org_name, dept_name in rows:
        out.append(dict(
            id=a.id, status=a.status, respondent=a.respondent,
            organization=org_name, department=dept_name,
            readiness_index=a.readiness_index, maturity_band=a.maturity_band,
            confidence_index=a.confidence_index, completed_at=a.completed_at,
            started_at=a.started_at,
        ))
    return out


def get_assumptions(db: Session, assessment_id: int):
    return db.get(models.AssessmentAssumption, assessment_id)


def save_assumptions(db: Session, assessment_id: int, *, staff, hourly_rate,
                     working_hours_per_month, max_savings_share,
                     annual_revenue, note, user_id):
    """Upsert client-editable assumptions with hard safety clamps."""
    def _num(value, default=None):
        try:
            return float(value) if value not in (None, "") else default
        except (TypeError, ValueError):
            return default

    row = db.get(models.AssessmentAssumption, assessment_id)
    if row is None:
        row = models.AssessmentAssumption(assessment_id=assessment_id)
        db.add(row)
    row.staff = max(1, min(100_000, int(_num(staff, 50) or 50)))
    row.hourly_rate = max(50.0, min(20_000.0, _num(hourly_rate, 500.0) or 500.0))
    row.working_hours_per_month = max(
        20.0, min(400.0, _num(working_hours_per_month, 173.33) or 173.33))
    row.max_savings_share = max(
        0.01, min(0.30, _num(max_savings_share, 0.12) or 0.12))
    revenue = _num(annual_revenue, None)
    row.annual_revenue = max(0.0, revenue) if revenue is not None else None
    row.note = (note or "").strip()[:2000] or None
    row.updated_by = user_id
    row.updated_at = _now()
    db.commit()
    return row


def previous_assessment(db: Session, assessment: models.Assessment):
    if assessment is None:
        return None
    query = select(models.Assessment).where(
        models.Assessment.organization_id == assessment.organization_id,
        models.Assessment.status == "completed",
        models.Assessment.id != assessment.id,
        models.Assessment.readiness_index.is_not(None),
    )
    if assessment.department_id:
        query = query.where(models.Assessment.department_id == assessment.department_id)
    else:
        query = query.where(models.Assessment.department_id.is_(None))
    return db.scalar(query.order_by(models.Assessment.id.desc()))


def ensure_plan_items(db: Session, assessment_id: int, result: dict) -> list:
    """Create a 90-day action plan once, preserving later edits."""
    existing = list(db.scalars(select(models.RoadmapItem).where(
        models.RoadmapItem.assessment_id == assessment_id
    ).order_by(models.RoadmapItem.id)))
    if existing:
        return existing
    from datetime import date, timedelta
    today = date.today()
    recommendations = []
    for phase in result.get("roadmap") or []:
        for item in phase.get("items") or []:
            recommendations.append((phase.get("number") or item.get("phase") or 1, item))
    recommendations.sort(key=lambda pair: -float(pair[1].get("priority") or 0))
    for index, (phase, item) in enumerate(recommendations[:9]):
        days = 30 if index < 3 else 60 if index < 6 else 90
        db.add(models.RoadmapItem(
            assessment_id=assessment_id,
            phase=phase,
            title=item.get("title") or "Improvement action",
            solution=item.get("solution"),
            technology=item.get("technology"),
            complexity=item.get("complexity"),
            priority=item.get("priority"),
            horizon=item.get("horizon"),
            owner=None,
            due_date=(today + timedelta(days=days)).isoformat(),
            status="not_started",
            notes=None,
            created_at=_now(),
            updated_at=_now(),
        ))
    db.commit()
    return list(db.scalars(select(models.RoadmapItem).where(
        models.RoadmapItem.assessment_id == assessment_id
    ).order_by(models.RoadmapItem.due_date, models.RoadmapItem.id)))


def update_plan_item(db: Session, assessment_id: int, item_id: int, *,
                     owner, due_date, status, notes, owner_phone=None):
    item = db.get(models.RoadmapItem, item_id)
    if item is None or item.assessment_id != assessment_id:
        return None
    allowed = {"not_started", "in_progress", "blocked", "done"}
    item.owner = (owner or "").strip()[:120] or None
    if owner_phone is not None:
        item.owner_phone = (owner_phone or "").strip()[:40] or None
    item.due_date = (due_date or "").strip()[:10] or None
    item.status = status if status in allowed else "not_started"
    item.notes = (notes or "").strip()[:2000] or None
    item.updated_at = _now()
    db.commit()
    return item
