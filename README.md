# Kitroom

**Kitroom** — платформа для загрузки, хранения и обмена драм-китами (наборами аудиосэмплов для битмейкеров и продюсеров).

Пользователь загружает ZIP-архив с сэмплами → сервис распаковывает его в фоне, строит дерево папок/файлов, извлекает метаданные аудио → другие пользователи могут просматривать кит как в проводнике, слушать сэмплы прямо в браузере и скачивать архив целиком.


---

## Стек технологий

**Backend**

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?logo=sqlalchemy&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)
![ARQ](https://img.shields.io/badge/ARQ-task_queue-2E7D32)
![Alembic](https://img.shields.io/badge/Alembic-migrations-6BA81E)

**Frontend**

![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=next.js&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![TailwindCSS](https://img.shields.io/badge/TailwindCSS-4-06B6D4?logo=tailwindcss&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178C6?logo=typescript&logoColor=white)

**Инфраструктура и интеграции**

![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![S3](https://img.shields.io/badge/S3--compatible-Cloud.ru_B2-569A31?logo=amazons3&logoColor=white)
![Google OAuth](https://img.shields.io/badge/OAuth-Google-4285F4?logo=google&logoColor=white)
![Resend](https://img.shields.io/badge/Email-Resend-000000)
![JWT](https://img.shields.io/badge/Auth-JWT-000000?logo=jsonwebtokens&logoColor=white)

---

## Функциональность

- **Загрузка китов ZIP-архивом** — с прямой загрузкой в S3 по presigned URL, минуя backend (быстрее и без нагрузки на сервер при больших файлах)
- **Фоновая обработка архива**: распаковка, валидация файлов, разбор структуры папок, подсчёт количества сэмплов — пользователь в это время видит статус (`pending → processing → ready / failed`)
- **Дерево файлов кита** — навигация по вложенным папкам как в обычном проводнике, без необходимости скачивать архив
- **Прослушивание сэмплов** прямо в браузере и скачивание кита целиком
- **Каталог китов** с собственной страницей кита (обложка, жанр, теги, описание, счётчик скачиваний)
- **Личный кабинет**: список своих китов, редактирование метаданных, удаление
- **Авторизация**:
  - email + пароль с подтверждением почты 6-значным кодом
  - вход через Google (OAuth2, redirect-флоу)
  - JWT access/refresh токены с автоматическим обновлением сессии на фронтенде
  - восстановление пароля по коду на почту
- **Rate limiting** на регистрации, логине, восстановлении пароля — защита от брутфорса и спама
- **Переключаемое хранилище файлов**: локальный диск для разработки или S3-совместимое хранилище (Cloud.ru B2) для продакшена — одна переменная окружения, без изменений в коде

## Демонстрация

![alt text](image.png)

---

## Инструкция по запуску

### Через Docker (рекомендуется)

```bash
git clone https://github.com/Geekyup/Kitroom.git
cd Kitroom
cp .env.example .env   # заполнить переменные окружения, см. ниже
docker compose up --build
```

- Backend API: `http://localhost:8000` (Swagger-документация: `/docs`)
- Frontend: `http://localhost:3000`

`docker-compose.yml` поднимает пять сервисов: `postgres`, `redis`, `migrate` (одноразовое применение Alembic-миграций), `api`, `worker`, `frontend`.

### Локально, без Docker

Требуется: Python 3.12+, Node.js 20+, запущенные PostgreSQL и Redis.

```bash
# Backend
pip install -r requirements.txt
alembic upgrade head
python -m app.main              # API на :8000

# Worker (в отдельном терминале)
python -m arq app.worker.settings.WorkerSettings

# Frontend (в отдельном терминале)
cd frontend
npm install
npm run dev                     # UI на :3000
```
### Тесты

```bash
py -m pytest tests/ -v
```

### Основные переменные окружения

| Переменная | Описание |
|---|---|
| `DATABASE_URL` | строка подключения к PostgreSQL |
| `REDIS_URL` | строка подключения к Redis |
| `SECRET_KEY`, `SESSION_SECRET_KEY` | секреты для JWT и сессий OAuth |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` | Google OAuth |
| `RESEND_API_KEY`, `EMAIL_FROM` | отправка писем (подтверждение почты, сброс пароля) |
| `STORAGE_BACKEND` | `local` или `b2` — переключатель хранилища файлов |
| `B2_KEY_ID`, `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`, `B2_ENDPOINT_URL`, `B2_REGION` | обязательны при `STORAGE_BACKEND=b2` |
| `MAX_ZIP_SIZE_MB`, `MAX_FILES_PER_KIT` | лимиты на загружаемый архив (по умолчанию 500 МБ / 2000 файлов) |

Полный список — в `app/core/config.py`.

---

