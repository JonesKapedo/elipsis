"""Server-rendered pages (Jinja2) — the human interface."""

import os

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from elipsis_api import models, schemas, services
from elipsis_api.config import SESSION_COOKIE
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user, login_redirect, templates
from elipsis_api.sample import SAMPLE_ORG, sample_result

router = APIRouter()

_SECURE_COOKIE = os.getenv("VERCEL") == "1" or os.getenv("ELIPSIS_SECURE_COOKIE") == "1"
_COOKIE_MAX_AGE = 60 * 60 * 24 * 14


def _not_found(request, user):
    return templates.TemplateResponse(request, "404.html", {"user": user},
                                      status_code=404)


def _question_count(db: Session) -> int:
    try:
        bank = services.get_bank(db)
        if bank is None:
            return 0
        return int(db.scalar(select(func.count()).select_from(models.Question).where(
            models.Question.questionnaire_id == bank.id)) or 0)
    except Exception:  # noqa: BLE001
        return 0


def _set_session_cookie(response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE, token, httponly=True, samesite="lax",
        secure=_SECURE_COOKIE, max_age=_COOKIE_MAX_AGE,
    )
