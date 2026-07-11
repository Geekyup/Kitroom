# Добавь это в app/main.py, в самом начале, до создания FastAPI-приложения
# (или в отдельный app/core/logging.py и вызови при старте).
#
# Без явной настройки uvicorn может не выводить логи сторонних логгеров
# на уровне INFO, и ты не увидишь прогресс аплоада.

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

# Явно поднимаем уровень для нашего storage-логгера, на случай если
# basicConfig где-то уже был вызван раньше с более высоким уровнем.
logging.getLogger("kitroom.storage").setLevel(logging.INFO)

# Опционально — если хочешь также видеть сырые HTTP-запросы botocore
# к S3 (полезно для отладки таймаутов/повторов), раскомментируй:
# logging.getLogger("botocore").setLevel(logging.DEBUG)
# logging.getLogger("aiobotocore").setLevel(logging.DEBUG)