from contextlib import asynccontextmanager

import logging

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

import app.db.models 
from app.api.v1.auth import router as auth_router
from app.api.v1.kits import router as kits_router
from app.api.v1.kits_download import router as kits_download_router
from app.api.v1.kits_tree import router as kits_tree_router
from app.api.v1.storage_local import router as storage_local_router
from app.api.v1.users import router as users_router
from app.core.config import settings
from app.core.exceptions import AppException
from app.storage.factory import get_storage_backend


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.arq_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))

    if settings.STORAGE_BACKEND == "b2":
        storage = get_storage_backend()
        await storage.connect()

    yield

    if settings.STORAGE_BACKEND == "b2":
        await get_storage_backend().close()

    await app.state.arq_pool.close()

logging.getLogger("botocore").setLevel(logging.DEBUG)
logging.getLogger("aiobotocore").setLevel(logging.DEBUG)

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET_KEY)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(kits_router, prefix="/api/v1")
app.include_router(kits_tree_router, prefix="/api/v1")
app.include_router(kits_download_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")

if settings.STORAGE_BACKEND == "local":
    from pathlib import Path

    from fastapi.staticfiles import StaticFiles

    storage_root = Path(settings.UPLOADS_STORAGE_ROOT)
    storage_root.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(storage_root)), name="static")

    app.include_router(storage_local_router, prefix="/api/v1")