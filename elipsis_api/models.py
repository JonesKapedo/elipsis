"""SQLAlchemy ORM models for Elipsis.

The persisted column names are deliberately neutral (`readiness_index`,
`pillar`, `subdomain`) so that the Turbinez -> Elipsis rebrand required no
migration. `create_all` only ever adds tables; schema changes that touch an
existing table are applied by recreating the local SQLite file in development.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from elipsis_api.database import Base


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    industry = Column(String)
    sub_industry = Column(String)
    employee_count = Column(Integer)
    revenue_band = Column(String)
    country = Column(String)
    city = Column(String)
    created_at = Column(String, default=_now)


class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    name = Column(String, nullable=False)
    head = Column(String)
    staff_count = Column(Integer)
    created_at = Column(String, default=_now)


class Questionnaire(Base):
    __tablename__ = "questionnaires"
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    department = Column(String, nullable=False)
    estimated_minutes = Column(Integer)
    active = Column(Integer, default=1)


class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True)
    questionnaire_id = Column(Integer, ForeignKey("questionnaires.id"), nullable=False)
    code = Column(String, nullable=False)
    # Which answer scale this question uses (constants.SCALES key).
    scale = Column(String)
    subdomain = Column(String, nullable=False)
    pillar = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    # Why leadership should care about this question, shown under the prompt.
    why = Column(Text)
    weight = Column(Integer, default=3)
    evidence_required = Column(Integer, default=0)
    position = Column(Integer, nullable=False)


class Assessment(Base):
    __tablename__ = "assessments"
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"))
    questionnaire_id = Column(Integer, ForeignKey("questionnaires.id"), nullable=False)
    respondent = Column(String)
    status = Column(String, default="in_progress")
    started_at = Column(String, default=_now)
    completed_at = Column(String)
    readiness_index = Column(Float)
    department_score = Column(Float)
    confidence_index = Column(Float)
    maturity_band = Column(String)

    organization = relationship("Organization")
    department = relationship("Department")
    questionnaire = relationship("Questionnaire")


class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = (UniqueConstraint("assessment_id", "question_id"),)
    id = Column(Integer, primary_key=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    score = Column(Integer)
    evidence = Column(String, default="none")


class PillarScore(Base):
    __tablename__ = "pillar_scores"
    id = Column(Integer, primary_key=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    pillar = Column(String, nullable=False)
    score = Column(Float)
    weight = Column(Float)


class SubdomainScore(Base):
    __tablename__ = "subdomain_scores"
    id = Column(Integer, primary_key=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    subdomain = Column(String, nullable=False)
    score = Column(Float)


class MetricScore(Base):
    """One row per derived executive metric per assessment (36 rows)."""
    __tablename__ = "metric_scores"
    id = Column(Integer, primary_key=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    metric = Column(String, nullable=False)
    pillar = Column(String, nullable=False)
    label = Column(String)
    kind = Column(String)          # "score" (higher better) | "risk" (higher worse)
    score = Column(Float)
    reading = Column(Text)


class PainPoint(Base):
    __tablename__ = "pain_points"
    id = Column(Integer, primary_key=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    trigger_code = Column(String)
    title = Column(String, nullable=False)
    severity = Column(String)
    impact_score = Column(Float)
    detail = Column(Text)


class Recommendation(Base):
    __tablename__ = "recommendations"
    id = Column(Integer, primary_key=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    pain_point_id = Column(Integer, ForeignKey("pain_points.id"))
    title = Column(String, nullable=False)
    solution = Column(Text)
    technology = Column(String)
    complexity = Column(String)
    priority_score = Column(Float)
    horizon = Column(String)
    expected_roi = Column(Float)
    # 1 Quick Wins | 2 Process Automation | 3 AI Enablement
    phase = Column(Integer)


class FinancialModel(Base):
    __tablename__ = "financial_models"
    id = Column(Integer, primary_key=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    current_cost = Column(Float)
    future_cost = Column(Float)
    annual_savings = Column(Float)
    investment = Column(Float)
    roi = Column(Float)
    payback_months = Column(Float)


class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    report_type = Column(String, nullable=False)
    generated_at = Column(String, default=_now)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String)
    role = Column(String, default="client")
    password_hash = Column(String, nullable=False)
    created_at = Column(String, default=_now)


class AuthSession(Base):
    __tablename__ = "sessions"
    token = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(String, default=_now)