"""Password hashing and signed session tokens.

Passwords use PBKDF2-HMAC-SHA256 in ``salt$hash`` form.

Sessions are **HMAC-signed cookies** embedding ``user_id`` and expiry so they
remain valid across Vercel serverless instances. Relying only on rows in the
``sessions`` table fails when the deployment uses ephemeral SQLite under
``/tmp`` (each instance has its own database).
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time

ITERATIONS = 120_000
SESSION_MAX_AGE = 60 * 60 * 24 * 14  # 14 days


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERATIONS)
    return f"{salt}${digest.hex()}"


def verify_password(password, stored):
    try:
        salt, _ = stored.split("$", 1)
    except (AttributeError, ValueError):
        return False
    return hmac.compare_digest(hash_password(password, salt), stored)


def new_token():
    return secrets.token_urlsafe(32)


def _session_secret() -> str:
    secret = (
        os.getenv("ELIPSIS_SECRET_KEY")
        or os.getenv("TURBINEZ_SECRET_KEY")
        or os.getenv("SECRET_KEY")
        or ""
    ).strip()
    if not secret:
        # Deterministic fallback so all Vercel instances share the same key when
        # the operator has not set ELIPSIS_SECRET_KEY yet. Override in production.
        secret = "elipsis-dev-session-key-change-me"
    return secret


def sign_session(user_id: int, max_age: int = SESSION_MAX_AGE) -> str:
    """Return a signed cookie value: ``user_id.expiry.signature``."""
    exp = int(time.time()) + int(max_age)
    payload = f"{int(user_id)}.{exp}"
    sig = hmac.new(
        _session_secret().encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:40]
    return f"{payload}.{sig}"


def verify_signed_session(token: str | None) -> int | None:
    """Return user_id if the signed cookie is valid and not expired."""
    if not token or token.count(".") != 2:
        return None
    try:
        user_id_s, exp_s, sig = token.split(".", 2)
        payload = f"{user_id_s}.{exp_s}"
        expected = hmac.new(
            _session_secret().encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()[:40]
        if not hmac.compare_digest(expected, sig):
            return None
        if int(exp_s) < int(time.time()):
            return None
        return int(user_id_s)
    except (TypeError, ValueError):
        return None
