"""Vercel serverless entrypoint for the Elipsis FastAPI app."""
import os
import sys
import traceback

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    from elipsis_api.main import app  # noqa: E402, F401
except Exception:  # pragma: no cover
    _err = traceback.format_exc()
    app = FastAPI()

    @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
    async def _boot_error(full_path: str = ""):
        return PlainTextResponse("Elipsis failed to import:\n\n" + _err, status_code=500)
