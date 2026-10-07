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
                questionnaire_id=bank.id, code=item["code"], scale=item["scale"],
                subdomain=item["subdomain"], pillar=SUBDOMAIN_PILLAR[item["subdomain"]],
                text=item["text"], why=item["why"], weight=item["weight"],
                evidence_required=1 if item["evidence_required"] else 0, position=pos))
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
    return bank.id


def get_bank(db: Session) -> models.Questionnaire | None:
    return db.scalar(select(models.Questionnaire).where(
        models.Questionnaire.code == QUESTIONNAIRE["code"]))


def get_questions(db: Session, questionnaire_id: int) -> list[models.Question]:
    return list(db.scalars(select(models.Question).where(
        models.Question.questionnaire_id == questionnaire_id
    ).order_by(models.Question.position)))


def create_assessment(db: Session, payload) -> models.Assessment:
    org = db.get(models.Organization, payload.organization_id) if payload.organization_id else None
    if org is None and payload.organization is not None:
        org = models.Organization(**payload.organization.model_dump())
        db.add(org)
        db.flush()
    if org is None:
        raise ValueError("an existing organization_id or a new organization is required")

    dept = db.scalar(select(models.Department).where(
        models.Department.organization_id == org.id,
        models.Department.name == payload.department))
    if dept is None:
        dept = models.Department(organization_id=org.id, name=payload.department)
        db.add(dept)
        db.flush()

    bank = get_bank(db)
    if bank is None:
        raise ValueError("questionnaire not seeded")
    assessment = models.Assessment(organization_id=org.id, department_id=dept.id,
                                   questionnaire_id=bank.id, respondent=payload.respondent,
                                   status="in_progress", started_at=_now())
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


def answers_map(db: Session, assessment_id: int):
    rows = db.scalars(select(models.Answer).where(
        models.Answer.assessment_id == assessment_id))
    return {r.question_id: {"score": r.score, "evidence": r.evidence or "none"} for r in rows}


def compute(db: Session, assessment_id: int) -> tuple[models.Assessment | None, dict[str, Any] | None]:
    assessment = db.get(models.Assessment, assessment_id)
    if assessment is None:
        return None, None
    questions = get_questions(db, assessment.questionnaire_id)
    q_dicts = [dict(id=q.id, code=q.code, subdomain=q.subdomain, pillar=q.pillar,
                    weight=q.weight, evidence_required=bool(q.evidence_required))
               for q in questions]
    org = db.get(models.Organization, assessment.organization_id)
    staff = getattr(org, "employee_count", None) if org else None
    return assessment, _compute(q_dicts, answers_map(db, assessment_id), staff=staff)


def save(db: Session, assessment_id: int, result):
    for model in (models.PillarScore, models.SubdomainScore, models.MetricScore,
                  models.PainPoint, models.Recommendation, models.FinancialModel):
        for row in db.scalars(select(model).where(model.assessment_id == assessment_id)):
            db.delete(row)
    db.flush()

    for code, score in result["pillars"].items():
        db.add(models.PillarScore(assessment_id=assessment_id, pillar=code, score=score,
                                  weight=PILLAR_WEIGHTS.get(code, 0.0)))
    for code, score in result["subdomains"].items():
        db.add(models.SubdomainScore(assessment_id=assessment_id, subdomain=code, score=score))

    for row in result["metric_rows"]:
        db.add(models.MetricScore(
            assessment_id=assessment_id, metric=row["code"], pillar=row["pillar"],
            label=row["label"], kind=row["kind"], score=row["value"],
            reading=row["reading"]))

    rec_by_trigger = {r["trigger"]: r for r in result["recommendations"]}
    for pp in result["pain_points"]:
        pain = models.PainPoint(assessment_id=assessment_id, trigger_code=pp["trigger"],
                                title=pp["title"], severity=pp["severity"],
                                impact_score=pp["impact"], detail=pp["detail"])
        db.add(pain)
        db.flush()
        rec = rec_by_trigger.get(pp["trigger"])
        if rec:
            db.add(models.Recommendation(
                assessment_id=assessment_id, pain_point_id=pain.id, title=rec["title"],
                solution=rec["solution"], technology=rec["technology"],
                complexity=rec["complexity"], priority_score=rec["priority"],
                phase=rec.get("phase"), horizon=rec["horizon"], expected_roi=rec["roi"]))

    fin = result["financial"]
    db.add(models.FinancialModel(
        assessment_id=assessment_id, current_cost=fin["current_cost"],
        future_cost=fin["future_cost"], annual_savings=fin["annual_savings"],
        investment=fin["investment"], roi=fin["roi"], payback_months=fin["payback_months"]))

    assessment = db.get(models.Assessment, assessment_id)
    if assessment is not None:
        assessment.status = "completed"
        assessment.completed_at = _now()
        assessment.readiness_index = result["readiness_index"]
        assessment.department_score = result["organisation_score"]
        assessment.confidence_index = result["confidence_index"]
        assessment.maturity_band = result["maturity_band"]
    db.add(models.Report(assessment_id=assessment_id,
                         report_type="Elipsis Transformation Assessment"))
    db.commit()
    return result


def submit(db: Session, assessment_id: int, answers):
    for item in answers:
        existing = db.scalar(select(models.Answer).where(
            models.Answer.assessment_id == assessment_id,
            models.Answer.question_id == item.question_id))
        if existing is None:
            db.add(models.Answer(assessment_id=assessment_id, question_id=item.question_id,
                                 score=item.score, evidence=item.evidence))
        else:
            existing.score = item.score
            existing.evidence = item.evidence
    db.commit()
    assessment, result = compute(db, assessment_id)
    if result is None:
        return None, None
    return assessment, save(db, assessment_id, result)


def list_assessments(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(
        select(models.Assessment, models.Organization.name, models.Department.name)
        .join(models.Organization, models.Organization.id == models.Assessment.organization_id)
        .join(models.Department, models.Department.id == models.Assessment.department_id,
              isouter=True)
        .order_by(models.Assessment.id.desc())).all()
    return [dict(id=a.id, status=a.status, readiness_index=a.readiness_index,
                 maturity_band=a.maturity_band, organization=org_name, department=dept_name,
                 organization_id=a.organization_id, department_id=a.department_id)
            for a, org_name, dept_name in rows]


def authenticate(db: Session, email: str, password: str):
    user = db.scalar(select(models.User).where(models.User.email == email))
    if user and security.verify_password(password, user.password_hash):
        return user
    return None


def create_session(db: Session, user_id: int) -> str:
    token = security.new_token()
    db.add(models.AuthSession(token=token, user_id=user_id))
    db.commit()
    return token


def user_for_token(db: Session, token: str | None):
    if not token:
        return None
    session = db.get(models.AuthSession, token)
    if session is None:
        return None
    return db.get(models.User, session.user_id)


def delete_session(db: Session, token: str | None):
    session = db.get(models.AuthSession, token) if token else None
    if session is not None:
        db.delete(session)
        db.commit()


def question_dicts(db: Session, assessment_id: int) -> list[dict[str, Any]]:
    assessment = db.get(models.Assessment, assessment_id)
    if assessment is None:
        return []
    questions = get_questions(db, assessment.questionnaire_id)
    return [dict(id=q.id, code=q.code, subdomain=q.subdomain, pillar=q.pillar,
                 weight=q.weight, evidence_required=bool(q.evidence_required))
            for q in questions]


def build_segments(db: Session, assessment_id: int) -> list[dict[str, Any]]:
    assessment = db.get(models.Assessment, assessment_id)
    if assessment is None:
        return []
    questions = get_questions(db, assessment.questionnaire_id)
    answers = answers_map(db, assessment_id)

    order, buckets = [], {}
    for q in questions:
        code = q.subdomain
        if code not in buckets:
            buckets[code] = []
            order.append(code)
        buckets[code].append(q)

    steps = []
    for index, code in enumerate(order, start=1):
        items = buckets[code]
        done = sum(1 for q in items
                   if answers.get(q.id) and answers[q.id].get("score") is not None)
        steps.append(dict(
            number=index,
            subdomain=code,
            pillar=items[0].pillar,
            questions=items,
            answered=done,
            total=len(items),
            complete=done == len(items),
            percent=round(100 * done / len(items)) if items else 0,
        ))
    return steps


def live_scores(db: Session, assessment_id: int, segment_code: str = ""):
    questions = question_dicts(db, assessment_id)
    if not questions:
        return None
    return _compute_live(questions, answers_map(db, assessment_id), segment_code)


def save_answers(db: Session, assessment_id: int, items):
    assessment = db.get(models.Assessment, assessment_id)
    if assessment is None:
        return 0
    written = 0
    for item in items:
        existing = db.scalar(select(models.Answer).where(
            models.Answer.assessment_id == assessment_id,
            models.Answer.question_id == item["question_id"]))
        if existing is None:
            db.add(models.Answer(assessment_id=assessment_id,
                                 question_id=item["question_id"],
                                 score=item["score"], evidence=item["evidence"]))
        else:
            existing.score = item["score"]
            existing.evidence = item["evidence"]
        written += 1
    db.commit()
    return written


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


def reset_demo_data(db: Session):
    assessment_ids = list(db.scalars(select(models.Assessment.id)))
    removed = 0
    if assessment_ids:
        for model in (models.Answer, models.MetricScore, models.PillarScore,
                      models.SubdomainScore, models.PainPoint,
                      models.Recommendation, models.FinancialModel, models.Report,
                      models.ShareLink):
            db.execute(delete(model).where(
                model.assessment_id.in_(assessment_ids)
                if hasattr(model, "assessment_id") else model.token != ""))
        # ShareLink uses assessment_id; delete explicitly
        db.execute(delete(models.ShareLink).where(
            models.ShareLink.assessment_id.in_(assessment_ids)))
        db.execute(delete(models.Assessment).where(models.Assessment.id.in_(assessment_ids)))
        removed = len(assessment_ids)
    db.commit()
    return removed


# --- Share links --------------------------------------------------------------

def create_share_link(db: Session, assessment_id: int, user_id: int | None = None,
                      label: str | None = None) -> models.ShareLink:
    assessment = db.get(models.Assessment, assessment_id)
    if assessment is None:
        raise ValueError("assessment not found")
    if assessment.status != "completed":
        raise ValueError("only completed assessments can be shared")
    token = security.new_token()
    link = models.ShareLink(
        token=token,
        assessment_id=assessment_id,
        created_by=user_id,
        label=label or "Board pack",
        created_at=_now(),
    )
    db.add(link)
    db.commit()
    return link


def resolve_share_token(db: Session, token: str):
    link = db.get(models.ShareLink, token)
    if link is None:
        return None, None, None
    assessment, result = compute(db, link.assessment_id)
    return link, assessment, result


# --- Department comparison ----------------------------------------------------

def list_organizations(db: Session) -> list[models.Organization]:
    return list(db.scalars(select(models.Organization).order_by(models.Organization.name)))


def department_comparison(db: Session, organization_id: int) -> dict[str, Any]:
    """Side-by-side view of completed assessments by department for one org."""
    org = db.get(models.Organization, organization_id)
    if org is None:
        return {"organization": None, "rows": [], "pillars": []}

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
        fin = db.scalar(select(models.FinancialModel).where(
            models.FinancialModel.assessment_id == assessment.id))
        units.append(dict(
            id=assessment.id,
            department=dept_name or "Organisation-wide",
            readiness_index=assessment.readiness_index,
            maturity_band=assessment.maturity_band,
            confidence_index=assessment.confidence_index,
            pillars=pillars,
            annual_savings=fin.annual_savings if fin else None,
            payback_months=fin.payback_months if fin else None,
        ))

    return dict(
        organization=org,
        rows=units,
        pillars=pillar_codes,
        average=round(
            sum(u["readiness_index"] for u in units if u["readiness_index"] is not None) / len(units),
            1,
        ) if units else None,
    )


# --- Guided demo mode ---------------------------------------------------------

def _demo_score(position: int, bias: int) -> int:
    """Deterministic 1–5 score with a departmental bias."""
    base = 1 + ((position * 5 + bias * 3) % 5)
    return max(1, min(5, base))


def run_guided_demo(db: Session) -> models.Assessment:
    """Create a multi-department demo org, pre-fill answers, and complete them.

    Returns the primary (Operations) assessment so the UI can open results.
    """
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
        dept = models.Department(
            organization_id=org.id, name=dept_name,
            head=f"{dept_name} Lead", staff_count=20 + bias * 5)
        db.add(dept)
        db.flush()
        assessment = models.Assessment(
            organization_id=org.id,
            department_id=dept.id,
            questionnaire_id=bank.id,
            respondent=f"Demo · {dept_name}",
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
