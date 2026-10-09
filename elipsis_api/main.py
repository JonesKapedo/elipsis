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
from starlette.exceptions import HTTPException as StarletteHTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constants import BRAND_NAME, FRAMEWORK_NAME  # noqa: E402
from elipsis_api import services  # noqa: E402
from elipsis_api.config import DATABASE_URL  # noqa: E402
from elipsis_api.database import Base, SessionLocal, engine  # noqa: E402
from elipsis_api import state as runtime_state  # noqa: E402

# Import routers defensively so a single broken module does not empty the app.
from elipsis_api.routers import api, pages
try:
    from elipsis_api.routers import collect as collect_routes
except Exception as _exc:
    collect_routes = None
    print(f"[elipsis] collect import failed: {_exc}", flush=True)  # noqa: E402

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
        print(f"[elipsis] database ready: {DATABASE_URL.split('://', 1)[0]}", flush=True)
    except Exception as exc:  # noqa: BLE001
        err = f"{exc.__class__.__name__}: {exc}"
        runtime_state.set_seed(False, err)
        print(f"[elipsis] startup seed failed: {err}", flush=True)
        traceback.print_exc()
    yield


app = FastAPI(
    title=f"{BRAND_NAME} API",
    description=FRAMEWORK_NAME,
    version="0.3.1",
    lifespan=lifespan,
)

app.include_router(api.router)
if auth_pages is not None:
    app.include_router(auth_pages.router)
if report_routes is not None:
    app.include_router(report_routes.router)
if studio is not None:
    app.include_router(studio.router)
if collect_routes is not None:
    app.include_router(collect_routes.router)
app.include_router(pages.router)

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
