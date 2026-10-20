"""Sign-up and resilient login (mounted before pages so these win)."""

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from elipsis_api import auth_extra, models, ratelimit, security, services
from elipsis_api.config import SESSION_COOKIE
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user, safe_next, templates
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
async def signup(request: Request,
           name: str = Form(""),
           email: str = Form(...),
           password: str = Form(...),
           password2: str = Form(...),
           user_type: str = Form("client"),
           db: Session = Depends(get_db)):
    ratelimit.enforce(request, "signup", limit=5, window=60)
    form = {"name": (name or "").strip(), "email": (email or "").strip(),
            "user_type": (user_type or "client").strip()}
    if password != password2:
        return templates.TemplateResponse(
            request, "signup.html",
            {"user": None, "error": "Passwords do not match.",
             "form": form, "total_questions": _question_count(db) or 63},
            status_code=400)
    try:
        account = auth_extra.register_user(db, email, password, name=name, user_type=form["user_type"])
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
    from elipsis_api.services_email import is_email_configured, send_email
    if is_email_configured():
        account.email_verified = False
        account.verification_token = secrets.token_urlsafe(32)
        db.commit()
        base = str(request.base_url).rstrip("/")
        await send_email(
            account.email, "Verify your Elipsis email",
            f'<p>Confirm your email: <a href="{base}/verify-email?token={account.verification_token}">Verify email</a></p>',
        )
    token = services.create_session(db, account.id)
    dest = "/marketplace" if form.get("user_type") == "bidder" else "/company"
    response = RedirectResponse(dest, status_code=303)
    _set_session_cookie(response, token)
    return response


@router.post("/login")
def login_resilient(request: Request, email: str = Form(...), password: str = Form(...),
                    next: str = Form(""),
                    db: Session = Depends(get_db)):
    ratelimit.enforce(request, "login", limit=10, window=60)
    account = auth_extra.authenticate_resilient(db, email, password)
    nxt = safe_next(next) or ""
    if account is None:
        return templates.TemplateResponse(
            request, "login.html",
            {"user": None,
             "error": "Invalid email or password. Create a free account if you are new.",
             "email": (email or "").strip().lower(),
             "next": nxt,
             "total_questions": _question_count(db) or 63},
            status_code=401)
    old = request.cookies.get(SESSION_COOKIE)
    if old:
        services.delete_session(db, old)
    token = services.create_session(db, account.id)
    response = RedirectResponse(nxt or "/dashboard", status_code=303)
    _set_session_cookie(response, token)
    return response


@router.get("/forgot-password")
def forgot_form(request: Request, user=Depends(get_current_user)):
    if user is not None:
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(
        request, "forgot_password.html",
        {"user": None, "sent": False, "error": None})


@router.post("/forgot-password")
async def forgot_password(request: Request, email: str = Form(...),
                          db: Session = Depends(get_db)):
    ratelimit.enforce(request, "forgot-password", limit=5, window=300)
    address = (email or "").strip().lower()
    user = db.scalar(select(models.User).where(models.User.email == address))
    if user is not None:
        user.reset_token = secrets.token_urlsafe(32)
        user.reset_expires_at = (
            datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1)
        ).isoformat(timespec="seconds")
        db.commit()
        from elipsis_api.services_email import is_email_configured, send_email
        if is_email_configured():
            base = str(request.base_url).rstrip("/")
            await send_email(
                user.email, "Reset your Elipsis password",
                f'<p>Reset your password: <a href="{base}/reset-password?token={user.reset_token}">Choose a new password</a>. The link expires in one hour.</p>',
            )
        else:
            print(f"[elipsis] password reset requested for {user.email} but no email "
                  "transport is configured", flush=True)
    return templates.TemplateResponse(
        request, "forgot_password.html",
        {"user": None, "sent": True, "error": None})


@router.get("/reset-password")
def reset_form(request: Request, token: str = "", db: Session = Depends(get_db)):
    user = _user_for_reset(db, token)
    if user is None:
        return templates.TemplateResponse(
            request, "reset_password.html",
            {"user": None, "token": "", "error": "This reset link is invalid or expired."},
            status_code=400)
    return templates.TemplateResponse(
        request, "reset_password.html",
        {"user": None, "token": token, "error": None})


@router.post("/reset-password")
def reset_password(request: Request, token: str = Form(...),
                   password: str = Form(...), password2: str = Form(...),
                   db: Session = Depends(get_db)):
    ratelimit.enforce(request, "reset-password", limit=5, window=300)
    user = _user_for_reset(db, token)
    if user is None:
        return templates.TemplateResponse(
            request, "reset_password.html",
            {"user": None, "token": "", "error": "This reset link is invalid or expired."},
            status_code=400)
    if password != password2:
        return templates.TemplateResponse(
            request, "reset_password.html",
            {"user": None, "token": token, "error": "Passwords do not match."},
            status_code=400)
    if len(password or "") < 8:
        return templates.TemplateResponse(
            request, "reset_password.html",
            {"user": None, "token": token,
             "error": "Password must be at least 8 characters."},
            status_code=400)
    user.password_hash = security.hash_password(password)
    user.reset_token = None
    user.reset_expires_at = None
    db.commit()
    from elipsis_api import session_auth
    session_auth.revoke_user_sessions(db, user.id)
    return RedirectResponse("/login?reset=1", status_code=303)


@router.get("/verify-email")
def verify_email(token: str = "", db: Session = Depends(get_db)):
    user = db.scalar(select(models.User).where(models.User.verification_token == token)) if token else None
    if user is None:
        return RedirectResponse("/login?verify=invalid", status_code=303)
    user.email_verified = True
    user.verification_token = None
    db.commit()
    return RedirectResponse("/dashboard?verified=1", status_code=303)


def _user_for_reset(db: Session, token: str):
    if not token:
        return None
    user = db.scalar(select(models.User).where(models.User.reset_token == token))
    if user is None or not user.reset_expires_at:
        return None
    try:
        expires = datetime.fromisoformat(user.reset_expires_at)
    except ValueError:
        return None
    if expires < datetime.now(UTC).replace(tzinfo=None):
        return None
    return user
