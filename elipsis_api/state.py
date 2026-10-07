"""Process-local runtime flags (seed status, etc.)."""

SEED_OK = False
SEED_ERROR: str | None = None


def set_seed(ok: bool, error: str | None = None) -> None:
    global SEED_OK, SEED_ERROR
    SEED_OK = ok
    SEED_ERROR = error


def seed_status() -> dict:
    return {"seed_ok": SEED_OK, "seed_error": SEED_ERROR}
