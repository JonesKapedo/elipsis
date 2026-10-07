"""Elipsis API application factory.

Run with:
    uvicorn elipsis_api.main:app --reload --port 8001

On Vercel the app is deployed as a serverless function; the entrypoint is
api/index.py (exports `app` from this module).
"""

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constants import BRAND_NAME, FRAMEWORK_NAME  # noqa: E402
from elipsis_api import services  # noqa: E402
from elipsis_api.config import BASE_DIR, DATABASE_URL  # noqa: E402
from elipsis_api.database import Base, SessionLocal, engine  # noqa: E402
from elipsis_api.routers import api, pages  # noqa: E402


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Create the schema and seed the question bank once per cold start.

    Errors are logged rather than crashing the whole function so a bad
    database URL still surfaces a usable error page instead of a bare 500.
    """
    try:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            services.seed(db)
        finally:
            db.close()
        print(f"[elipsis] database: {DATABASE_URL}", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"[elipsis] startup seed failed: {exc!r}", flush=True)
    yield


app = FastAPI(title=f"{BRAND_NAME} API", description=FRAMEWORK_NAME,
              version="0.1.0", lifespan=lifespan)

# API routes
app.include_router(api.router)
app.include_router(pages.router)

# Serve CSS and other static assets (repo-root /static)
_static = Path(__file__).resolve().parent.parent / "static"
if _static.is_dir():
    app.mount("/static", StaticFiles(directory=str(_static)), name="static")
