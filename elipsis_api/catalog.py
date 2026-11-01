"""Commercial SKU catalog — single source of truth for prices and offers.

Templates and routes must read from here. Do not hardcode a price.
"""

from __future__ import annotations

CURRENCY = "USD"

SKUS: dict[str, dict] = {
    "pulse": {
        "key": "pulse",
        "name": "Pulse",
        "price_usd": 0,
        "billing": "free",
        "tagline": "Your constraint, free.",
        "note": "One operation. No card.",
        "features": [
            "63-question logistics diagnostic",
            "Readiness index and maturity band",
            "Top three constraint names",
            "One sample action",
            "About 25 minutes",
        ],
        "cta": "Start free assessment",
        "href": "/signup",
        "featured": False,
    },
    "report": {
        "key": "report",
        "name": "Constraint Report",
        "price_usd": 499,
        "billing": "one_time",
        "tagline": "The board-ready operating document.",
        "note": "One report. Perpetual access.",
        "features": [
            "Full 36-metric report and confidence",
            "Costed constraint with printed assumptions",
            "90-day plan with owners and dates",
            "Board-pack PDF and share link",
            "Free re-score at 90 days",
        ],
        "cta": "Get the Constraint Report",
        "href": "/start",
        "featured": True,
        "proof": (
            "Comparable on-site diagnostics often start at $2,000+; "
            "Elipsis delivers the structured report layer in hours, "
            "not a week on site."
        ),
    },
    "facilitated": {
        "key": "facilitated",
        "name": "Facilitated Report",
        "price_usd": 1900,
        "billing": "one_time",
        "tagline": "The report, reviewed with you.",
        "note": "Report + review call + intros.",
        "features": [
            "Everything in the Constraint Report",
            "60–90 minute review with an operator",
            "Three curated implementer introductions",
            "Revised report within 5 business days",
        ],
        "cta": "Book a facilitated report",
        "href": "/contact",
        "featured": False,
    },
    "operator_monthly": {
        "key": "operator_monthly",
        "name": "Operator",
        "price_usd": 129,
        "billing": "monthly",
        "annual_price_usd": 999,
        "tagline": "Run the plan after the report.",
        "note": "Cancel before renewal.",
        "features": [
            "Action board with owners and dates",
            "Team seats and shared tracking",
            "Quarterly re-score cadence",
            "Exports and board packs",
        ],
        "cta": "Start Operator",
        "href": "/pro",
        "featured": False,
    },
    "operator_annual": {
        "key": "operator_annual",
        "name": "Operator (annual)",
        "price_usd": 999,
        "billing": "yearly",
        "tagline": "Two months free.",
        "note": "Billed once a year.",
        "features": [
            "Everything in Operator monthly",
            "Two months free",
            "Priority support",
        ],
        "cta": "Start Operator annual",
        "href": "/pro?billing=annual",
        "featured": False,
    },
    "partner": {
        "key": "partner",
        "name": "Partner",
        "price_usd": 249,
        "billing": "monthly",
        "tagline": "Deliver Elipsis to your clients.",
        "note": "Phase 3.",
        "features": [
            "Multi-client workspace",
            "White-label reports",
            "Priority introductions",
        ],
        "cta": "Talk to us",
        "href": "/contact",
        "featured": False,
    },
}

RETIRED: dict[str, dict] = {
    "full_assessment": {"name": "Unlock Full Assessment", "price_usd": 49,
                        "replaced_by": "report"},
    "premium_monthly": {"name": "Premium monthly", "price_usd": 29,
                        "replaced_by": "operator_monthly"},
    "premium_annual": {"name": "Premium annual", "price_usd": 380,
                       "replaced_by": "operator_annual"},
    "bidder_monthly": {"name": "Bidder monthly", "price_usd": 39,
                       "replaced_by": "partner"},
    "bidder_six_months": {"name": "Bidder six months", "price_usd": 119,
                          "replaced_by": "partner"},
    "bidder_yearly": {"name": "Bidder annual", "price_usd": 219,
                      "replaced_by": "partner"},
    "switch_topup": {"name": "Switch top-up", "price_usd": 24.50,
                     "replaced_by": None},
}


def get(sku: str) -> dict:
    return SKUS[sku]


def price(sku: str) -> int:
    return int(SKUS[sku]["price_usd"])


def amount_minor(sku: str) -> int:
    return int(round(SKUS[sku]["price_usd"] * 100))


def label(sku: str) -> str:
    return str(SKUS[sku]["name"])


def public_skus() -> list[dict]:
    """Order shown on marketing pages."""
    order = ("pulse", "report", "facilitated", "operator_monthly")
    return [SKUS[key] for key in order]
