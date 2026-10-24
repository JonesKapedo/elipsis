"""Pydantic request/response schemas for the Elipsis API."""


from pydantic import BaseModel, Field


class HealthOut(BaseModel):
    status: str
    brand: str
    index: str
    database: str


class OrganizationIn(BaseModel):
    name: str = Field(..., min_length=1)
    industry: str | None = None
    sub_industry: str | None = None
    employee_count: int | None = Field(None, ge=0)
    revenue_band: str | None = None
    country: str | None = None
    city: str | None = None
    legal_name: str | None = None
    registration_number: str | None = None
    tax_id: str | None = None
    address: str | None = None
    timezone: str | None = None
    fiscal_year_start: str | None = None
    operating_sites: str | None = None
    primary_services: str | None = None
    systems_used: str | None = None
    website: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    description: str | None = None


class OrganizationOut(OrganizationIn):
    id: int


class AssessmentIn(BaseModel):
    organization_id: int | None = None
    organization: OrganizationIn | None = None
    department: str = "Operations"
    respondent: str | None = None
    mode: str | None = "pulse"
    source: str | None = "self"


class AnswerIn(BaseModel):
    question_id: int
    score: int = Field(..., ge=0, le=5)
    evidence: str = "none"


class SubmitIn(BaseModel):
    answers: list[AnswerIn]


class AssessmentOut(BaseModel):
    id: int
    organization_id: int
    department_id: int | None
    questionnaire_id: int
    respondent: str | None
    status: str
    readiness_index: float | None
    maturity_band: str | None
    confidence_index: float | None


class OptionOut(BaseModel):
    """One selectable answer for a question."""
    score: int
    emoji: str
    label: str
    help: str


class QuestionOut(BaseModel):
    id: int
    code: str
    scale: str | None = None
    options: list[OptionOut] = Field(default_factory=list)
    subdomain: str
    pillar: str
    text: str
    why: str | None = None
    weight: int
    evidence_required: bool


class PainPointOut(BaseModel):
    trigger: str
    title: str
    severity: str
    impact: float
    detail: str


class RecommendationOut(BaseModel):
    trigger: str
    title: str
    solution: str
    technology: str
    complexity: str
    priority: float
    horizon: str
    roi: float
    phase: int | None = None
    pillar: str | None = None


class AssumptionsOut(BaseModel):
    """The working behind the financial impact, so a client can check it."""
    staff: int
    hourly_rate: float
    working_hours_per_month: int
    labour_line: float
    savings_cap: float
    max_savings_share: float
    capped: bool
    cap_applied: float
    raw_savings: float
    scale_factor: float
    friction_cost: float
    hours_freed: int


class FinancialOut(BaseModel):
    assumptions: AssumptionsOut | None = None
    current_cost: float
    future_cost: float
    annual_savings: float
    investment: float
    roi: float
    payback_months: float


class MetricOut(BaseModel):
    """One derived executive metric."""
    code: str
    pillar: str
    label: str
    kind: str          # "score" (higher better) | "risk" (higher worse)
    value: float
    reading: str


class PhaseOut(BaseModel):
    number: int
    label: str
    horizon: str
    note: str
    count: int
    value: float
    items: list[RecommendationOut]


class BenchmarkOut(BaseModel):
    """Industry / size-band benchmark comparison."""
    industry: str
    size_band: str
    industry_avg: float
    size_avg: float
    digital_avg: float
    automation_avg: float
    ai_avg: float
    percentile: float
    pillar_bench: list[dict[str, object]]


class AuthOut(BaseModel):
    user_id: int
    email: str
    name: str
    role: str
    token: str


class LoginIn(BaseModel):
    email: str
    password: str


class LoginOut(BaseModel):
    token: str
    user: AuthOut


class ResultOut(BaseModel):
    readiness_index: float
    organisation_score: float
    department_score: float
    confidence_index: float
    confidence_band: str
    maturity_band: str
    pillars: dict[str, float]
    subdomains: dict[str, float]
    metrics: dict[str, float]
    metric_rows: list[MetricOut]
    metrics_by_pillar: dict[str, list[MetricOut]]
    answered: int
    total: int
    pain_points: list[PainPointOut]
    recommendations: list[RecommendationOut]
    roadmap: list[PhaseOut]
    top_opportunities: list[str]
    financial: FinancialOut
    benchmarks: BenchmarkOut | None = None
    sample_report: dict[str, object] | None = None
    report_url: str | None = None


class SampleReportOut(BaseModel):
    org_name: str
    version: str
    ready_on: str
    index: int
    maturity: str
    pillars: dict[str, float]
    metrics: dict[str, float]
    pain_points: list[dict[str, object]]
    recommendations: list[dict[str, object]]
    roadmap: list[dict[str, object]]
    financial: dict[str, object]


class MarketplaceRequestIn(BaseModel):
    organization_id: int | None = None
    assessment_id: int | None = None
    title: str = Field(..., min_length=3, max_length=160)
    description: str | None = None
    expectations: str | None = None
    specifications: str | None = None
    contact_preference: str | None = None
    budget_range: str | None = None
    deadline: str | None = None
    location: str | None = None


class BidSubmissionIn(BaseModel):
    proposal: str = Field(..., min_length=10)
    estimated_cost: float = Field(..., ge=0)
    timeline: str = Field(..., min_length=1, max_length=120)
    roadmap_document_id: int | None = None


class PreferredBidIn(BaseModel):
    bid_id: int
