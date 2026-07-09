from arq.connections import RedisSettings

import app.db.models  # noqa: F401 — регистрирует все модели в реестре SQLAlchemy
from app.core.config import settings
from app.worker.tasks import process_kit


class WorkerSettings:
    functions = [process_kit]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)

    # если процессинг зипа с валидацией аудио может занять время —
    # даём задаче до 10 минут прежде чем ARQ пометит её как failed по таймауту
    job_timeout = 600
    max_jobs = 5