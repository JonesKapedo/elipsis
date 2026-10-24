"""Paystack adapter.

Replace PAYSTACK_SECRET_KEY and PAYSTACK_PUBLIC_KEY in the environment.
While the secret is the dummy value, checkout stays inside Elipsis and marks
the payment successful without calling Paystack. A real secret posts to
https://api.paystack.co/transaction/initialize and verifies with
GET /transaction/verify/{reference}.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import urllib.error
import urllib.request

DUMMY_SECRET = "sk_test_dummy_replace_me"
DUMMY_PUBLIC = "pk_test_dummy_replace_me"

SECRET = os.getenv("PAYSTACK_SECRET_KEY", DUMMY_SECRET)
PUBLIC = os.getenv("PAYSTACK_PUBLIC_KEY", DUMMY_PUBLIC)


def is_production() -> bool:
    return bool(os.getenv("VERCEL")) or os.getenv("ELIPSIS_ENV", "").lower() == "production"


def is_dummy() -> bool:
    return not SECRET or SECRET == DUMMY_SECRET or os.getenv("PAYSTACK_MODE") == "dummy"


def ensure_configured() -> None:
    """Production must never accept the in-app dummy checkout."""
    if is_production() and (is_dummy() or not PUBLIC or PUBLIC == DUMMY_PUBLIC):
        raise RuntimeError(
            "PAYSTACK_SECRET_KEY and PAYSTACK_PUBLIC_KEY must be real in production; "
            "dummy checkout is disabled."
        )


def new_reference(prefix: str = "ELP") -> str:
    return f"{prefix}_{secrets.token_hex(8)}"


def initialize(email: str, amount_minor: int, reference: str, callback_url: str,
               metadata: dict | None = None, currency: str = "USD",
               plan_code: str | None = None) -> dict:
    """Initialize a checkout. Amount is already in the currency subunit (cents)."""
    ensure_configured()
    payload = {
        "email": email,
        "amount": int(amount_minor),
        "currency": currency.upper(),
        "reference": reference,
        "callback_url": callback_url,
        "metadata": metadata or {},
    }
    if plan_code:
        payload["plan"] = plan_code
    if is_dummy():
        return {
            "authorization_url": f"/pay/dummy/{reference}",
            "reference": reference,
            "access_code": "dummy",
            "dummy": True,
            "public_key": PUBLIC,
        }
    req = urllib.request.Request(
        "https://api.paystack.co/transaction/initialize",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {SECRET}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"Paystack initialize failed: {detail}") from exc
    data = body.get("data") or {}
    return {
        "authorization_url": data.get("authorization_url"),
        "reference": data.get("reference") or reference,
        "access_code": data.get("access_code"),
        "dummy": False,
        "public_key": PUBLIC,
    }


def verify(reference: str) -> dict:
    ensure_configured()
    if is_dummy():
        return {"status": "success", "reference": reference, "dummy": True}
    req = urllib.request.Request(
        f"https://api.paystack.co/transaction/verify/{reference}",
        headers={"Authorization": f"Bearer {SECRET}"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = json.loads(resp.read().decode())
    data = body.get("data") or {}
    return {
        "status": data.get("status") or "failed",
        "reference": reference,
        "dummy": False,
        "amount": data.get("amount"),
        "currency": data.get("currency"),
    }


def verify_webhook(payload: bytes, signature: str | None) -> bool:
    """Validate Paystack's x-paystack-signature HMAC before trusting an event."""
    if not signature or not SECRET:
        return False
    expected = hmac.new(SECRET.encode(), payload, hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected, signature)
