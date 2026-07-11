import uuid
from pathlib import Path

import aioboto3
from botocore.config import Config
from fastapi import UploadFile

from app.core.config import settings


class B2StorageBackend:
    """
    Backblaze B2 (S3-совместимый) storage backend.
    Тот же интерфейс, что у LocalStorageBackend, но вместо путей на диске
    возвращает B2 object key — единый способ адресации что для
    приватных (kits zip), что для публичных (cover/avatar/extracted) объектов,
    т.к. в B2 нет разделения на "публичную папку" — публичность обеспечивается
    presigned URL с ограниченным сроком жизни (см. get_url).
    """

    def __init__(self):
        self.bucket = settings.B2_BUCKET_NAME
        self._session = aioboto3.Session()
        self._client_kwargs = dict(
            endpoint_url=settings.B2_ENDPOINT_URL,
            aws_access_key_id=settings.B2_KEY_ID,
            aws_secret_access_key=settings.B2_APPLICATION_KEY,
            region_name=settings.B2_REGION,
            config=Config(signature_version="s3v4"),
        )

    def _get_client(self):
        return self._session.client("s3", **self._client_kwargs)

    async def save_upload(self, file: UploadFile) -> str:
        """Загружает оригинальный zip, возвращает object_key."""
        key = f"kits/uploads/{uuid.uuid4()}.zip"
        await self._upload_fileobj(file, key)
        return key

    async def save_cover(self, kit_id: int, file: UploadFile) -> str:
        extension = Path(file.filename or "cover.jpg").suffix or ".jpg"
        key = f"kits/{kit_id}/cover{extension}"
        await self._upload_fileobj(file, key)
        return key

    async def save_avatar(self, user_id: int, file: UploadFile) -> str:
        extension = Path(file.filename or "avatar.jpg").suffix or ".jpg"
        key = f"avatars/{user_id}/avatar{extension}"
        await self._upload_fileobj(file, key)
        return key

    async def save_bytes(self, data: bytes, key: str, content_type: str | None = None) -> str:
        """Используется ArchiveService для загрузки распакованных звуков."""
        async with self._get_client() as client:
            await client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type or "application/octet-stream",
            )
        return key

    async def get_bytes(self, key: str) -> bytes:
        """Используется ArchiveService, чтобы скачать zip перед распаковкой."""
        async with self._get_client() as client:
            response = await client.get_object(Bucket=self.bucket, Key=key)
            return await response["Body"].read()

    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        """Presigned URL — замена /static/... для приватного бакета."""
        async with self._get_client() as client:
            return await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
            )

    def delete(self, key: str) -> None:
        """
        Синхронный интерфейс сохранён ради совместимости с KitService,
        но сам вызов должен быть async — см. delete_async.
        Оставлено как no-op с предупреждением; используйте delete_async.
        """
        raise NotImplementedError("Use delete_async for B2StorageBackend")

    async def delete_async(self, key: str) -> None:
        async with self._get_client() as client:
            await client.delete_object(Bucket=self.bucket, Key=key)

    async def delete_prefix(self, prefix: str) -> None:
        """Удаляет все объекты под префиксом — для очистки kits/{id}/extracted/."""
        async with self._get_client() as client:
            paginator = client.get_paginator("list_objects_v2")
            async for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                objects = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
                if objects:
                    await client.delete_objects(Bucket=self.bucket, Delete={"Objects": objects})

    async def _upload_fileobj(self, file: UploadFile, key: str) -> None:
        async with self._get_client() as client:
            await client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=await file.read(),
                ContentType=file.content_type or "application/octet-stream",
            )


b2_storage = B2StorageBackend()
