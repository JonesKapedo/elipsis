"""Elipsis API application factory.

Run with:
    uvicorn elipsis_api.main:app --reload --port 8001

On Vercel the app is deployed as a serverless function; the entrypoint is
api/index.py (exports `app` from this module).
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
from starlette.exceptions import HTTPException as StarletteHTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constants import BRAND_NAME, FRAMEWORK_NAME  # noqa: E402
from elipsis_api import services  # noqa: E402
from elipsis_api.config import BASE_DIR, DATABASE_URL  # noqa: E402
from elipsis_api.database import Base, SessionLocal, engine  # noqa: E402
from elipsis_api.routers import api, pages  # noqa: E402

_SEED_OK = False
_SEED_ERROR: str | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Create schema and seed once per cold start; never crash the process."""
    global _SEED_OK, _SEED_ERROR
    try:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            services.seed(db)
            _SEED_OK = True
            _SEED_ERROR = None
        finally:
            db.close()
        print(f"[elipsis] database ready: {DATABASE_URL.split('://', 1)[0]}", flush=True)
    except Exception as exc:  # noqa: BLE001
        _SEED_OK = False
        _SEED_ERROR = f"{exc.__class__.__name__}: {exc}"
        print(f"[elipsis] startup seed failed: {_SEED_ERROR}", flush=True)
        traceback.print_exc()
    yield


app = FastAPI(
    title=f"{BRAND_NAME} API",
    description=FRAMEWORK_NAME,
    version="0.2.1",
    lifespan=lifespan,
)

# API + page routes
app.include_router(api.router)
app.include_router(pages.router)

# CSS and other static assets (repo-root /static)
_static = Path(__file__).resolve().parent.parent / "static"
if _static.is_dir():
    app.mount("/static", StaticFiles(directory=str(_static)), name="static")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_request: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, (dict, list)):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


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
    # Avoid exposing internals in production-like environments.
    detail = "internal_error"
    if os.getenv("ELIPSIS_DEBUG") == "1" or os.getenv("VERCEL_ENV") == "preview":
        detail = f"{exc.__class__.__name__}: {exc}"
    return JSONResponse(status_code=500, content={"detail": detail})


def seed_status() -> dict:
    """Expose startup seed state for health checks."""
    return {"seed_ok": _SEED_OK, "seed_error": _SEED_ERROR}
