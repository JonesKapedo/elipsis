"""Shared dependencies: Jinja templates, current-user lookup, login redirect."""

from fastapi import Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from constants import (
    BRAND_NAME,
    BRAND_SHORT,
    BRAND_MARK,
    BRAND_TAGLINE,
    ASSESSMENT_NAME,
    CONFIDENCE_NAME,
    CURRENCY,
    FRAMEWORK_NAME,
    INDEX_NAME,
    INDEX_SHORT,
    MATURITY_ANSWER_HINTS,
    MATURITY_ANSWER_LABELS,
    ANSWER_SCALE,
    PILLAR_ICONS,
    SUBDOMAIN_ICONS,
    METRIC_ICONS,
    PILLAR_PLAIN,
    METRIC_KINDS,
    METRIC_LABELS,
    METRIC_READINGS,
    PILLAR_LABELS,
    PILLAR_OBJECTIVES,
    PILLAR_WEIGHTS,
    PILLARS,
    PHASES,
    PHASE_LABELS,
    QUESTIONNAIRE_CODE,
    QUESTIONNAIRE_NAME,
    REPORT_HEADER,
    SUBDOMAIN_LABELS,
    SUBDOMAIN_MEASURES,
    SUBDOMAIN_PILLAR,
    EVIDENCE_LABELS,
)
from elipsis_api import services
from elipsis_api.config import SESSION_COOKIE, TEMPLATES_DIR
from elipsis_api.database import get_db

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals.update(
    BRAND_NAME=BRAND_NAME, BRAND_SHORT=BRAND_SHORT, BRAND_MARK=BRAND_MARK,
    BRAND_TAGLINE=BRAND_TAGLINE, ASSESSMENT_NAME=ASSESSMENT_NAME,
    FRAMEWORK_NAME=FRAMEWORK_NAME, INDEX_NAME=INDEX_NAME, INDEX_SHORT=INDEX_SHORT,
    CONFIDENCE_NAME=CONFIDENCE_NAME, CURRENCY=CURRENCY,
    PILLARS=PILLARS,
    PILLAR_LABELS=PILLAR_LABELS, PILLAR_OBJECTIVES=PILLAR_OBJECTIVES,
    PILLAR_WEIGHTS=PILLAR_WEIGHTS,
    SUBDOMAIN_LABELS=SUBDOMAIN_LABELS, SUBDOMAIN_MEASURES=SUBDOMAIN_MEASURES,
    SUBDOMAIN_PILLAR=SUBDOMAIN_PILLAR,
    METRIC_LABELS=METRIC_LABELS, METRIC_KINDS=METRIC_KINDS,
    METRIC_READINGS=METRIC_READINGS,
    PHASES=PHASES, PHASE_LABELS=PHASE_LABELS,
    QUESTIONNAIRE_CODE=QUESTIONNAIRE_CODE, QUESTIONNAIRE_NAME=QUESTIONNAIRE_NAME,
    REPORT_HEADER=REPORT_HEADER,
    EVIDENCE_LABELS=EVIDENCE_LABELS,
    MATURITY_ANSWER_LABELS=MATURITY_ANSWER_LABELS,
    ANSWER_SCALE=ANSWER_SCALE,
    PILLAR_ICONS=PILLAR_ICONS, SUBDOMAIN_ICONS=SUBDOMAIN_ICONS,
    METRIC_ICONS=METRIC_ICONS, PILLAR_PLAIN=PILLAR_PLAIN,
    MATURITY_ANSWER_HINTS=MATURITY_ANSWER_HINTS,
)


def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Optional authentication — returns the User or None."""
    return services.user_for_token(db, request.cookies.get(SESSION_COOKIE))


def login_redirect():
    return RedirectResponse("/login", status_code=303)


def money(value):
    try:
        return f"{CURRENCY} {float(value):,.0f}"
    except (TypeError, ValueError):
        return f"{CURRENCY} 0"


templates.env.filters["money"] = money