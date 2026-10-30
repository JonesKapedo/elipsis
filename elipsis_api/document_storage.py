"""Storage for compliance document attachments.

S3 is used when it is configured. Local disk is the development fallback so
the attachment flow stays usable without cloud credentials.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import UploadFile

from elipsis_api.config import UPLOAD_DIR
from elipsis_api.services_s3 import (
    MAX_FILE_SIZE,
    generate_presigned_url,
    is_s3_configured,
    upload_file_to_s3,
    validate_file,
)


class AttachmentError(ValueError):
    """A safe, user-facing attachment error."""


def _safe_key(name: str) -> str:
    suffix = Path(name or "").suffix.lower()
    if not suffix:
        raise AttachmentError("The file needs a name and an extension.")
    return (
        f"compliance/{datetime.now(UTC).year}/{datetime.now(UTC).month:02d}/"
        f"{uuid.uuid4().hex}{suffix}"
    )


def local_path(key: str) -> Path:
    """Resolve a stored key, refusing anything outside the upload directory."""
    root = UPLOAD_DIR.resolve()
    path = (root / key).resolve()
    if root not in path.parents:
        raise AttachmentError("Invalid attachment path.")
    return path


async def store_attachment(file: UploadFile) -> dict:
    valid, error = validate_file(file, "documents")
    if not valid:
        raise AttachmentError(error)
    content = await file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise AttachmentError("The file is larger than the 50 MB limit.")
    if not content:
        raise AttachmentError("The selected file is empty.")
    key = _safe_key(file.filename or "")
    name = os.path.basename(file.filename or "attachment")
    if is_s3_configured():
        await file.seek(0)
        stored = await upload_file_to_s3(file, folder="compliance")
        return {
            "name": name,
            "key": stored["s3_key"],
            "backend": "s3",
            "size": stored["file_size"],
            "type": stored.get("file_type") or file.content_type,
        }
    path = local_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return {
        "name": name,
        "key": key,
        "backend": "local",
        "size": len(content),
        "type": file.content_type or "application/octet-stream",
    }


def attachment_url(key: str, backend: str | None) -> str | None:
    if backend == "s3":
        return generate_presigned_url(key)
    return None


async def remove_attachment(key: str | None, backend: str | None) -> None:
    if not key:
        return
    if backend == "s3":
        from elipsis_api.services_s3 import delete_file_from_s3

        try:
            await delete_file_from_s3(key)
        except Exception:  # noqa: BLE001 - cleanup must never block a request
            return
        return
    try:
        local_path(key).unlink(missing_ok=True)
    except (OSError, AttachmentError):
        return
