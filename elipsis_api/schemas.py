"""Pydantic request/response schemas for the Elipsis API."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class HealthOut(BaseModel):
    status: str
    brand: str
    index: str
    database: str


class OrganizationIn(BaseModel):
    name: str = Field(..., min_length=1)
    industry: Optional[str] = None
    sub_industry: Optional[str] = None
    employee_count: Optional[int] = Field(None, ge=0)
    revenue_band: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None


class OrganizationOut(OrganizationIn):
    id: int


class AssessmentIn(BaseModel):
    organization_id: Optional[int] = None
    organization: Optional[OrganizationIn] = None
    department: str = "Operations"
    respondent: Optional[str] = None


class AnswerIn(BaseModel):
    question_id: int
    score: int = Field(..., ge=0, le=5)
    evidence: str = "none"


class SubmitIn(BaseModel):
    answers: List[AnswerIn]


class AssessmentOut(BaseModel):
    id: int
    organization_id: int
    department_id: Optional[int]
    questionnaire_id: int
    respondent: Optional[str]
    status: str
    readiness_index: Optional[float]
    maturity_band: Optional[str]
    confidence_index: Optional[float]


class OptionOut(BaseModel):
    """One selectable answer for a question."""
    score: int
    emoji: str
    label: str
    help: str


class QuestionOut(BaseModel):
    id: int
    code: str
    scale: Optional[str] = None
    options: List[OptionOut] = Field(default_factory=list)
    subdomain: str
    pillar: str
    text: str
    why: Optional[str] = None
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
    phase: Optional[int] = None
    pillar: Optional[str] = None


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
    assumptions: Optional[AssumptionsOut] = None
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
    items: List[RecommendationOut]


class ResultOut(BaseModel):
    readiness_index: float
    organisation_score: float
    # Retained for backward compatibility with pre-rebrand API clients.
    department_score: float
    confidence_index: float
    confidence_band: str
    maturity_band: str
    pillars: Dict[str, float]
    subdomains: Dict[str, float]
    metrics: Dict[str, float]
    metric_rows: List[MetricOut]
    metrics_by_pillar: Dict[str, List[MetricOut]]
    answered: int
    total: int
    pain_points: List[PainPointOut]
    recommendations: List[RecommendationOut]
    roadmap: List[PhaseOut]
    top_opportunities: List[str]
    financial: FinancialOut