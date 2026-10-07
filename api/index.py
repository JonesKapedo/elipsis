"""Vercel serverless entrypoint for the Elipsis FastAPI app."""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from elipsis_api.main import app  # noqa: E402, F401
