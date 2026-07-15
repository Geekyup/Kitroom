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