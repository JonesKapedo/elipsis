"""Legacy /api entrypoint (optional).

Prefer root main.py or [tool.vercel] entrypoint = "elipsis_api.main:app".
Kept so older configs that pointed at /api still resolve to the same app.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from elipsis_api.main import app as app  # noqa: E402
