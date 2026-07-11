from arq.connections import RedisSettings

import app.core.logging  # noqa: F401 — настраивает logging.basicConfig для процесса воркера
import app.db.models
from app.core.config import settings
from app.worker.tasks import process_kit


class WorkerSettings:
    functions = [process_kit]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)

    # если процессинг зипа с валидацией аудио может занять время —
    # даём задаче до 10 минут прежде чем ARQ пометит её как failed по таймауту
    job_timeout = 600
    # Было 5 — на контейнере с ограниченной памятью параллельная
    # обработка нескольких китов (каждый может весить сотни МБ) легко
    # приводит к суммарному потреблению памяти выше лимита и OOM kill.
    # Пока не увеличена память контейнера — держим строго 1 job за раз.
    max_jobs = 1