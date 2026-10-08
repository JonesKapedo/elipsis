"""Root FastAPI entrypoint for Vercel zero-config detection.

Vercel looks for a top-level `app` (main.py / app.py) or the entrypoint in
pyproject.toml:

    [tool.vercel]
    entrypoint = "elipsis_api.main:app"

Do not add catch-all rewrites to /api/index in vercel.json — those rewrite the
request path so FastAPI only sees /api/index and every real route 404s.
"""
from elipsis_api.main import app

__all__ = ["app"]
