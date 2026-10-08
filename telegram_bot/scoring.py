"""Preliminary automation-opportunity scoring for the Telegram quick check.

The public functions ``score_tasks`` and ``estimate_roi`` keep their original
signatures and outputs for valid input, but now validate, coerce and bound
every value so malformed chat input can never crash the bot or produce
nonsense (negative, infinite or absurdly large) figures.  ``assess`` returns a
richer, structured result for callers that want more than a band.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from constants import CURRENCY, DEFAULT_HOURLY_RATE

WEEKS_PER_MONTH = 4.33
HOURS_PER_FTE_MONTH = 40 * WEEKS_PER_MONTH
DEFAULT_AUTOMATION_SHARE = 0.4

HIGH_THRESHOLD_MINUTES = 2000
MEDIUM_THRESHOLD_MINUTES = 600
SCORE_CEILING_MINUTES = 40_000

FIELD_ALIASES = {
    "tasks_per_week": ("tasks_per_week", "tasks", "weekly_tasks"),
    "minutes_per_task": ("minutes_per_task", "minutes", "task_minutes"),
    "staff": ("staff", "people", "team_size", "headcount"),
}

FIELD_LIMITS = {
    "tasks_per_week": (0, 10_000, True),
    "minutes_per_task": (0, 600, False),
    "staff": (0, 100_000, True),
}


class ScoringInputError(ValueError):
    """Raised when an input cannot be interpreted as a usable number."""


@dataclass
class QuickCheckResult:
    band: str
    opportunity_score: float
    weekly_minutes: float
    monthly_hours: float
    fte_equivalent: float
    monthly_cost: float
    monthly_savings: float
    annual_savings: float
    automation_share: float
    hourly_rate: float
    clamped: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def summary_lines(self, currency: str = CURRENCY) -> list[str]:
        lines = [
            f"Automation opportunity: {self.band} ({self.opportunity_score:.0f}/100)",
            f"Repetitive workload: {self.monthly_hours:,.0f} hours/month "
            f"(~{self.fte_equivalent:.1f} full-time people)",
            f"Estimated monthly savings: {currency} {self.monthly_savings:,.0f}",
            f"Estimated annual savings: {currency} {self.annual_savings:,.0f}",
        ]
        if self.clamped:
            lines.append("Note: some answers were capped to realistic limits ("
                         + ", ".join(self.clamped) + ").")
        return lines


def _coerce(value: Any, name: str) -> tuple[float, bool]:
    """Return (number, was_clamped) for one field, or raise ScoringInputError."""
    minimum, maximum, integer = FIELD_LIMITS[name]
    if value is None or isinstance(value, bool):
        raise ScoringInputError(f"{name} is required")
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "").replace("_", "").rstrip("%").strip()
        if not cleaned:
            raise ScoringInputError(f"{name} is required")
        try:
            value = float(cleaned)
        except ValueError as exc:
            raise ScoringInputError(f"{name} must be a number") from exc
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ScoringInputError(f"{name} must be a number") from exc
    if not math.isfinite(number):
        raise ScoringInputError(f"{name} must be a finite number")
    if number < minimum:
        raise ScoringInputError(f"{name} cannot be negative")
    clamped = number > maximum
    number = min(number, maximum)
    if integer:
        number = float(round(number))
    return number, clamped


def _lookup(data: Mapping[str, Any], name: str) -> Any:
    for key in FIELD_ALIASES[name]:
        if key in data and data[key] is not None:
            return data[key]
    return None


def normalise_inputs(data: Mapping[str, Any]) -> tuple[dict[str, float], list[str]]:
    """Validate a quick-check payload, resolving aliases and bounding values."""
    if not isinstance(data, Mapping):
        raise ScoringInputError("quick-check data must be a mapping")
    values, clamped = {}, []
    for name in FIELD_ALIASES:
        number, was_clamped = _coerce(_lookup(data, name), name)
        values[name] = number
        if was_clamped:
            clamped.append(name)
    return values, clamped


def weekly_workload_minutes(data: Mapping[str, Any]) -> float:
    values, _ = normalise_inputs(data)
    return values["tasks_per_week"] * values["minutes_per_task"] * values["staff"]


def band_for_minutes(weekly_minutes: float) -> str:
    if weekly_minutes > HIGH_THRESHOLD_MINUTES:
        return "High"
    if weekly_minutes > MEDIUM_THRESHOLD_MINUTES:
        return "Medium"
    return "Low"


def opportunity_score(weekly_minutes: float) -> float:
    """0-100 log-scaled score so very large teams do not dominate linearly."""
    if weekly_minutes <= 0:
        return 0.0
    ratio = math.log10(1 + weekly_minutes) / math.log10(1 + SCORE_CEILING_MINUTES)
    return round(max(0.0, min(1.0, ratio)) * 100, 1)


def _safe_rate(hourly_rate: Any) -> float:
    try:
        rate = float(hourly_rate)
    except (TypeError, ValueError):
        return float(DEFAULT_HOURLY_RATE)
    if not math.isfinite(rate) or rate < 0:
        return float(DEFAULT_HOURLY_RATE)
    return rate


def _safe_share(share: Any) -> float:
    try:
        value = float(share)
    except (TypeError, ValueError):
        return DEFAULT_AUTOMATION_SHARE
    if not math.isfinite(value):
        return DEFAULT_AUTOMATION_SHARE
    return max(0.0, min(1.0, value))


def score_tasks(data: Mapping[str, Any]) -> str:
    """Preliminary automation-opportunity band from overall team workload."""
    return band_for_minutes(weekly_workload_minutes(data))


def estimate_roi(data: Mapping[str, Any], hourly_rate: float = DEFAULT_HOURLY_RATE,
                 automation_share: float = DEFAULT_AUTOMATION_SHARE) -> float:
    """Estimated monthly savings, in the Elipsis reporting currency (KES)."""
    hours = weekly_workload_minutes(data) / 60 * WEEKS_PER_MONTH
    return hours * _safe_rate(hourly_rate) * _safe_share(automation_share)


def assess(data: Mapping[str, Any], hourly_rate: float = DEFAULT_HOURLY_RATE,
           automation_share: float = DEFAULT_AUTOMATION_SHARE) -> QuickCheckResult:
    """Full structured quick-check result."""
    values, clamped = normalise_inputs(data)
    weekly = values["tasks_per_week"] * values["minutes_per_task"] * values["staff"]
    rate = _safe_rate(hourly_rate)
    share = _safe_share(automation_share)
    monthly_hours = weekly / 60 * WEEKS_PER_MONTH
    monthly_cost = monthly_hours * rate
    monthly_savings = monthly_cost * share
    return QuickCheckResult(
        band=band_for_minutes(weekly),
        opportunity_score=opportunity_score(weekly),
        weekly_minutes=round(weekly, 1),
        monthly_hours=round(monthly_hours, 1),
        fte_equivalent=round(monthly_hours / HOURS_PER_FTE_MONTH, 2),
        monthly_cost=round(monthly_cost, 2),
        monthly_savings=round(monthly_savings, 2),
        annual_savings=round(monthly_savings * 12, 2),
        automation_share=share,
        hourly_rate=rate,
        clamped=clamped,
    )
