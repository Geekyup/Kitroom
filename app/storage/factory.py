"""
Единая точка выбора storage backend'а — локальный диск или B2/S3.

Переключение делается ОДНОЙ переменной окружения (STORAGE_BACKEND=local
или STORAGE_BACKEND=b2), без правок кода. Оба backend'а реализуют
одинаковый интерфейс (save_upload, save_cover, save_avatar, get_url,
get_upload_url, head_object, delete_async, delete_prefix,
download_to_file, save_many_bytes, generate_upload_key) — весь код
сервисов (KitService, ArchiveService, UserService) работает с любым
из них без изменений.

StorageBackend — единственный экземпляр на процесс (как раньше был
b2_storage), создаётся лениво при первом обращении.
"""

from typing import Union

from app.core.config import settings
from app.storage.b2 import B2StorageBackend
from app.storage.local import LocalStorageBackend

StorageBackend = Union[LocalStorageBackend, B2StorageBackend]

_storage_instance: StorageBackend | None = None


def get_storage_backend() -> StorageBackend:
    global _storage_instance
    if _storage_instance is None:
        if settings.STORAGE_BACKEND == "b2":
            _storage_instance = B2StorageBackend()
        else:
            _storage_instance = LocalStorageBackend()
    return _storage_instance