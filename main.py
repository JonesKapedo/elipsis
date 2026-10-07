"""Root entrypoint so Vercel auto-detection finds a top-level FastAPI `app`.

The real application lives in elipsis_api.main; this module re-exports it.
Also declared in pyproject.toml as:

    [tool.vercel]
    entrypoint = "elipsis_api.main:app"
"""
from elipsis_api.main import app

__all__ = ["app"]
