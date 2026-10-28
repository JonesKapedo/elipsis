#!/usr/bin/env python3
"""Post-deploy smoke test for Elipsis.

Usage:
    ELIPSIS_SMOKE_BASE_URL=https://app.example.com \
        python scripts/smoke.py

Optional authenticated checks:
    ELIPSIS_SMOKE_COOKIE="elipsis_session=..." python scripts/smoke.py
"""
from __future__ import annotations

import os
import sys

import httpx

BASE_URL = (os.getenv("ELIPSIS_SMOKE_BASE_URL") or "http://127.0.0.1:8001").rstrip("/")
COOKIE = os.getenv("ELIPSIS_SMOKE_COOKIE", "").strip()

PUBLIC_CHECKS = [
    ("/api/v1/health", "Elipsis"),
    ("/", "Elipsis"),
    ("/pricing", "Elipsis"),
    ("/login", "Elipsis"),
    ("/robots.txt", "User-agent"),
    ("/sitemap.xml", "<urlset"),
]

AUTH_CHECKS = [
    ("/dashboard", "Elipsis"),
    ("/marketplace", "Marketplace"),
]


def _failures(client: httpx.Client, checks: list[tuple[str, str]]) -> list[str]:
    failures: list[str] = []
    for path, needle in checks:
        try:
            response = client.get(f"{BASE_URL}{path}")
        except httpx.HTTPError as exc:
            failures.append(f"{path}: request failed ({exc})")
            continue
        if response.status_code != 200:
            failures.append(f"{path}: HTTP {response.status_code}")
            continue
        if needle and needle not in response.text:
            failures.append(f"{path}: missing expected content {needle!r}")
        else:
            print(f"ok   {path}")
    return failures


def main() -> int:
    headers = {"User-Agent": "elipsis-smoke/1.0"}
    if COOKIE:
        headers["Cookie"] = COOKIE
    failures: list[str] = []
    with httpx.Client(timeout=20, follow_redirects=True, headers=headers) as client:
        failures.extend(_failures(client, PUBLIC_CHECKS))
        if COOKIE:
            failures.extend(_failures(client, AUTH_CHECKS))
        health = client.get(f"{BASE_URL}/api/v1/health")
        if health.status_code == 200:
            payload = health.json()
            if payload.get("status") != "ok":
                failures.append(f"/api/v1/health: status={payload.get('status')!r}")
    if failures:
        print("\nSmoke test FAILED:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    print("\nSmoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
