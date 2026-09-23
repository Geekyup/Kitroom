# Рефакторинг архитектуры: layered → feature-based (по образцу llm-gateway)

## Было (Kitroom, слоистая архитектура)
```
app/
  api/v1/{auth,users,kits,kits_download,kits_tree,storage_local}.py
  api/deps.py            <- один общий файл со ВСЕМИ зависимостями всех доменов
  services/{auth,user,kit_service,archive_service}.py
  repositories/{auth,verification,kit_repository,node_repository}.py
  schemas/{auth,token,user,kit,node}.py
  db/models/{user,drum_kit,drum_kit_node}.py
```
Чтобы понять фичу "kits", нужно было прыгать по 5 папкам.

## Стало (вертикальные срезы, как в llm-gateway)
```
app/
  auth/     — models, schemas, repository, service, deps, router, exceptions, security.py, oauth.py, email.py
  users/    — schemas, service, deps, router (профиль /me и публичный /users/{username})
  kits/     — models, schemas, repository, service, deps, router, exceptions, archive.py, tasks.py
  storage/  — factory, local, b2, deps, router, exceptions (инфраструктура, не домен)
  core/     — config, exceptions (базовый AppException), limiter, logging (общее для всех)
  db/       — base.py (Base, TimestampMixin), session.py, models.py (сборка всех моделей для alembic)
  worker/   — settings.py (ARQ конфиг, ссылается на kits.tasks.process_kit)
  tests/    — app/tests/{auth,users,kits,storage}/, зеркалит структуру app/
```

## Ключевые решения
- **`/me`, `/me/avatar`, `/me/username`** раньше жили в `api/v1/auth.py`, хотя это профиль
  пользователя, а не аутентификация. Перенёс логику в `users/router.py`, но подключил её
  в `main.py` с тем же префиксом `/api/v1/auth`, чтобы **не сломать фронтенд**
  (публичный API проверен побайтово — идентичен оригиналу, см. ниже).
- **Кросс-доменная связь `User.kits ↔ DrumKit.owner`**: `User` живёт в `auth/models.py`,
  `DrumKit` — в `kits/models.py`. SQLAlchemy резолвит `relationship()` по строковому имени
  класса на этапе `configure_mappers()`, так что это работает, если оба модуля
  зарегистрированы на общий `Base` до первого обращения к БД. Для этого есть
  `app/db/models.py` — импортируется в `alembic/env.py`, `worker/settings.py`, `main.py`.
- **`security.py`, `oauth.py`, `email.py`** переехали из `core/` в `auth/` — они специфичны
  для домена аутентификации, а не общая инфраструктура.
- **Дублирование в `KitService`** (`list_catalog`/`list_my_kits`/`list_by_username` — три
  идентичных блока сборки `KitCatalogItemOut`) вынесено в приватный `_to_catalog_item()`.
  Поведение не изменилось, просто убрал копипасту заодно с переносом.

## Исправленный баг (не архитектурный, но пришлось поправить, иначе код не запускался бы)
В оригинале `KitService.confirm_kit_upload` вызывал `self.kit_repo.mark_failed(...)`,
но такого метода в `KitRepository` не было вообще (только `update_status`). Заменил на
`kit_repo.update_status(kit.id, KitStatus.FAILED, error_message=...)` — по смыслу то же самое,
метод для этого и существует. Соответствующий тест обновлён.

## Проверено
- `pytest` — все 81 тест проходят (`app/tests/`)
- `app.main` импортируется без ошибок, публичный API (35 роутов) **идентичен** оригиналу
  побайтово (сравнение через diff списков path+methods)
- `alembic history` — видит всю цепочку миграций без изменений (сами файлы миграций не
  трогались, они не зависят от структуры Python-пакетов)
- `app.worker.settings.WorkerSettings` импортируется корректно
- `Base.metadata.tables` — все 5 таблиц зарегистрированы, кросс-модульные relationship
  резолвятся без ошибок

## Что НЕ менялось
- Frontend (папка `frontend/`) — скопирован как есть, бэкенд-рефакторинг его не касается
- Docker/CI конфиги — скопированы как есть, они не завязаны на внутреннюю структуру `app/`
- Файлы миграций (`migrations/versions/*.py`) — скопированы без изменений
- Бизнес-логика — перенесена дословно (кроме одного исправленного бага выше)
