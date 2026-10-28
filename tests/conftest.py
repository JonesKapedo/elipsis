"""Shared fixtures: put the project root on the path so tests import the app."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Tests must never fall back to the developer database in .env. Set a fresh
# SQLite file before any test module imports config or database. Individual
# modules may still override ELIPSIS_DATABASE_URL with their own temp path.
os.environ.setdefault(
    "ELIPSIS_DATABASE_URL",
    f"sqlite:///{Path(tempfile.mkdtemp(prefix='elipsis-tests-')) / 'test.db'}",
)
