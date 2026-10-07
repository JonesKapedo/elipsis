"""Vercel serverless entrypoint for the Elipsis FastAPI app.

Vercel looks for an ASGI `app` under /api. Importing from elipsis_api.main
keeps a single source of truth for routes, lifespan, and static mounts.
"""
from elipsis_api.main import app  # noqa: F401
