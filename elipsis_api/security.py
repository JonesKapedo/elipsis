"""Password hashing and session tokens — schema-compatible with the stdlib layer.

Uses PBKDF2-HMAC-SHA256 in the same `salt$hash` format as `web/auth.py` so the
two transports share one `users` table and one `sessions` table.
"""

import hashlib
import hmac
import secrets

ITERATIONS = 120_000


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