"""Elipsis API application factory.

Run with:
    uvicorn elipsis_api.main:app --reload --port 8001

On Vercel use zero-config FastAPI (root main.py or pyproject entrypoint).
Do not catch-all rewrite to /api/index — that turns every path into 404.
"""

import os
import sys
import time
import traceback
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constants import BRAND_NAME, FRAMEWORK_NAME  # noqa: E402
from elipsis_api import services  # noqa: E402
from elipsis_api import state as runtime_state  # noqa: E402
from elipsis_api.config import DATABASE_URL  # noqa: E402
from elipsis_api.database import Base, SessionLocal, engine  # noqa: E402
from elipsis_api.routers import api, pages

try:
    from elipsis_api.routers import auth_pages  # noqa: E402
except Exception as _exc:  # noqa: BLE001
    auth_pages = None
    print(f"[elipsis] auth_pages import failed: {_exc}", flush=True)

try:
    from elipsis_api.routers import report_routes  # noqa: E402
except Exception as _exc:  # noqa: BLE001
    report_routes = None
    print(f"[elipsis] report_routes import failed: {_exc}", flush=True)

try:
    from elipsis_api.routers import studio  # noqa: E402
except Exception as _exc:  # noqa: BLE001
    studio = None
    print(f"[elipsis] studio import failed: {_exc}", flush=True)

try:
    from elipsis_api.routers import marketplace  # noqa: E402
except Exception as _exc:  # noqa: BLE001
    marketplace = None
    print(f"[elipsis] marketplace import failed: {_exc}", flush=True)

try:
    from elipsis_api.routers import bidder  # noqa: E402
except Exception as _exc:  # noqa: BLE001
    bidder = None
    print(f"[elipsis] bidder import failed: {_exc}", flush=True)

try:
    from elipsis_api.routers import admin  # noqa: E402
except Exception as _exc:  # noqa: BLE001
    admin = None
    print(f"[elipsis] admin import failed: {_exc}", flush=True)

try:
    from elipsis_api.routers import organizations  # noqa: E402
except Exception as _exc:  # noqa: BLE001
    organizations = None
    print(f"[elipsis] organizations import failed: {_exc}", flush=True)

try:
    from elipsis_api.routers import files  # noqa: E402
except Exception as _exc:  # noqa: BLE001
    files = None
    print(f"[elipsis] files import failed: {_exc}", flush=True)

try:
    from elipsis_api.routers import messaging  # noqa: E402
except Exception as _exc:  # noqa: BLE001
    messaging = None
    print(f"[elipsis] messaging import failed: {_exc}", flush=True)

try:
    from elipsis_api.routers import analytics  # noqa: E402
except Exception as _exc:  # noqa: BLE001
    analytics = None
    print(f"[elipsis] analytics import failed: {_exc}", flush=True)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Same-origin CSRF guard plus conservative security headers."""

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
    CSRF_EXEMPT = {"/paystack/webhook"}

    async def dispatch(self, request: Request, call_next):
        request_id = (request.headers.get("x-request-id") or "")[:64]
        if not request_id or not all(ch.isalnum() or ch in "-_" for ch in request_id):
            request_id = uuid.uuid4().hex
        started = time.perf_counter()
        if request.method not in self.SAFE_METHODS and request.url.path not in self.CSRF_EXEMPT:
            fetch_site = request.headers.get("sec-fetch-site", "")
            if fetch_site == "cross-site":
                return JSONResponse(status_code=403, content={"detail": "csrf_rejected"})
            origin = request.headers.get("origin") or request.headers.get("referer")
            if origin:
                from urllib.parse import urlparse
                host = request.headers.get("host", "")
                parsed = urlparse(origin)
                allowed = {f"https://{host}", f"http://{host}"}
                allowed.update(
                    o.strip() for o in os.getenv("ELIPSIS_ALLOWED_ORIGINS", "").split(",")
                    if o.strip()
                )
                if f"{parsed.scheme}://{parsed.netloc}" not in allowed:
                    return JSONResponse(status_code=403, content={"detail": "csrf_rejected"})
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["Server-Timing"] = f"app;dur={(time.perf_counter() - started) * 1000:.1f}"
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        response.headers.setdefault(
            "Content-Security-Policy",
            "frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        response.headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")
        response.headers.setdefault("X-DNS-Prefetch-Control", "off")
        path = request.url.path
        private_prefix = (
            "/assessment", "/assessments", "/company", "/dashboard", "/settings",
            "/support", "/account", "/admin", "/api", "/actions", "/operations",
            "/inbox", "/letter", "/notifications", "/feedback", "/getting-started",
        )
        if path.startswith(private_prefix):
            response.headers.setdefault("X-Robots-Tag", "noindex, nofollow")
        content_type = response.headers.get("content-type", "")
        if path.startswith("/static/"):
            response.headers.setdefault("Cache-Control", "public, max-age=86400")
        elif "text/html" in content_type:
            response.headers.setdefault("Cache-Control", "no-store")
            response.headers.setdefault("Vary", "Cookie")
        if os.getenv("VERCEL") or os.getenv("ELIPSIS_ENV", "").lower() == "production":
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            services.seed(db)
            runtime_state.set_seed(True, None)
        finally:
            db.close()
        from elipsis_api import database as _dbmod
        scheme = getattr(_dbmod, "ACTIVE_DATABASE_URL", DATABASE_URL).split("://", 1)[0]
        print(f"[elipsis] database ready: {scheme}", flush=True)
    except Exception as exc:  # noqa: BLE001
        err = f"{exc.__class__.__name__}: {exc}"
        runtime_state.set_seed(False, err)
        print(f"[elipsis] startup seed failed: {err}", flush=True)
        traceback.print_exc()
    yield


app = FastAPI(
    title=f"{BRAND_NAME} API",
    description=FRAMEWORK_NAME,
    version="0.5.1",
    lifespan=lifespan,
)

_allowed_origins = [
    o.strip() for o in os.getenv("ELIPSIS_ALLOWED_ORIGINS", "").split(",") if o.strip()
]
if _allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    )
app.add_middleware(SecurityMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=600)

app.include_router(api.router)
if auth_pages is not None:
    app.include_router(auth_pages.router)
if report_routes is not None:
    app.include_router(report_routes.router)
if studio is not None:
    app.include_router(studio.router)

if marketplace is not None:
    app.include_router(marketplace.router, prefix="/api/v1")
    print("[elipsis] marketplace routes mounted", flush=True)
if bidder is not None:
    app.include_router(bidder.router, prefix="/api/v1")
    print("[elipsis] bidder routes mounted", flush=True)
if admin is not None:
    app.include_router(admin.router, prefix="/api/v1")
    print("[elipsis] admin routes mounted", flush=True)
if organizations is not None:
    app.include_router(organizations.router, prefix="/api/v1")
    print("[elipsis] organizations routes mounted", flush=True)

if files is not None:
    app.include_router(files.router, prefix="/api/v1")
    print("[elipsis] files routes mounted", flush=True)
if messaging is not None:
    app.include_router(messaging.router, prefix="/api/v1")
    print("[elipsis] messaging routes mounted", flush=True)
if analytics is not None:
    app.include_router(analytics.router, prefix="/api/v1")
    print("[elipsis] analytics routes mounted", flush=True)

try:
    from elipsis_api.routers import collect as _collect_mod  # noqa: E402
    app.include_router(_collect_mod.router)
    print("[elipsis] collect routes mounted", flush=True)
except Exception as _exc:  # noqa: BLE001
    print(f"[elipsis] collect not mounted: {_exc}", flush=True)

from elipsis_api.routers import company_room as _company_room  # noqa: E402
from elipsis_api.routers import growth as _growth  # noqa: E402
from elipsis_api.routers import operations_ui as _operations  # noqa: E402
from elipsis_api.routers import service as _service  # noqa: E402
from elipsis_api.routers import value as _value  # noqa: E402
from elipsis_api.routers import workspace as _workspace  # noqa: E402

app.include_router(_value.router)
app.include_router(_workspace.router)
app.include_router(_company_room.router)
app.include_router(_service.router)
app.include_router(_growth.router)
app.include_router(_operations.router)
app.include_router(_operations.api_router)
app.include_router(pages.router)

try:
    from elipsis_api.routers import marketplace_ui as _marketplace_ui  # noqa: E402
    app.include_router(_marketplace_ui.router)
    print("[elipsis] marketplace UI routes mounted", flush=True)
except Exception as _exc:  # noqa: BLE001
    print(f"[elipsis] marketplace UI not mounted: {_exc}", flush=True)

# company_ui is intentionally unmounted: the studio router owns /company.
_static = Path(__file__).resolve().parent.parent / "static"
if _static.is_dir():
    app.mount("/static", StaticFiles(directory=str(_static)), name="static")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_request: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, (dict, list)):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": "validation_error", "errors": exc.errors()},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    print(f"[elipsis] unhandled {exc.__class__.__name__} on {request.url.path}: {exc}",
          flush=True)
    traceback.print_exc()
    detail = "internal_error"
    if os.getenv("ELIPSIS_DEBUG") == "1" or os.getenv("VERCEL_ENV") == "preview":
        detail = f"{exc.__class__.__name__}: {exc}"
    return JSONResponse(status_code=500, content={"detail": detail})
