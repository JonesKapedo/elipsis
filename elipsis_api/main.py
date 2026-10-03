"""Elipsis API application factory.

Run with:
    .venv-1/bin/uvicorn elipsis_api.main:app --reload --port 8001
or:
    python3 run_api.py
"""

import os
import sys

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constants import BRAND_NAME, FRAMEWORK_NAME  # noqa: E402
from elipsis_api import services  # noqa: E402
from elipsis_api.config import BASE_DIR, DATABASE_URL  # noqa: E402
from elipsis_api.database import Base, SessionLocal, engine  # noqa: E402
from elipsis_api.routers import api, pages  # noqa: E402

app = FastAPI(title=f"{BRAND_NAME} API", description=FRAMEWORK_NAME, version="0.1.0")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        services.seed(db)
    finally:
        db.close()
    print(f"[elipsis] database: {DATABASE_URL}", flush=True)


app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.include_router(api.router)
app.include_router(pages.router)