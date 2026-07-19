from functools import cache
from typing import Union

from app.core.config import settings
from app.storage.b2 import B2StorageBackend
from app.storage.local import LocalStorageBackend

StorageBackend = Union[LocalStorageBackend, B2StorageBackend]

@cache 
def get_storage_backend() -> StorageBackend:
    if settings.STORAGE_BACKEND == "b2":
        return B2StorageBackend()
    return LocalStorageBackend()