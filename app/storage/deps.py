from app.storage.factory import StorageBackend, get_storage_backend


def get_storage() -> StorageBackend:
    return get_storage_backend()
