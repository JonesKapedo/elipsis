"""Supabase Auth REST client for server-side credential verification."""

from __future__ import annotations

import os
from typing import Any

import httpx


class SupabaseAuthError(RuntimeError):
    """Base class for Supabase Auth failures safe to map to HTTP responses."""


class SupabaseConfigurationError(SupabaseAuthError):
    """Supabase Auth is not configured or the server key is rejected."""


class SupabaseUnavailable(SupabaseAuthError):
    """Supabase Auth could not be reached or returned a transient failure."""


class InvalidCredentials(SupabaseAuthError):
    """The email/password pair was rejected."""


class EmailNotConfirmed(SupabaseAuthError):
    """The Supabase user has not confirmed their email address."""


class AccountExists(SupabaseAuthError):
    """A Supabase user already exists for this email address."""


class UserNotFound(SupabaseAuthError):
    """The requested Supabase user does not exist."""


def _settings() -> tuple[str, str, str]:
    return (
        (os.getenv("SUPABASE_URL") or "").strip().rstrip("/"),
        (os.getenv("SUPABASE_ANON_KEY") or "").strip(),
        (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip(),
    )


def is_configured() -> bool:
    url, anon_key, service_key = _settings()
    return bool(url and anon_key and service_key)


def require_configured() -> None:
    if not is_configured():
        raise SupabaseConfigurationError(
            "Sign-in is not configured. Set SUPABASE_URL, SUPABASE_ANON_KEY, "
            "and SUPABASE_SERVICE_ROLE_KEY."
        )


def _timeout() -> float:
    try:
        return float(os.getenv("SUPABASE_AUTH_TIMEOUT", "10"))
    except ValueError:
        return 10.0


def _request(
    method: str,
    path: str,
    key: str,
    *,
    json_body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> httpx.Response:
    url, _, _ = _settings()
    if not url or not key:
        raise SupabaseConfigurationError("Supabase Auth is not configured.")
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }
    try:
        with httpx.Client(timeout=_timeout()) as client:
            return client.request(
                method,
                f"{url}{path}",
                headers=headers,
                json=json_body,
                params=params,
            )
    except httpx.HTTPError as exc:
        raise SupabaseUnavailable("Authentication service is unavailable.") from exc


def _payload(response: httpx.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _code(response: httpx.Response) -> str:
    data = _payload(response)
    return str(data.get("error_code") or data.get("code") or "").lower()


def _message(response: httpx.Response) -> str:
    data = _payload(response)
    return str(
        data.get("msg")
        or data.get("message")
        or data.get("error_description")
        or ""
    ).lower()


def _is_bad_key(response: httpx.Response) -> bool:
    code = _code(response)
    message = _message(response)
    return response.status_code in {401, 403} and (
        code in {"invalid_api_key", "bad_jwt", "no_authorization"}
        or "api key" in message
        or "jwt" in message
    )


def _raise_admin_error(response: httpx.Response) -> None:
    if _is_bad_key(response):
        raise SupabaseConfigurationError("Supabase server credentials were rejected.")
    if response.status_code == 429 or response.status_code >= 500:
        raise SupabaseUnavailable("Authentication service is temporarily unavailable.")
    raise SupabaseAuthError("Supabase Auth request failed.")


def sign_in(email: str, password: str) -> dict[str, Any]:
    _, anon_key, _ = _settings()
    response = _request(
        "POST",
        "/auth/v1/token",
        anon_key,
        json_body={"email": email, "password": password},
        params={"grant_type": "password"},
    )
    if response.status_code == 200:
        data = _payload(response)
        user = data.get("user")
        if not isinstance(user, dict) or not user.get("id"):
            raise SupabaseAuthError("Supabase Auth returned no user.")
        return data

    code = _code(response)
    if _is_bad_key(response):
        raise SupabaseConfigurationError("Supabase anon key was rejected.")
    if code == "email_not_confirmed":
        raise EmailNotConfirmed("Confirm your email before signing in.")
    if code in {"invalid_credentials", "invalid_grant"} or response.status_code in {400, 401}:
        raise InvalidCredentials("Invalid email or password.")
    if response.status_code == 429 or response.status_code >= 500:
        raise SupabaseUnavailable("Authentication service is temporarily unavailable.")
    raise SupabaseAuthError("Sign-in failed.")


def admin_create_user(
    email: str,
    password: str,
    *,
    name: str | None = None,
    user_type: str = "client",
) -> dict[str, Any]:
    _, _, service_key = _settings()
    metadata: dict[str, Any] = {"user_type": user_type}
    if name:
        metadata["name"] = name
    response = _request(
        "POST",
        "/auth/v1/admin/users",
        service_key,
        json_body={
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": metadata,
        },
    )
    if response.status_code in {200, 201}:
        data = _payload(response)
        if not data.get("id"):
            raise SupabaseAuthError("Supabase Auth returned no user id.")
        return data

    code = _code(response)
    message = _message(response)
    if (
        code in {"email_exists", "user_already_exists"}
        or "already registered" in message
        or "already exists" in message
    ):
        raise AccountExists("An account with this email already exists.")
    _raise_admin_error(response)
    return {}


def admin_update_user(user_id: str, **fields: Any) -> dict[str, Any]:
    _, _, service_key = _settings()
    response = _request(
        "PUT",
        f"/auth/v1/admin/users/{user_id}",
        service_key,
        json_body=fields,
    )
    if response.status_code == 200:
        return _payload(response)
    if response.status_code == 404:
        raise UserNotFound("Supabase user not found.")
    _raise_admin_error(response)
    return {}


def admin_delete_user(user_id: str) -> None:
    _, _, service_key = _settings()
    response = _request(
        "DELETE",
        f"/auth/v1/admin/users/{user_id}",
        service_key,
    )
    if response.status_code in {200, 204, 404}:
        return
    _raise_admin_error(response)


def _users_from_response(response: httpx.Response) -> list[dict[str, Any]]:
    data = _payload(response)
    users = data.get("users")
    if isinstance(users, list):
        return [item for item in users if isinstance(item, dict)]
    return []


def admin_find_user_by_email(email: str) -> dict[str, Any] | None:
    _, _, service_key = _settings()
    wanted = (email or "").strip().lower()
    if not wanted:
        return None
    page = 1
    for _ in range(20):
        response = _request(
            "GET",
            "/auth/v1/admin/users",
            service_key,
            params={"page": page, "per_page": 200},
        )
        if response.status_code != 200:
            _raise_admin_error(response)
            return None
        users = _users_from_response(response)
        for user in users:
            if str(user.get("email") or "").strip().lower() == wanted:
                return user
        payload = _payload(response)
        next_page = payload.get("nextPage")
        if not users or next_page in {None, "", page}:
            break
        try:
            page = int(next_page)
        except (TypeError, ValueError):
            break
    return None


def create_or_link_user(
    email: str,
    password: str,
    *,
    name: str | None = None,
    user_type: str = "client",
) -> dict[str, Any]:
    try:
        return admin_create_user(
            email, password, name=name, user_type=user_type)
    except AccountExists:
        user = admin_find_user_by_email(email)
        if user is None:
            raise
        admin_update_user(str(user["id"]), password=password)
        return user


def ensure_password(email: str, password: str, *, name: str | None = None,
                    user_type: str = "client") -> dict[str, Any]:
    user = admin_find_user_by_email(email)
    if user is None:
        return admin_create_user(
            email, password, name=name, user_type=user_type)
    updated = admin_update_user(str(user["id"]), password=password)
    return updated or user
