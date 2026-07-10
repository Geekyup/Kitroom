from contextlib import asynccontextmanager
from pathlib import Path

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

import app.db.models  # noqa: F401 — регистрирует все модели в реестре SQLAlchemy
from app.api.v1.auth import router as auth_router
from app.api.v1.kits import router as kits_router
from app.api.v1.kits_download import router as kits_download_router
from app.api.v1.kits_tree import router as kits_tree_router
from app.core.config import settings
from app.core.exceptions import AppException


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.arq_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    yield
    await app.state.arq_pool.close()


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


Path(settings.PUBLIC_STORAGE_ROOT).mkdir(parents=True, exist_ok=True)
Path(settings.UPLOADS_STORAGE_ROOT).mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=settings.PUBLIC_STORAGE_ROOT), name="static")

app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(kits_router, prefix="/api/v1")
app.include_router(kits_tree_router, prefix="/api/v1")
app.include_router(kits_download_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)