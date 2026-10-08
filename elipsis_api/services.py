"""Service layer: seeding and the assessment lifecycle (SQLAlchemy + shared engine)."""

import os
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import delete, func, select
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
            title=p.get("title") or "Pain point", detail=p.get("detail"),
            trigger_code=p.get("trigger"), impact_score=p.get("impact")))

    for idx, phase in enumerate(result.get("roadmap") or [], start=1):
        for r in phase.get("items") or []:
            db.add(models.Recommendation(
                assessment_id=assessment_id,
                title=r.get("title") or "Recommendation",
                solution=r.get("solution"),
                technology=r.get("technology"),
                complexity=r.get("complexity"),
                priority_score=r.get("priority"),
                expected_roi=r.get("roi"),
                horizon=phase.get("horizon") or phase.get("label"),
                phase=idx,
            ))

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


def list_assessments(db: Session, org_ids: list[int] | None = None) -> list[dict[str, Any]]:
    if org_ids is not None and not org_ids:
        return []
    query = (
        select(models.Assessment, models.Organization.name, models.Department.name)
        .join(models.Organization, models.Organization.id == models.Assessment.organization_id)
        .join(models.Department, models.Department.id == models.Assessment.department_id, isouter=True)
        .order_by(models.Assessment.id.desc())
    )
    if org_ids is not None:
        query = query.where(models.Assessment.organization_id.in_(org_ids))
    rows = db.execute(query).all()
    ids = [a.id for a, _, _ in rows]
    progress = {}
    if ids:
        progress = dict(db.execute(
            select(models.Answer.assessment_id, func.count())
            .where(models.Answer.assessment_id.in_(ids))
            .group_by(models.Answer.assessment_id)).all())
    savings = {}
    if ids:
        savings = dict(db.execute(
            select(models.FinancialModel.assessment_id, models.FinancialModel.annual_savings)
            .where(models.FinancialModel.assessment_id.in_(ids))).all())
    total_q = len(QUESTIONS)
    out = []
    for a, org_name, dept_name in rows:
        answered = int(progress.get(a.id) or 0)
        out.append(dict(
            id=a.id, status=a.status, respondent=a.respondent,
            organization_id=a.organization_id,
            organization=org_name, department=dept_name,
            answered=answered, total_questions=total_q,
            progress=round(100 * min(answered, total_q) / total_q) if total_q else 0,
            annual_savings=savings.get(a.id),
            readiness_index=a.readiness_index, maturity_band=a.maturity_band,
            confidence_index=a.confidence_index, completed_at=a.completed_at,
            started_at=a.started_at,
        ))
    return out


def authenticate(db: Session, email: str, password: str):
    user = db.scalar(select(models.User).where(models.User.email == email.strip().lower()))
    if user and security.verify_password(password, user.password_hash):
        return user
    return None


def register_user(db: Session, email: str, password: str, name: str | None = None):
    email = (email or "").strip().lower()
    name = (name or "").strip()[:120] or None
    if not email or "@" not in email:
        raise ValueError("Enter a valid work email address.")
    if len(password or "") < 8:
        raise ValueError("Password must be at least 8 characters.")
    existing = db.scalar(select(models.User).where(models.User.email == email))
    if existing is not None:
        raise ValueError("An account with this email already exists. Sign in instead.")
    user = models.User(
        email=email, name=name, role="client",
        password_hash=security.hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_session(db: Session, user_id: int) -> str:
    token = security.new_token()
    db.add(models.Session(user_id=user_id, token=token))
    db.commit()
    return token


def user_for_token(db: Session, token: str | None):
    if not token:
        return None
    sess = db.scalar(select(models.Session).where(models.Session.token == token))
    if sess is None:
        return None
    return db.get(models.User, sess.user_id)


def delete_session(db: Session, token: str | None):
    if not token:
        return
    sess = db.scalar(select(models.Session).where(models.Session.token == token))
    if sess:
        db.delete(sess)
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
            pillar=SUBDOMAIN_PILLAR.get(code, ""),
            questions=items,
            answered=done,
            total=len(items),
            complete=done >= len(items) and len(items) > 0,
        ))
    return steps


def live_scores(db: Session, assessment_id: int, segment_code: str = ""):
    assessment = db.get(models.Assessment, assessment_id)
    if assessment is None:
        return None
    questions = question_dicts(db, assessment_id)
    answers = answers_map(db, assessment_id)
    return _compute_live(questions, answers, segment_code or "")


def save_answers(db: Session, assessment_id: int, items):
    assessment = db.get(models.Assessment, assessment_id)
    if assessment is None:
        return
    for item in items:
        existing = db.scalar(select(models.Answer).where(
            models.Answer.assessment_id == assessment_id,
            models.Answer.question_id == item["question_id"]))
        if existing is None:
            db.add(models.Answer(
                assessment_id=assessment_id,
                question_id=item["question_id"],
                score=item["score"],
                evidence=item.get("evidence") or "none",
            ))
        else:
            existing.score = item["score"]
            existing.evidence = item.get("evidence") or existing.evidence or "none"
    db.commit()


def dashboard_data(db: Session, limit: int = 8,
                   org_ids: list[int] | None = None) -> dict[str, Any]:
    rows = list_assessments(db, org_ids)
    completed = [r for r in rows if r.get("status") == "completed"
                 and r.get("readiness_index") is not None]

    pillar_totals = {}
    completed_ids = [r["id"] for r in completed]
    if completed_ids:
        for p in db.scalars(select(models.PillarScore).where(
                models.PillarScore.assessment_id.in_(completed_ids))):
            if p.score is None:
                continue
            bucket = pillar_totals.setdefault(p.pillar, [0.0, 0])
            bucket[0] += p.score
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
        savings=round(sum(r.get("annual_savings") or 0 for r in completed), 2),
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
    query = select(models.Assessment.id)
    if org_ids is not None:
        if not org_ids:
            return 0
        query = query.where(models.Assessment.organization_id.in_(org_ids))
    assessment_ids = list(db.scalars(query))
    removed = 0
    if assessment_ids:
        for model in (models.Answer, models.MetricScore, models.PillarScore,
                      models.SubdomainScore, models.PainPoint,
                      models.Recommendation, models.FinancialModel, models.Report,
                      models.ShareLink):
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


def list_organizations(db: Session, org_ids: list[int] | None = None) -> list[models.Organization]:
    query = select(models.Organization).order_by(models.Organization.name)
    if org_ids is not None:
        if not org_ids:
            return []
        query = query.where(models.Organization.id.in_(org_ids))
    return list(db.scalars(query))


# --- Company scoping -------------------------------------------------------

def is_admin(user) -> bool:
    if user is None:
        return False
    if (getattr(user, "role", "") or "") == "admin":
        return True
    admin_email = (os.getenv("ELIPSIS_ADMIN_EMAIL") or DEFAULT_ADMIN_EMAIL).lower()
    return (getattr(user, "email", "") or "").lower() == admin_email


def owned_org_ids(db: Session, user) -> list[int]:
    if user is None:
        return []
    return list(db.scalars(select(models.OrgOwner.organization_id).where(
        models.OrgOwner.user_id == user.id)))


def owned_orgs(db: Session, user) -> list[models.Organization]:
    return list_organizations(db, owned_org_ids(db, user))


def claim_org(db: Session, user_id: int, organization_id: int) -> None:
    exists = db.scalar(select(models.OrgOwner).where(
        models.OrgOwner.user_id == user_id,
        models.OrgOwner.organization_id == organization_id))
    if exists is None:
        db.add(models.OrgOwner(user_id=user_id, organization_id=organization_id))
        db.commit()


def visible_org_ids(db: Session, user) -> list[int] | None:
    """Organisations a user should see. ``None`` means everything (admin portfolio).

    A user who owns companies always sees only those, so every surface is
    tailored to their company; admins without companies see the portfolio.
    """
    owned = owned_org_ids(db, user)
    if owned:
        return owned
    return None if is_admin(user) else []


def can_access_org(db: Session, user, organization_id: int | None) -> bool:
    if user is None or organization_id is None:
        return False
    if is_admin(user):
        return True
    return organization_id in owned_org_ids(db, user)


def company_overview(db: Session, org: models.Organization) -> dict[str, Any]:
    """Everything the dashboard and company page show about one company."""
    rows = list_assessments(db, [org.id])
    completed = sorted([r for r in rows if r["status"] == "completed"
                        and r.get("readiness_index") is not None],
                       key=lambda r: (r.get("completed_at") or "", r["id"]))
    latest_by_dept: dict[str, dict[str, Any]] = {}
    for r in completed:
        latest_by_dept[r.get("department") or "Organisation-wide"] = r
    latest_ids = [r["id"] for r in latest_by_dept.values()]

    pillars: dict[str, list[float]] = {}
    pains: list[dict[str, Any]] = []
    quick_wins: list[dict[str, Any]] = []
    if latest_ids:
        for p in db.scalars(select(models.PillarScore).where(
                models.PillarScore.assessment_id.in_(latest_ids))):
            if p.score is not None:
                pillars.setdefault(p.pillar, []).append(p.score)
        dept_of = {r["id"]: r.get("department") for r in latest_by_dept.values()}
        for p in db.scalars(select(models.PainPoint).where(
                models.PainPoint.assessment_id.in_(latest_ids))
                .order_by(models.PainPoint.impact_score.desc()).limit(6)):
            pains.append(dict(title=p.title, severity=p.severity, impact=p.impact_score,
                              detail=p.detail, assessment_id=p.assessment_id,
                              department=dept_of.get(p.assessment_id)))
        for r in db.scalars(select(models.Recommendation).where(
                models.Recommendation.assessment_id.in_(latest_ids),
                models.Recommendation.phase == 1)
                .order_by(models.Recommendation.priority_score.desc()).limit(5)):
            quick_wins.append(dict(title=r.title, technology=r.technology,
                                   roi=r.expected_roi, priority=r.priority_score,
                                   assessment_id=r.assessment_id))

    scores = [r["readiness_index"] for r in latest_by_dept.values()]
    leaderboard = sorted(latest_by_dept.values(),
                         key=lambda r: r.get("readiness_index") or 0, reverse=True)
    return dict(
        organization=org,
        rows=rows,
        completed=completed,
        in_progress=[r for r in rows if r["status"] != "completed"],
        latest=completed[-1] if completed else None,
        trend=[dict(label=(r.get("completed_at") or "")[:10], value=r["readiness_index"],
                    department=r.get("department"), id=r["id"]) for r in completed],
        leaderboard=leaderboard,
        pillars={code: round(sum(v) / len(v), 1) for code, v in pillars.items() if v},
        average=round(sum(scores) / len(scores), 1) if scores else None,
        savings=round(sum(r.get("annual_savings") or 0 for r in leaderboard), 2),
        pains=pains,
        quick_wins=quick_wins,
        departments=len(latest_by_dept),
    )


def department_comparison(db: Session, organization_id: int) -> dict[str, Any]:
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
        fin = db.scalar(select(models.FinancialModel).where(
            models.FinancialModel.assessment_id == assessment.id))
        units.append({
            "id": assessment.id,
            "assessment_id": assessment.id,
            "annual_savings": fin.annual_savings if fin else None,
            "payback_months": fin.payback_months if fin else None,
            "department": dept_name or "Organisation-wide",
            "respondent": assessment.respondent,
            "readiness_index": assessment.readiness_index,
            "maturity_band": assessment.maturity_band,
            "confidence_index": assessment.confidence_index,
            "completed_at": assessment.completed_at,
            "pillars": pillars,
        })

    scores = [u["readiness_index"] for u in units if u["readiness_index"] is not None]
    average = round(sum(scores) / len(scores), 1) if scores else None
    return {
        "organization": org,
        "rows": units,
        "pillars": pillar_codes,
        "average": average,
    }


def _demo_score(position: int, bias: int) -> int:
    base = 2 + ((position * 7 + bias) % 3)
    return max(1, min(5, base))


def run_guided_demo(db: Session) -> models.Assessment:
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
