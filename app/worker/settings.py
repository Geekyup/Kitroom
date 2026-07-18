from arq.connections import RedisSettings

import app.core.logging
import app.db.models
from app.core.config import settings
from app.storage.factory import get_storage_backend
from app.worker.tasks import process_kit


async def startup(ctx: dict) -> None:
    if settings.STORAGE_BACKEND == "b2":
        storage = get_storage_backend()
        await storage.connect()


async def shutdown(ctx: dict) -> None:
    if settings.STORAGE_BACKEND == "b2":
        await get_storage_backend().close()


class WorkerSettings:
    functions = [process_kit]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    job_timeout = 600
    max_jobs = 1