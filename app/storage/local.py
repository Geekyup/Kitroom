import time
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings

_pending_uploads: dict[str, dict] = {}

UPLOAD_TOKEN_TTL_SECONDS = 3600


def register_upload_token(key: str, content_type: str) -> str:
    token = uuid.uuid4().hex
    _pending_uploads[token] = {
        "key": key,
        "content_type": content_type,
        "expires_at": time.monotonic() + UPLOAD_TOKEN_TTL_SECONDS,
    }
    return token


def resolve_upload_token(token: str) -> str | None:
    """Возвращает object key для токена, если он существует и не истёк."""
    entry = _pending_uploads.get(token)
    if entry is None:
        return None
    if time.monotonic() > entry["expires_at"]:
        _pending_uploads.pop(token, None)
        return None
    return entry["key"]


def consume_upload_token(token: str) -> None:
    _pending_uploads.pop(token, None)


class LocalStorageBackend:

    def __init__(self):
        self.root = Path(settings.UPLOADS_STORAGE_ROOT)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for_key(self, key: str) -> Path:
        return self.root / key

    async def _write_upload_file(self, file: UploadFile, key: str) -> str:
        dest = self._path_for_key(key)
        dest.parent.mkdir(parents=True, exist_ok=True)

        with open(dest, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                f.write(chunk)

        return key

    async def save_upload(self, file: UploadFile) -> str:
        """Сохраняет оригинальный zip, возвращает object_key (как B2)."""
        key = f"kits/uploads/{uuid.uuid4()}.zip"
        return await self._write_upload_file(file, key)

    async def save_cover(self, kit_id: int, file: UploadFile) -> str:
        extension = Path(file.filename or "cover.jpg").suffix or ".jpg"
        key = f"kits/{kit_id}/cover{extension}"
        return await self._write_upload_file(file, key)

    async def save_avatar(self, user_id: int, file: UploadFile) -> str:
        extension = Path(file.filename or "avatar.jpg").suffix or ".jpg"
        key = f"avatars/{user_id}/avatar{extension}"
        return await self._write_upload_file(file, key)

    async def save_bytes(self, data: bytes, key: str, content_type: str | None = None) -> str:
        dest = self._path_for_key(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return key

    async def save_many_bytes(
        self,
        items: list[tuple[bytes, str, str | None]],
        concurrency: int | None = None,
    ) -> None:
        for data, key, _content_type in items:
            dest = self._path_for_key(key)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)

    async def download_to_file(self, key: str, dest_path: str, timeout_seconds: float = 300) -> int:
        src = self._path_for_key(key)
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(src.read_bytes())
        return dest.stat().st_size

    async def get_bytes(self, key: str, timeout_seconds: float = 300) -> bytes:
        return self._path_for_key(key).read_bytes()

    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        return f"{settings.BACKEND_URL}/static/{key}"

    async def get_upload_url(
        self, key: str, content_type: str = "application/zip", expires_in: int = 3600
    ) -> str:
        token = register_upload_token(key, content_type)
        return f"{settings.BACKEND_URL}/api/v1/storage/local-upload/{token}"

    def generate_upload_key(self) -> str:
        return f"kits/uploads/{uuid.uuid4()}.zip"

    async def head_object(self, key: str) -> dict:
        """
        Аналог S3 head_object — бросает FileNotFoundError, если объекта нет
        (в KitService это ловится как ClientError для B2; для local режима
        см. обработку в storage_local-роуте/KitService, где нужно ловить
        оба типа исключений одинаково).
        """
        path = self._path_for_key(key)
        if not path.exists():
            raise FileNotFoundError(key)
        return {"ContentLength": path.stat().st_size}

    def delete(self, key: str) -> None:
        p = self._path_for_key(key)
        if p.exists():
            p.unlink()
            self._cleanup_empty_parents(p.parent)

    async def delete_async(self, key: str) -> None:
        self.delete(key)

    async def delete_prefix(self, prefix: str) -> None:
        """Удаляет все файлы под key-префиксом — аналог B2 delete_prefix
        (используется для чистки kits/{id}/extracted/ и т.д.)."""
        base = self._path_for_key(prefix)
        if not base.exists():
            return
        if base.is_file():
            base.unlink()
            self._cleanup_empty_parents(base.parent)
            return
        for p in sorted(base.rglob("*"), key=lambda x: len(x.parts), reverse=True):
            if p.is_file():
                p.unlink()
        for p in sorted(base.rglob("*"), key=lambda x: len(x.parts), reverse=True):
            if p.is_dir() and not any(p.iterdir()):
                p.rmdir()
        if base.exists() and base.is_dir() and not any(base.iterdir()):
            base.rmdir()

    def _cleanup_empty_parents(self, folder: Path) -> None:
        """После удаления файла подчищает опустевшие родительские папки,
        не поднимаясь выше self.root."""
        current = folder
        while current != self.root and current.is_relative_to(self.root):
            if not current.exists():
                break
            if any(current.iterdir()):
                break
            current.rmdir()
            current = current.parent