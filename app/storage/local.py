import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings


class LocalStorageBackend:
    """
    Локальный диск как storage backend с разделением приватной/публичной зоны.
    Интерфейс намеренно узкий, чтобы позже подменить на S3Storage
    (приватный bucket + публичный bucket/CDN) без изменений в KitService.
    """

    def __init__(self):
        self.uploads_root = Path(settings.UPLOADS_STORAGE_ROOT)
        self.public_root = Path(settings.PUBLIC_STORAGE_ROOT)
        self.uploads_root.mkdir(parents=True, exist_ok=True)
        self.public_root.mkdir(parents=True, exist_ok=True)

    async def save_upload(self, file: UploadFile) -> str:
        """Сохраняет оригинальный zip в приватную зону."""
        filename = f"{uuid.uuid4()}.zip"
        dest = self.uploads_root / "kits" / filename
        dest.parent.mkdir(parents=True, exist_ok=True)

        with open(dest, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                f.write(chunk)

        return str(dest)

    async def save_cover(self, kit_id: int, file: UploadFile) -> str:
        """Сохраняет обложку кита в публичную зону — отдаётся напрямую через /static."""
        extension = Path(file.filename or "cover.jpg").suffix or ".jpg"
        dest = self.public_root / "kits" / str(kit_id) / f"cover{extension}"
        dest.parent.mkdir(parents=True, exist_ok=True)

        with open(dest, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                f.write(chunk)

        return str(dest)

    async def save_avatar(self, user_id: int, file: UploadFile) -> str:
        """Сохраняет аватар пользователя в публичную зону — отдаётся напрямую через /static."""
        extension = Path(file.filename or "avatar.jpg").suffix or ".jpg"
        dest = self.public_root / "avatars" / str(user_id) / f"avatar{extension}"
        dest.parent.mkdir(parents=True, exist_ok=True)

        with open(dest, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                f.write(chunk)

        return str(dest)

    def get_path(self, absolute_path: str) -> Path:
        return Path(absolute_path)

    def delete(self, path: str) -> None:
        p = Path(path)
        if p.exists():
            p.unlink()