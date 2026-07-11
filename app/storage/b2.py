import asyncio
import logging
import time
import uuid
from pathlib import Path

import aioboto3
from botocore.config import Config
from fastapi import UploadFile

from app.core.config import settings

logger = logging.getLogger("kitroom.storage")


class B2StorageBackend:
    """
    S3-совместимый storage backend (Backblaze B2 / Railway Bucket / любой S3 API).
    Тот же интерфейс, что у LocalStorageBackend, но вместо путей на диске
    возвращает object key — единый способ адресации что для
    приватных (kits zip), так и для публичных (cover/avatar/extracted) объектов,
    т.к. в S3-совместимых хранилищах нет разделения на "публичную папку" — публичность
    обеспечивается presigned URL с ограниченным сроком жизни (см. get_url).
    """

    def __init__(self):
        self.bucket = settings.B2_BUCKET_NAME
        self._session = aioboto3.Session()
        self._client_kwargs = dict(
            endpoint_url=settings.B2_ENDPOINT_URL,
            aws_access_key_id=settings.B2_KEY_ID,
            aws_secret_access_key=settings.B2_APPLICATION_KEY,
            region_name=settings.B2_REGION,
            config=Config(
                signature_version="s3v4",
                # Обязательно для Railway Bucket и большинства self-hosted
                # S3-совместимых сервисов (MinIO, Garage и т.д.) — без этого
                # клиент пытается резолвить bucket.endpoint (virtual-hosted style)
                # и падает с SignatureDoesNotMatch / DNS ошибкой.
                # Backblaze B2 нормально работает с этой опцией тоже, так что
                # переезд между провайдерами не ломает совместимость.
                s3={"addressing_style": "path"},
                # Явные таймауты — иначе зависший коннект молча ждёт минутами
                # вместо быстрого фейла с понятной ошибкой.
                # read_timeout уменьшен с 120 до 30: extracted-файлы (сэмплы)
                # обычно небольшие, 120s на попытку с 5 retries давали до 10
                # минут ожидания на одном подвисшем файле.
                connect_timeout=10,
                read_timeout=30,
                retries={"max_attempts": 3, "mode": "standard"},
                max_pool_connections=20,
            ),
        )
        # Порог, с которого put_object заменяется на multipart upload
        # с параллельной заливкой частей — резко ускоряет большие файлы.
        # Уменьшенный chunk size (5MB, минимум для S3 multipart) и меньший
        # параллелизм — компромисс в пользу стабильности на нестабильных
        # сетях (Docker Desktop на Windows периодически рвёт долгие
        # исходящие соединения на больших частях).
        self._multipart_threshold = 16 * 1024 * 1024  # 16MB
        self._multipart_chunksize = 8 * 1024 * 1024  # 8MB вместо 16MB
        self._multipart_concurrency = 4  # 4 вместо 8 — меньше шанс упереться в обрыв

        # Параллелизм для batch-загрузки множества мелких файлов
        # (extracted-сэмплы кита) в рамках одного переиспользуемого клиента.
        self._batch_concurrency = 8

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
        """Используется для одиночной загрузки (одна операция — один клиент)."""
        async with self._get_client() as client:
            await client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type or "application/octet-stream",
            )
        return key

    async def save_many_bytes(
        self,
        items: list[tuple[bytes, str, str | None]],
        concurrency: int | None = None,
    ) -> None:
        """
        Батч-загрузка множества файлов через ОДИН переиспользуемый клиент
        с ограниченным параллелизмом.

        Используется ArchiveService для заливки всех extracted-сэмплов кита
        разом — вместо создания нового TCP/TLS соединения на каждый файл
        (как было раньше при последовательных save_bytes в цикле), что на
        архивах с десятками-сотнями файлов давало огромные накладные расходы
        на handshake и суммарно растягивало обработку на много минут.

        items: список (data, key, content_type)
        """
        if not items:
            return

        sem = asyncio.Semaphore(concurrency or self._batch_concurrency)
        total = len(items)
        completed = 0
        t_start = time.monotonic()

        async with self._get_client() as client:

            async def _put(data: bytes, key: str, content_type: str | None) -> None:
                nonlocal completed
                async with sem:
                    await client.put_object(
                        Bucket=self.bucket,
                        Key=key,
                        Body=data,
                        ContentType=content_type or "application/octet-stream",
                    )
                    completed += 1
                    if completed % 10 == 0 or completed == total:
                        elapsed = time.monotonic() - t_start
                        logger.info(
                            "[batch-upload] %d/%d файлов загружено за %.1fs",
                            completed, total, elapsed,
                        )

            await asyncio.gather(*[_put(d, k, c) for d, k, c in items])

        elapsed = time.monotonic() - t_start
        logger.info("[batch-upload] ЗАВЕРШЕНО %d файлов за %.1fs", total, elapsed)

    async def download_to_file(self, key: str, dest_path: str, timeout_seconds: float = 300) -> int:
        """
        Стримит объект из S3 сразу на диск, НЕ накапливая его в памяти.

        Нужен для больших архивов (сотни МБ): get_bytes() держит весь
        файл в оперативке (плюс временную копию при join чанков) — на
        контейнере с ограниченной памятью (Railway) это приводило к
        OOM kill прямо посреди скачивания, без единой ошибки в логах
        (ядро просто убивает процесс). Запись на диск чанками держит
        потребление памяти на уровне одного chunk_size вне зависимости
        от размера файла.

        Возвращает количество записанных байт.
        """
        async def _download() -> int:
            written = 0
            async with self._get_client() as client:
                response = await client.get_object(Bucket=self.bucket, Key=key)
                with open(dest_path, "wb") as f:
                    async for chunk in response["Body"].iter_chunks(chunk_size=1024 * 1024):
                        f.write(chunk)
                        written += len(chunk)
            return written

        try:
            return await asyncio.wait_for(_download(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            logger.error(
                "download_to_file: скачивание %s не уложилось в %.0fs — обрыв/слишком медленный канал",
                key, timeout_seconds,
            )
            raise

    async def get_bytes(self, key: str, timeout_seconds: float = 300) -> bytes:
        """
        Используется для НЕБОЛЬШИХ объектов (обложки, аватары и т.п.).
        Для больших архивов используй download_to_file — здесь файл
        всё ещё целиком попадает в память.

        Читаем поток ЧАНКАМИ через iter_chunks(), а не одним
        await response["Body"].read(). botocore's read_timeout считается
        между чанками (idle timeout), а не на всю операцию, так что
        read() его не соблюдает как общий дедлайн — оборачиваем всё в
        asyncio.wait_for с общим таймаутом.
        """
        async def _download() -> bytes:
            async with self._get_client() as client:
                response = await client.get_object(Bucket=self.bucket, Key=key)
                chunks: list[bytes] = []
                async for chunk in response["Body"].iter_chunks(chunk_size=1024 * 1024):
                    chunks.append(chunk)
                return b"".join(chunks)

        try:
            return await asyncio.wait_for(_download(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            logger.error(
                "get_bytes: скачивание %s не уложилось в %.0fs — обрыв/слишком медленный канал",
                key, timeout_seconds,
            )
            raise

    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        """Presigned URL — замена /static/... для приватного бакета."""
        async with self._get_client() as client:
            return await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
            )

    async def get_upload_url(
        self, key: str, content_type: str = "application/zip", expires_in: int = 3600
    ) -> str:
        """
        Presigned PUT URL — клиент грузит файл НАПРЯМУЮ в S3, минуя бэкенд.
        Даёт максимальную скорость аплоада, т.к. файл больше не проходит
        через контейнер API (убирает двойной сетевой проход и упирание
        в его CPU/память/сетевой канал, особенно критично на Docker Desktop).

        Использование на фронте: получить URL, затем сделать
        fetch(url, { method: "PUT", body: file, headers: { "Content-Type": content_type } })
        """
        async with self._get_client() as client:
            return await client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
            )

    def generate_upload_key(self) -> str:
        """Генерирует object_key для будущего кита без записи в S3 (для presigned-флоу)."""
        return f"kits/uploads/{uuid.uuid4()}.zip"

    async def head_object(self, key: str) -> dict:
        """
        Проверяет, что объект реально загружен в S3 (клиент отчитался "готово").
        Возвращает метаданные (ContentLength и т.д.) или бросает ClientError,
        если объекта нет — используй это перед постановкой в очередь на обработку.
        """
        async with self._get_client() as client:
            return await client.head_object(Bucket=self.bucket, Key=key)

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
        """
        Стримит файл в S3 чанками через upload_fileobj вместо чтения всего
        файла в память (await file.read()).

        Для больших файлов aioboto3/boto3 s3transfer автоматически включает
        multipart upload (порог задаётся TransferConfig) и параллельно грузит
        несколько частей — это даёт основной прирост скорости на файлах
        от нескольких десятков МБ и выше, т.к. вместо одного медленного
        последовательного запроса идёт N параллельных.

        Логирует прогресс по мере передачи (через Callback у s3transfer) и
        точное время старта/финиша/ошибки — это нужно, чтобы при обрыве
        соединения было видно: сколько байт успело уйти, сколько времени
        прошло с начала аплоада, и сразу ли рвётся или после N MB.
        """
        from boto3.s3.transfer import TransferConfig

        transfer_config = TransferConfig(
            multipart_threshold=self._multipart_threshold,
            multipart_chunksize=self._multipart_chunksize,
            max_concurrency=self._multipart_concurrency,
            use_threads=True,
        )

        # UploadFile.file — это SpooledTemporaryFile с синхронным read(),
        # upload_fileobj умеет работать с обычным file-like объектом.
        file.file.seek(0)
        file.file.seek(0, 2)  # к концу, чтобы узнать размер
        total_size = file.file.tell()
        file.file.seek(0)

        upload_id = uuid.uuid4().hex[:8]
        logger.info(
            "[upload:%s] СТАРТ key=%s size=%.2fMB chunk=%dMB concurrency=%d",
            upload_id, key, total_size / 1024 / 1024,
            self._multipart_chunksize // (1024 * 1024), self._multipart_concurrency,
        )

        progress = {"transferred": 0, "last_logged_pct": -10}
        t_start = time.monotonic()

        def _progress_callback(bytes_transferred: int) -> None:
            progress["transferred"] += bytes_transferred
            if total_size > 0:
                pct = int(progress["transferred"] / total_size * 100)
            else:
                pct = 0
            # Логируем каждые ~10%, чтобы не заспамить логи на больших файлах
            if pct >= progress["last_logged_pct"] + 10:
                elapsed = time.monotonic() - t_start
                speed_mbps = (progress["transferred"] / 1024 / 1024) / elapsed if elapsed > 0 else 0
                logger.info(
                    "[upload:%s] прогресс %d%% (%.2f/%.2f MB) за %.1fs, скорость ~%.2f MB/s",
                    upload_id, pct, progress["transferred"] / 1024 / 1024,
                    total_size / 1024 / 1024, elapsed, speed_mbps,
                )
                progress["last_logged_pct"] = pct

        try:
            async with self._get_client() as client:
                await client.upload_fileobj(
                    file.file,
                    self.bucket,
                    key,
                    ExtraArgs={"ContentType": file.content_type or "application/octet-stream"},
                    Config=transfer_config,
                    Callback=_progress_callback,
                )
        except Exception as e:
            elapsed = time.monotonic() - t_start
            logger.error(
                "[upload:%s] ОБРЫВ после %.2f/%.2f MB (%.0f%%), за %.1fs: %s: %s",
                upload_id,
                progress["transferred"] / 1024 / 1024,
                total_size / 1024 / 1024,
                (progress["transferred"] / total_size * 100) if total_size else 0,
                elapsed,
                type(e).__name__,
                e,
            )
            raise

        elapsed = time.monotonic() - t_start
        speed_mbps = (total_size / 1024 / 1024) / elapsed if elapsed > 0 else 0
        logger.info(
            "[upload:%s] ЗАВЕРШЕНО %.2fMB за %.1fs, средняя скорость %.2f MB/s",
            upload_id, total_size / 1024 / 1024, elapsed, speed_mbps,
        )


b2_storage = B2StorageBackend()