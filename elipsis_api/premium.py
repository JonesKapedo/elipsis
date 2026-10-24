"""Premium workspace pricing and entitlement definitions."""

from __future__ import annotations

import os as _os

CURRENCY = "USD"
MONTHLY_USD = 29
ANNUAL_USD = 380
FULL_ASSESSMENT_USD = 49
SWITCH_TOPUP_USD = 24.50
SWITCH_TOPUP_COUNT = 3
MONTHLY_DAYS = 31
ANNUAL_DAYS = 365

BIDDER_PLANS = {
    "monthly": {"label": "Monthly", "price": 39, "days": 30},
    "six_months": {"label": "Six months", "price": 119, "days": 182},
    "yearly": {"label": "Annual", "price": 219, "days": 365},
}

PLANS = {
    "monthly": {
        "label": "Monthly pass",
        "price": MONTHLY_USD,
        "days": MONTHLY_DAYS,
        "note": "One payment, 31 days of Premium.",
    },
    "annual": {
        "label": "Annual pass",
        "price": ANNUAL_USD,
        "days": ANNUAL_DAYS,
        "note": "One payment, 365 days of Premium.",
    },
}

FEATURES = (
    ("Multiple companies", "Keep separate operating profiles, diagnostics, and benchmarks under one account."),
    ("Team questionnaires", "Send department questionnaires, set deadlines and target roles, and combine responses into one diagnostic."),
    ("Board packs", "Download PDF, Excel, and JSON, print a clean report, or share a read-only board link."),
)


def plan(cycle: str | None) -> dict:
    return PLANS["annual" if cycle == "annual" else "monthly"]


def amount_minor(cycle: str | None) -> int:
    return int(plan(cycle)["price"] * 100)


REQUESTER_PLAN_ENV = {
    "monthly": "PAYSTACK_PLAN_PREMIUM_MONTHLY",
    "annual": "PAYSTACK_PLAN_PREMIUM_ANNUAL",
}
BIDDER_PLAN_ENV = {
    "monthly": "PAYSTACK_PLAN_BIDDER_MONTHLY",
    "six_months": "PAYSTACK_PLAN_BIDDER_SIX_MONTHS",
    "yearly": "PAYSTACK_PLAN_BIDDER_YEARLY",
}


def requester_plan_code(cycle: str | None) -> str:
    key = "annual" if cycle == "annual" else "monthly"
    return (_os.getenv(REQUESTER_PLAN_ENV[key]) or "").strip()


def bidder_plan_code(tier: str | None) -> str:
    return (_os.getenv(BIDDER_PLAN_ENV.get(tier or "", "")) or "").strip()


def recurring_configured(purpose: str) -> bool:
    if purpose == "bidder":
        return any((_os.getenv(name) or "").strip() for name in BIDDER_PLAN_ENV.values())
    return any((_os.getenv(name) or "").strip() for name in REQUESTER_PLAN_ENV.values())


def plan_for_code(code: str | None) -> tuple[str, str] | None:
    code = (code or "").strip()
    if not code:
        return None
    for cycle, name in REQUESTER_PLAN_ENV.items():
        if (_os.getenv(name) or "").strip() == code:
            return "premium", cycle
    for tier, name in BIDDER_PLAN_ENV.items():
        if (_os.getenv(name) or "").strip() == code:
            return "bidder_plan", tier
    return None
