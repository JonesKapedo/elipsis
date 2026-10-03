"""SQLAlchemy ORM models for Elipsis.

The persisted column names are deliberately neutral (`readiness_index`,
`pillar`, `subdomain`) so that the Turbinez -> Elipsis rebrand required no
migration. `create_all` only ever adds tables; schema changes that touch an
existing table are applied by recreating the local SQLite file in development.
"""

from datetime import datetime, timezone

from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from elipsis_api.database import Base


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    industry: Mapped[str | None] = mapped_column(String)
    sub_industry: Mapped[str | None] = mapped_column(String)
    employee_count: Mapped[int | None] = mapped_column(Integer)
    revenue_band: Mapped[str | None] = mapped_column(String)
    country: Mapped[str | None] = mapped_column(String)
    city: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[str | None] = mapped_column(String, default=_now)


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    head: Mapped[str | None] = mapped_column(String)
    staff_count: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[str | None] = mapped_column(String, default=_now)


class Questionnaire(Base):
    __tablename__ = "questionnaires"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)
    department: Mapped[str] = mapped_column(String, nullable=False)
    estimated_minutes: Mapped[int | None] = mapped_column(Integer)
    active: Mapped[int | None] = mapped_column(Integer, default=1)


class Question(Base):
    __tablename__ = "questions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    questionnaire_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("questionnaires.id"), nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False)
    # Which answer scale this question uses (constants.SCALES key).
    scale: Mapped[str | None] = mapped_column(String)
    subdomain: Mapped[str] = mapped_column(String, nullable=False)
    pillar: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # Why leadership should care about this question, shown under the prompt.
    why: Mapped[str | None] = mapped_column(Text)
    weight: Mapped[int | None] = mapped_column(Integer, default=3)
    evidence_required: Mapped[int | None] = mapped_column(Integer, default=0)
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class Assessment(Base):
    __tablename__ = "assessments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False)
    department_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("departments.id"))
    questionnaire_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("questionnaires.id"), nullable=False)
    respondent: Mapped[str | None] = mapped_column(String)
    status: Mapped[str | None] = mapped_column(String, default="in_progress")
    started_at: Mapped[str | None] = mapped_column(String, default=_now)
    completed_at: Mapped[str | None] = mapped_column(String)
    readiness_index: Mapped[float | None] = mapped_column(Float)
    department_score: Mapped[float | None] = mapped_column(Float)
    confidence_index: Mapped[float | None] = mapped_column(Float)
    maturity_band: Mapped[str | None] = mapped_column(String)

    organization: Mapped["Organization"] = relationship()
    department: Mapped["Department"] = relationship()
    questionnaire: Mapped["Questionnaire"] = relationship()


class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = (UniqueConstraint("assessment_id", "question_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assessments.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("questions.id"), nullable=False)
    score: Mapped[int | None] = mapped_column(Integer)
    evidence: Mapped[str | None] = mapped_column(String, default="none")


class PillarScore(Base):
    __tablename__ = "pillar_scores"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assessments.id"), nullable=False)
    pillar: Mapped[str] = mapped_column(String, nullable=False)
    score: Mapped[float | None] = mapped_column(Float)
    weight: Mapped[float | None] = mapped_column(Float)


class SubdomainScore(Base):
    __tablename__ = "subdomain_scores"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assessments.id"), nullable=False)
    subdomain: Mapped[str] = mapped_column(String, nullable=False)
    score: Mapped[float | None] = mapped_column(Float)


class MetricScore(Base):
    """One row per derived executive metric per assessment (36 rows)."""
    __tablename__ = "metric_scores"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assessments.id"), nullable=False)
    metric: Mapped[str] = mapped_column(String, nullable=False)
    pillar: Mapped[str] = mapped_column(String, nullable=False)
    label: Mapped[str | None] = mapped_column(String)
    kind: Mapped[str | None] = mapped_column(String)  # "score" (higher better) | "risk" (higher worse)
    score: Mapped[float | None] = mapped_column(Float)
    reading: Mapped[str | None] = mapped_column(Text)


class PainPoint(Base):
    __tablename__ = "pain_points"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assessments.id"), nullable=False)
    trigger_code: Mapped[str | None] = mapped_column(String)
    title: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str | None] = mapped_column(String)
    impact_score: Mapped[float | None] = mapped_column(Float)
    detail: Mapped[str | None] = mapped_column(Text)


class Recommendation(Base):
    __tablename__ = "recommendations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assessments.id"), nullable=False)
    pain_point_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("pain_points.id"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    solution: Mapped[str | None] = mapped_column(Text)
    technology: Mapped[str | None] = mapped_column(String)
    complexity: Mapped[str | None] = mapped_column(String)
    priority_score: Mapped[float | None] = mapped_column(Float)
    horizon: Mapped[str | None] = mapped_column(String)
    expected_roi: Mapped[float | None] = mapped_column(Float)
    # 1 Quick Wins | 2 Process Automation | 3 AI Enablement
    phase: Mapped[int | None] = mapped_column(Integer)


class FinancialModel(Base):
    __tablename__ = "financial_models"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assessments.id"), nullable=False)
    current_cost: Mapped[float | None] = mapped_column(Float)
    future_cost: Mapped[float | None] = mapped_column(Float)
    annual_savings: Mapped[float | None] = mapped_column(Float)
    investment: Mapped[float | None] = mapped_column(Float)
    roi: Mapped[float | None] = mapped_column(Float)
    payback_months: Mapped[float | None] = mapped_column(Float)


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assessments.id"), nullable=False)
    report_type: Mapped[str] = mapped_column(String, nullable=False)
    generated_at: Mapped[str | None] = mapped_column(String, default=_now)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String)
    role: Mapped[str | None] = mapped_column(String, default="client")
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str | None] = mapped_column(String, default=_now)


class AuthSession(Base):
    __tablename__ = "sessions"
    token: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[str | None] = mapped_column(String, default=_now)