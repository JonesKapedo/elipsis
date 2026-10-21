"""SQLAlchemy ORM models for Elipsis."""

from datetime import UTC, datetime

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from elipsis_api.database import Base


def _now():
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


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
    review_due_at: Mapped[str | None] = mapped_column(String)
    review_note: Mapped[str | None] = mapped_column(Text)

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
    assumptions_json: Mapped[str | None] = mapped_column(Text)


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
    email_verified: Mapped[bool | None] = mapped_column(Boolean, default=True)
    verification_token: Mapped[str | None] = mapped_column(String)
    verification_sent_at: Mapped[str | None] = mapped_column(String)
    reset_token: Mapped[str | None] = mapped_column(String)
    reset_expires_at: Mapped[str | None] = mapped_column(String)


class AuthSession(Base):
    __tablename__ = "sessions"
    token: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[str | None] = mapped_column(String, default=_now)
    expires_at: Mapped[str | None] = mapped_column(String)

    @property
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        from datetime import datetime
        try:
            return datetime.fromisoformat(self.expires_at) < datetime.now(UTC).replace(tzinfo=None)
        except ValueError:
            return True


# services.py and services_auth.py both construct models.Session.
Session = AuthSession


class ShareLink(Base):
    __tablename__ = "share_links"
    token: Mapped[str] = mapped_column(String, primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assessments.id"), nullable=False)
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"))
    label: Mapped[str | None] = mapped_column(String)
    expires_at: Mapped[str | None] = mapped_column(String)
    last_viewed_at: Mapped[str | None] = mapped_column(String)
    view_count: Mapped[int | None] = mapped_column(Integer, default=0)
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
    owner: Mapped[str | None] = mapped_column(String)
    owner_phone: Mapped[str | None] = mapped_column(String)
    due_date: Mapped[str | None] = mapped_column(String)
    status: Mapped[str | None] = mapped_column(String, default="not_started")
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str | None] = mapped_column(String, default=_now)
    updated_at: Mapped[str | None] = mapped_column(String, default=_now)


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
    contact_email: Mapped[str | None] = mapped_column(String)
    contact_phone: Mapped[str | None] = mapped_column(String)
    website: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)
    years_in_business: Mapped[int | None] = mapped_column(Integer)
    team_size: Mapped[int | None] = mapped_column(Integer)
    subscription_status: Mapped[str | None] = mapped_column(String, default="inactive")
    subscription_tier: Mapped[str | None] = mapped_column(String)
    subscription_expires_at: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[str | None] = mapped_column(String, default=_now)

    user: Mapped["User"] = relationship()


class BidderPortfolio(Base):
    """Portfolio images and work samples for bidder companies."""
    __tablename__ = "bidder_portfolio"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bidder_company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bidder_companies.id"), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String)
    project_name: Mapped[str | None] = mapped_column(String)
    project_url: Mapped[str | None] = mapped_column(String)
    s3_key: Mapped[str | None] = mapped_column(String)
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
    message: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    requirements: Mapped[str | None] = mapped_column(Text)
    budget_range: Mapped[str | None] = mapped_column(String)
    deadline: Mapped[str | None] = mapped_column(String)
    location: Mapped[str | None] = mapped_column(String)
    status: Mapped[str | None] = mapped_column(String, default="pending")
    payment_status: Mapped[str | None] = mapped_column(String, default="unpaid")
    payment_amount: Mapped[float | None] = mapped_column(Float)
    admin_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str | None] = mapped_column(String, default=_now)
    verified_at: Mapped[str | None] = mapped_column(String)
    verified_by_admin: Mapped[bool | None] = mapped_column(Boolean, default=False)
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
    file_name: Mapped[str | None] = mapped_column(String)
    filename: Mapped[str | None] = mapped_column(String)
    file_url: Mapped[str] = mapped_column(String, nullable=False)
    file_type: Mapped[str | None] = mapped_column(String)
    s3_key: Mapped[str | None] = mapped_column(String)
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
    message: Mapped[str | None] = mapped_column(Text)
    proposal: Mapped[str | None] = mapped_column(Text)
    timeline: Mapped[str | None] = mapped_column(String)
    estimated_cost: Mapped[float | None] = mapped_column(Float)
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
    tier: Mapped[str | None] = mapped_column(String, default="monthly")
    amount: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(String, default="KES")
    status: Mapped[str | None] = mapped_column(String, default="active")
    started_at: Mapped[str | None] = mapped_column(String, default=_now)
    start_date: Mapped[str | None] = mapped_column(String)
    expires_at: Mapped[str | None] = mapped_column(String)
    end_date: Mapped[str | None] = mapped_column(String)
    payment_reference: Mapped[str | None] = mapped_column(String)
    cancelled_at: Mapped[str | None] = mapped_column(String)


# ============================================================================
# WORKSPACE / BILLING / COLLECT / MESSAGING
# ============================================================================

class UserPref(Base):
    """Per-user workspace preferences and Pro entitlement."""
    __tablename__ = "user_prefs"
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), primary_key=True)
    symbol: Mapped[str | None] = mapped_column(String, default="E")
    motion: Mapped[str | None] = mapped_column(String, default="on")
    density: Mapped[str | None] = mapped_column(String, default="comfortable")
    pro_until: Mapped[str | None] = mapped_column(String)
    digest_frequency: Mapped[str | None] = mapped_column(String, default="weekly")
    digest_last_sent: Mapped[str | None] = mapped_column(String)
    partner_name: Mapped[str | None] = mapped_column(String)
    partner_footer: Mapped[str | None] = mapped_column(String)
    partner_accent: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[str | None] = mapped_column(String, default=_now)


class Payment(Base):
    """Paystack payment attempt for Pro, physical engagements or subscriptions."""
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    reference: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    purpose: Mapped[str] = mapped_column(String, nullable=False)
    amount_kes: Mapped[float] = mapped_column(Float, nullable=False)
    related_id: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str | None] = mapped_column(String, default="pending")
    created_at: Mapped[str | None] = mapped_column(String, default=_now)
    paid_at: Mapped[str | None] = mapped_column(String)


class PhysicalRequest(Base):
    """Paid physical assessment request submitted from the Pro page."""
    __tablename__ = "physical_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("organizations.id"))
    company_name: Mapped[str] = mapped_column(String, nullable=False)
    package: Mapped[str | None] = mapped_column(String)
    amount_kes: Mapped[float | None] = mapped_column(Float)
    sites: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String, default="awaiting_payment")
    created_at: Mapped[str | None] = mapped_column(String, default=_now)


class TeamLetter(Base):
    """A team invitation / outreach letter captured from the workspace."""
    __tablename__ = "team_letters"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    organization: Mapped[str | None] = mapped_column(String)
    role_title: Mapped[str | None] = mapped_column(String)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str | None] = mapped_column(String, default=_now)


class CollectCampaign(Base):
    """Multi-respondent questionnaire campaign for one organisation."""
    __tablename__ = "collect_campaigns"
    token: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False)
    department_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("departments.id"))
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"))
    title: Mapped[str | None] = mapped_column(String)
    deadline: Mapped[str | None] = mapped_column(String)
    min_respondents: Mapped[int | None] = mapped_column(Integer, default=1)
    allow_anonymous: Mapped[int | None] = mapped_column(Integer, default=0)
    status: Mapped[str | None] = mapped_column(String, default="collecting")
    note: Mapped[str | None] = mapped_column(Text)
    master_assessment_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("assessments.id"))
    created_at: Mapped[str | None] = mapped_column(String, default=_now)


class CollectResponse(Base):
    """One respondent's assessment inside a collect campaign."""
    __tablename__ = "collect_responses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_token: Mapped[str] = mapped_column(
        String, ForeignKey("collect_campaigns.token"), nullable=False)
    assessment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assessments.id"), nullable=False)
    respondent_name: Mapped[str | None] = mapped_column(String)
    respondent_email: Mapped[str | None] = mapped_column(String)
    is_anonymous: Mapped[int | None] = mapped_column(Integer, default=0)
    status: Mapped[str | None] = mapped_column(String, default="in_progress")
    created_at: Mapped[str | None] = mapped_column(String, default=_now)


class Conversation(Base):
    """Two-party conversation, optionally tied to a marketplace request."""
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user1_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    user2_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    request_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("physical_assessment_requests.id"))
    last_message_at: Mapped[str | None] = mapped_column(String, default=_now)
    created_at: Mapped[str | None] = mapped_column(String, default=_now)


class Message(Base):
    """Message inside a conversation."""
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("conversations.id"), nullable=False)
    sender_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool | None] = mapped_column(Boolean, default=False)
    created_at: Mapped[str | None] = mapped_column(String, default=_now)


class AssessmentAssumption(Base):
    """Client-editable financial assumptions for one assessment."""
    __tablename__ = "assessment_assumptions"
    assessment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assessments.id"), primary_key=True)
    staff: Mapped[int | None] = mapped_column(Integer)
    hourly_rate: Mapped[float | None] = mapped_column(Float)
    working_hours_per_month: Mapped[float | None] = mapped_column(Float)
    max_savings_share: Mapped[float | None] = mapped_column(Float)
    annual_revenue: Mapped[float | None] = mapped_column(Float)
    note: Mapped[str | None] = mapped_column(Text)
    updated_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"))
    updated_at: Mapped[str | None] = mapped_column(String, default=_now)


class EvidenceAttachment(Base):
    """A file attached as proof for one assessment answer."""
    __tablename__ = "evidence_attachments"
    __table_args__ = (Index("ix_evidence_attachments_assessment", "assessment_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assessments.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("questions.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    uploaded_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[str | None] = mapped_column(String, default=_now)


class CampaignComment(Base):
    """Facilitator/participant notes on a collection campaign."""
    __tablename__ = "campaign_comments"
    __table_args__ = (Index("ix_campaign_comments_token", "campaign_token"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_token: Mapped[str] = mapped_column(
        String, ForeignKey("collect_campaigns.token"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str | None] = mapped_column(String, default=_now)


class CampaignApproval(Base):
    """Sign-off on a completed collection campaign."""
    __tablename__ = "campaign_approvals"
    __table_args__ = (Index("ix_campaign_approvals_token", "campaign_token"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_token: Mapped[str] = mapped_column(
        String, ForeignKey("collect_campaigns.token"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"))
    decision: Mapped[str] = mapped_column(String, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str | None] = mapped_column(String, default=_now)


class AuditEvent(Base):
    """Immutable, organisation-scoped record of consequential actions."""
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_org", "organization_id"),
        Index("ix_audit_events_created", "created_at"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("organizations.id"))
    assessment_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("assessments.id"))
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String, nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str | None] = mapped_column(String, default=_now)


class SavedView(Base):
    """A named action-board filter for one user."""
    __tablename__ = "saved_views"
    __table_args__ = (UniqueConstraint("user_id", "name"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    query: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[str | None] = mapped_column(String, default=_now)


class NotificationRead(Base):
    """Read state for computed workspace notifications."""
    __tablename__ = "notification_reads"
    __table_args__ = (UniqueConstraint("user_id", "fingerprint"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String, nullable=False)
    read_at: Mapped[str | None] = mapped_column(String, default=_now)


class WebhookEndpoint(Base):
    """An ERP/WMS endpoint that receives workspace events."""
    __tablename__ = "webhook_endpoints"
    __table_args__ = (Index("ix_webhook_endpoints_org", "organization_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    secret: Mapped[str] = mapped_column(String, nullable=False)
    events: Mapped[str | None] = mapped_column(String, default="action.updated,assessment.completed")
    active: Mapped[bool | None] = mapped_column(Boolean, default=True)
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[str | None] = mapped_column(String, default=_now)


class WebhookDelivery(Base):
    """Best-effort delivery log for one webhook event."""
    __tablename__ = "webhook_deliveries"
    __table_args__ = (Index("ix_webhook_deliveries_endpoint", "endpoint_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    endpoint_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("webhook_endpoints.id"), nullable=False)
    event: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String, default="queued")
    response_code: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str | None] = mapped_column(String, default=_now)
    delivered_at: Mapped[str | None] = mapped_column(String)
