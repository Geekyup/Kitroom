from pathlib import Path

from fastapi import APIRouter, Request

from app.core.config import settings
from app.core.exceptions import AppException
from app.storage.local import consume_upload_token, resolve_upload_token

router = APIRouter(prefix="/storage", tags=["storage"])


class UploadTokenInvalid(AppException):
    status_code = 400
    detail = "Upload token is invalid or expired"


@router.put("/local-upload/{token}")
async def local_upload(token: str, request: Request) -> dict:
    key = resolve_upload_token(token)
    if key is None:
        raise UploadTokenInvalid()

    dest = Path(settings.UPLOADS_STORAGE_ROOT) / key
    dest.parent.mkdir(parents=True, exist_ok=True)

    with open(dest, "wb") as f:
        async for chunk in request.stream():
            f.write(chunk)

    consume_upload_token(token)
    return {"key": key, "size_bytes": dest.stat().st_size}