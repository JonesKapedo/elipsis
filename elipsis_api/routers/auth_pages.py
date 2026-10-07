"""Sign-up and resilient login (mounted before pages so these win)."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from elipsis_api import auth_extra, services
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user, templates
from elipsis_api.routers.pages import _question_count, _set_session_cookie

router = APIRouter()


@router.get("/signup")
def signup_form(request: Request, user=Depends(get_current_user),
                db: Session = Depends(get_db)):
    if user is not None:
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(
        request, "signup.html",
        {"user": user, "error": None, "form": None,
         "total_questions": _question_count(db) or 63})


@router.post("/signup")
def signup(request: Request,
           name: str = Form(""),
           email: str = Form(...),
           password: str = Form(...),
           password2: str = Form(...),
           db: Session = Depends(get_db)):
    form = {"name": (name or "").strip(), "email": (email or "").strip()}
    if password != password2:
        return templates.TemplateResponse(
            request, "signup.html",
            {"user": None, "error": "Passwords do not match.",
             "form": form, "total_questions": _question_count(db) or 63},
            status_code=400)
    try:
        account = auth_extra.register_user(db, email, password, name=name)
    except ValueError as exc:
        return templates.TemplateResponse(
            request, "signup.html",
            {"user": None, "error": str(exc),
             "form": form, "total_questions": _question_count(db) or 63},
            status_code=400)
    except Exception as exc:  # noqa: BLE001
        print(f"[elipsis] signup failed: {exc}", flush=True)
        return templates.TemplateResponse(
            request, "signup.html",
            {"user": None, "error": "Could not create account. Please try again.",
             "form": form, "total_questions": _question_count(db) or 63},
            status_code=500)
    token = services.create_session(db, account.id)
    response = RedirectResponse("/start", status_code=303)
    _set_session_cookie(response, token)
    return response


@router.post("/login")
def login_resilient(request: Request, email: str = Form(...), password: str = Form(...),
                    db: Session = Depends(get_db)):
    account = auth_extra.authenticate_resilient(db, email, password)
    if account is None:
        return templates.TemplateResponse(
            request, "login.html",
            {"user": None,
             "error": "Invalid email or password. Create a free account if you are new.",
             "email": (email or "").strip().lower(),
             "total_questions": _question_count(db) or 63},
            status_code=401)
    token = services.create_session(db, account.id)
    response = RedirectResponse("/dashboard", status_code=303)
    _set_session_cookie(response, token)
    return response
