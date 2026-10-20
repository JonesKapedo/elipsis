"""Small in-process rate limiter for credential endpoints."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

_LOCK = threading.Lock()
_HITS: dict[str, deque[float]] = defaultdict(deque)


def client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def check(scope: str, key: str, limit: int = 10, window: int = 60) -> bool:
    now = time.monotonic()
    bucket_key = f"{scope}:{key}"
    with _LOCK:
        bucket = _HITS[bucket_key]
        while bucket and bucket[0] <= now - window:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True


def enforce(request: Request, scope: str, limit: int = 10, window: int = 60) -> None:
    if not check(scope, client_key(request), limit=limit, window=window):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Try again in a minute.",
            headers={"Retry-After": str(window)},
        )
