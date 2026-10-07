"""Vercel serverless entrypoint for the Elipsis FastAPI app.

Vercel looks for a top-level `app` in this file (or the entrypoint declared
in pyproject.toml under [tool.vercel]).
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from elipsis_api.main import app as app  # noqa: E402
