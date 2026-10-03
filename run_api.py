"""Launcher for the Elipsis FastAPI platform (primary interface).

    python3 run_api.py            ->  http://127.0.0.1:8001
    python3 run_api.py --reload   ->  auto-reload during development

Requires the FastAPI virtualenv (the FastAPI stack now lives in .venv), e.g.:
    /path/to/.venv-1/bin/python run_api.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    import uvicorn

    from elipsis_api.config import HOST, PORT  # noqa: F401

    reload = "--reload" in sys.argv
    uvicorn.run("elipsis_api.main:app", host=HOST, port=PORT, reload=reload)


if __name__ == "__main__":
    main()