from arq.connections import RedisSettings

import app.core.logging  # noqa: F401 — настраивает logging.basicConfig для процесса воркера
import app.db.models
from app.core.config import settings
from app.worker.tasks import process_kit


class WorkerSettings:
    functions = [process_kit]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    job_timeout = 600
    max_jobs = 1