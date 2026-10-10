"""Elipsis API application factory.

Run with:
    uvicorn elipsis_api.main:app --reload --port 8001

On Vercel use zero-config FastAPI (root main.py or pyproject entrypoint).
Do not catch-all rewrite to /api/index — that turns every path into 404.
"""

import os
import sys
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constants import BRAND_NAME, FRAMEWORK_NAME  # noqa: E402
from elipsis_api import services  # noqa: E402
from elipsis_api.config import DATABASE_URL  # noqa: E402
from elipsis_api.database import Base, SessionLocal, engine  # noqa: E402
from elipsis_api import state as runtime_state  # noqa: E402

# Import routers defensively so a single broken module does not empty the app.
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

# Import marketplace routers
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

# Import enhanced feature routers
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


class AdminFullAccessMiddleware(BaseHTTPMiddleware):
    """Middleware to grant admins full access to all routes."""
    
    async def dispatch(self, request: Request, call_next):
        # Check if user is admin (simplified - you'd get this from session/token)
        # For now, we'll handle this in the route dependencies
        response = await call_next(request)
        return response


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Create schema and seed once per cold start; never crash the process."""
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
    version="0.5.0",  # Updated version with all enhancements
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add admin full access middleware
app.add_middleware(AdminFullAccessMiddleware)

# Core routers
app.include_router(api.router)
if auth_pages is not None:
    app.include_router(auth_pages.router)
if report_routes is not None:
    app.include_router(report_routes.router)
if studio is not None:
    app.include_router(studio.router)

# Marketplace routers
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

# Enhanced feature routers
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
    
app.include_router(pages.router)

# Marketplace + admin request desk (server-rendered professional shell)
try:
    from elipsis_api.routers import marketplace_ui as _marketplace_ui  # noqa: E402
    app.include_router(_marketplace_ui.router)
    print("[elipsis] marketplace UI routes mounted", flush=True)
except Exception as _exc:  # noqa: BLE001
    print(f"[elipsis] marketplace UI not mounted: {_exc}", flush=True)

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
    """Never leak a bare 500 with no body on serverless."""
    print(f"[elipsis] unhandled {exc.__class__.__name__} on {request.url.path}: {exc}",
          flush=True)
    traceback.print_exc()
    detail = "internal_error"
    if os.getenv("ELIPSIS_DEBUG") == "1" or os.getenv("VERCEL_ENV") == "preview":
        detail = f"{exc.__class__.__name__}: {exc}"
    return JSONResponse(status_code=500, content={"detail": detail})
