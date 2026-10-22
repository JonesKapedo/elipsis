"""Premium workspace pricing and entitlement definitions."""

from __future__ import annotations

CURRENCY = "USD"
MONTHLY_USD = 39
ANNUAL_USD = 390
MONTHLY_DAYS = 31
ANNUAL_DAYS = 365

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
        "note": "One payment, 365 days of Premium. Two months free.",
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
