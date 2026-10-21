"""ICP definition and defensible public reference points.

Nothing in this module is presented as an Elipsis customer result. Public
figures are labelled with their publisher and URL; cohort figures are computed
from completed Elipsis assessments and are suppressed below a minimum sample.
"""

from __future__ import annotations

from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

ICP_CODE = "logistics"
ICP_NAME = "Logistics and field-operations companies"
ICP_LABEL = "Logistics operators (10–1,000 staff)"
ICP_DESCRIPTION = (
    "Freight forwarders, transport operators, warehousing, distribution, and "
    "field-service businesses — from single-site operators to multi-country groups."
)
ICP_WHY = (
    "Operating friction compounds across every handoff, asset, and invoice. "
    "The first reference market was Kenya; the framework is not country specific."
)

SOURCES = [
    dict(
        label="Registered logistics companies in Kenya",
        value="14,479",
        detail="NACE 52; 55% employ 10–49 people and 58% report USD 100K–1M revenue.",
        publisher="InfobelPRO / Business Registration Service",
        year="2026",
        url="https://www.infobelpro.com/companies/kenya/logistics",
    ),
    dict(
        label="Kenyan firms that automated a process in the last 12 months",
        value="78%",
        detail="CEO survey; transport & storage was 3% of respondents.",
        publisher="Central Bank of Kenya",
        year="2025",
        url="https://www.centralbank.go.ke/uploads/market_perception_surveys/2137496720_CEOs%20Survey,%20September%202025.pdf",
    ),
    dict(
        label="MSMEs in Kenya",
        value="7.41 million",
        detail="1.56M licensed; MSMEs are ~98% of businesses and ~33.8% of GDP.",
        publisher="Micro and Small Enterprises Authority / KNBS",
        year="2025",
        url="https://sdgs.un.org/sites/default/files/2025-10/KENYA%20MSEA%20PRESENTATION%20%20DEQING%20PRC.pdf",
    ),
]

REFERENCE_POINTS = [
    dict(label="Typical firm size", value="10–49 staff",
         note="55% of registered logistics companies.",
         source="InfobelPRO / BRS (2026)"),
    dict(label="Typical revenue band", value="USD 100K–1M",
         note="58% of registered logistics companies.",
         source="InfobelPRO / BRS (2026)"),
    dict(label="Automation activity", value="78% of Kenyan firms",
         note="Any process automated in the previous 12 months.",
         source="CBK CEO Survey (Sep 2025)"),
]

METHOD_NOTE = (
    "Financial figures are management estimates from labour exposure and "
    "process-drag severity, capped as a share of the annual labour line. They "
    "are not audited savings. Public reference points describe the market, not "
    "Elipsis customer outcomes. Peer medians are shown only when at least five "
    "comparable completed assessments exist."
)

MIN_COHORT = 5


def size_band(employee_count: int | None) -> str | None:
    if not employee_count:
        return None
    if employee_count < 50:
        return "10–49 staff"
    if employee_count < 200:
        return "50–199 staff"
    return "200+ staff"


def cohort_benchmark(db: Session, organization, score: float | None = None) -> dict | None:
    """Median readiness for completed peers, preferring industry + size band."""
    from elipsis_api import models

    if organization is None:
        return None
    industry = (organization.industry or "").strip()
    if not industry:
        return None
    band = size_band(organization.employee_count)
    rows = list(db.scalars(select(models.Assessment).where(
        models.Assessment.status == "completed",
        models.Assessment.readiness_index.is_not(None),
    )))
    industry_values = []
    band_values = []
    for row in rows:
        org = db.get(models.Organization, row.organization_id)
        if not org or (org.industry or "").strip().lower() != industry.lower():
            continue
        value = float(row.readiness_index)
        industry_values.append(value)
        if band and size_band(org.employee_count) == band:
            band_values.append(value)
    values = band_values if len(band_values) >= MIN_COHORT else industry_values
    scope = "industry_size" if values is band_values and band else "industry"
    if len(values) < MIN_COHORT:
        return dict(available=False, sample=len(values), minimum=MIN_COHORT,
                    industry=industry, band=band)
    percentile = None
    if score is not None:
        below = sum(1 for value in values if value <= float(score))
        percentile = round(100 * below / len(values))
    return dict(available=True, sample=len(values), industry=industry,
                band=band if scope == "industry_size" else None,
                scope=scope, median=round(median(values), 1),
                best=round(max(values), 1), lowest=round(min(values), 1),
                percentile=percentile)
