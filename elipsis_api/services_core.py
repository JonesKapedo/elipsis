"""Service layer: seeding and the assessment lifecycle (SQLAlchemy + shared engine)."""

import os
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from constants import PILLAR_WEIGHTS, SUBDOMAIN_PILLAR
from elipsis_questions import QUESTIONS, QUESTIONNAIRE
from readiness import compute as _compute
from readiness import compute_live as _compute_live
from elipsis_api import models, security


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


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
        print("[elipsis] WARNING: no ELIPSIS_ADMIN_PASSWORD set, so the first "
              "administrator uses the default password. Set ELIPSIS_ADMIN_EMAIL "
              "and ELIPSIS_ADMIN_PASSWORD before exposing this instance.",
              flush=True)
    db.add(models.User(email=email, name="Elipsis Admin", role="admin",
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


def compute(db: Session, assessment_id: int) -> tuple[models.Assessment | None, dict[str, Any] | None]:
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
    result = _compute(q_dicts, answers, staff=staff)
    return assessment, result


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
            assessment_id=assessment_id, severity=p.get("severity"),
            title=p.get("title"), detail=p.get("detail"),
            impact=p.get("impact")))

    for phase in (result.get("roadmap") or []):
        for r in phase.get("items") or []:
            db.add(models.Recommendation(
                assessment_id=assessment_id, phase=phase.get("label"),
                title=r.get("title"), solution=r.get("solution"),
                technology=r.get("technology"), complexity=r.get("complexity"),
                roi=r.get("roi"), priority=r.get("priority")))

    fin = result.get("financial") or {}
    db.add(models.FinancialModel(
        assessment_id=assessment_id,
        current_cost=fin.get("current_cost"),
        future_cost=fin.get("future_cost"),
        annual_savings=fin.get("annual_savings"),
        investment=fin.get("investment"),
        roi=fin.get("roi"),
        payback_months=fin.get("payback_months"),
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
