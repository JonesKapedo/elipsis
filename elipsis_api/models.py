"""SQLAlchemy ORM models for Elipsis."""

from datetime import datetime, timezone

from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint, Boolean
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
    # New marketplace fields
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"))
    annual_revenue_min: Mapped[float | None] = mapped_column(Float)
    annual_revenue_max: Mapped[float | None] = mapped_column(Float)
    company_size: Mapped[str | None] = mapped_column(String)
    contact_email: Mapped[str | None] = mapped_column(String)
    contact_phone: Mapped[str | None] = mapped_column(String)
    website: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)


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
    scale: Mapped[str | None] = mapped_column(String)
    subdomain: Mapped[str] = mapped_column(String, nullable=False)
    pillar: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
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
    # New field for scope selection
    scope: Mapped[str | None] = mapped_column(String, default="whole_organization")

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
    __tablename__ = "metric_scores"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assessments.id"), nullable=False)
    metric: Mapped[str] = mapped_column(String, nullable=False)
    pillar: Mapped[str] = mapped_column(String, nullable=False)
    label: Mapped[str | None] = mapped_column(String)
    kind: Mapped[str | None] = mapped_column(String)
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
    # New marketplace fields
    user_type: Mapped[str | None] = mapped_column(String, default="client")
    is_admin: Mapped[bool | None] = mapped_column(Boolean, default=False)
    last_login: Mapped[str | None] = mapped_column(String)


class AuthSession(Base):
    __tablename__ = "sessions"
    token: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[str | None] = mapped_column(String, default=_now)


# services.py and services_auth.py both construct models.Session.
Session = AuthSession


class ShareLink(Base):
    __tablename__ = "share_links"
    token: Mapped[str] = mapped_column(String, primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assessments.id"), nullable=False)
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"))
    label: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[str | None] = mapped_column(String, default=_now)


class ContactMessage(Base):
    """Inbound contact form submissions."""
    __tablename__ = "contact_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    organization: Mapped[str | None] = mapped_column(String)
    topic: Mapped[str | None] = mapped_column(String)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str | None] = mapped_column(String, default=_now)


class RoadmapItem(Base):
    __tablename__ = "roadmap_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assessments.id"), nullable=False)
    phase: Mapped[int | None] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String, nullable=False)
    solution: Mapped[str | None] = mapped_column(Text)
    technology: Mapped[str | None] = mapped_column(String)
    complexity: Mapped[str | None] = mapped_column(String)
    priority: Mapped[float | None] = mapped_column(Float)
    horizon: Mapped[str | None] = mapped_column(String)
    roi: Mapped[float | None] = mapped_column(Float)
    kpi: Mapped[str | None] = mapped_column(String)


class RoadmapPhase(Base):
    __tablename__ = "roadmap_phases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assessments.id"), nullable=False)
    number: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String, nullable=False)
    horizon: Mapped[str | None] = mapped_column(String)
    note: Mapped[str | None] = mapped_column(Text)
    count: Mapped[int | None] = mapped_column(Integer)


class OrgOwner(Base):
    """Links a user to organisations they created. Assessments stay free."""
    __tablename__ = "org_owners"
    __table_args__ = (UniqueConstraint("user_id", "organization_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False)
    created_at: Mapped[str | None] = mapped_column(String, default=_now)


# ============================================================================
# NEW MARKETPLACE MODELS
# ============================================================================

class BidderCompany(Base):
    """Service provider companies that deliver automation solutions."""
    __tablename__ = "bidder_companies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    company_name: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str | None] = mapped_column(String)
    services_offered: Mapped[str | None] = mapped_column(Text)
    rate_card: Mapped[str | None] = mapped_column(Text)
    contact_email: Mapped[str] = mapped_column(String, nullable=False)
    contact_phone: Mapped[str | None] = mapped_column(String)
    website: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)
    experience_years: Mapped[int | None] = mapped_column(Integer)
    subscription_status: Mapped[str | None] = mapped_column(String, default="inactive")
    subscription_expires_at: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[str | None] = mapped_column(String, default=_now)

    user: Mapped["User"] = relationship()


class BidderPortfolio(Base):
    """Portfolio images and work samples for bidder companies."""
    __tablename__ = "bidder_portfolio"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bidder_company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bidder_companies.id"), nullable=False)
    image_url: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str | None] = mapped_column(String, default=_now)


class PhysicalAssessmentRequest(Base):
    """Requests for physical assessment and automation delivery from client companies."""
    __tablename__ = "physical_assessment_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    requirements: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String, default="pending")
    payment_status: Mapped[str | None] = mapped_column(String, default="unpaid")
    payment_amount: Mapped[float | None] = mapped_column(Float)
    admin_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str | None] = mapped_column(String, default=_now)
    verified_at: Mapped[str | None] = mapped_column(String)
    published_at: Mapped[str | None] = mapped_column(String)
    completed_at: Mapped[str | None] = mapped_column(String)

    organization: Mapped["Organization"] = relationship()
    user: Mapped["User"] = relationship()


class RequestDocument(Base):
    """Documents attached to physical assessment requests."""
    __tablename__ = "request_documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("physical_assessment_requests.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    file_url: Mapped[str] = mapped_column(String, nullable=False)
    file_size: Mapped[int | None] = mapped_column(Integer)
    uploaded_at: Mapped[str | None] = mapped_column(String, default=_now)


class BidSubmission(Base):
    """Bids placed by bidder companies on published requests."""
    __tablename__ = "bid_submissions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("physical_assessment_requests.id"), nullable=False)
    bidder_company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bidder_companies.id"), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_timeline: Mapped[str | None] = mapped_column(String)
    proposed_cost: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str | None] = mapped_column(String, default="submitted")
    created_at: Mapped[str | None] = mapped_column(String, default=_now)

    request: Mapped["PhysicalAssessmentRequest"] = relationship()
    bidder_company: Mapped["BidderCompany"] = relationship()


class BidderFeedback(Base):
    """Feedback from client companies about bidder companies after service delivery."""
    __tablename__ = "bidder_feedback"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bidder_company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bidder_companies.id"), nullable=False)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("physical_assessment_requests.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    rating: Mapped[int | None] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str | None] = mapped_column(String, default=_now)

    bidder_company: Mapped["BidderCompany"] = relationship()


class Subscription(Base):
    """Subscription records for bidder companies."""
    __tablename__ = "subscriptions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bidder_company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bidder_companies.id"), nullable=False)
    plan_type: Mapped[str | None] = mapped_column(String, default="monthly")
    amount: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(String, default="USD")
    status: Mapped[str | None] = mapped_column(String, default="active")
    started_at: Mapped[str | None] = mapped_column(String, default=_now)
    expires_at: Mapped[str | None] = mapped_column(String)
    cancelled_at: Mapped[str | None] = mapped_column(String)
