from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    DEBUG: bool = False
    PROJECT_NAME: str = "DrumKit Service"

    # Database
    DATABASE_URL: str

    @field_validator("DATABASE_URL")
    @classmethod
    def _ensure_asyncpg_driver(cls, v: str) -> str:
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        return v

    # Redis / ARQ
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""

    # Публичный адрес фронтенда — куда редиректить браузер после google/callback
    FRONTEND_URL: str = "http://localhost:3000"

    # Session (для oauth state/nonce)
    SESSION_SECRET_KEY: str

    # Email (Resend)
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = ""
    VERIFICATION_CODE_EXPIRE_MINUTES: int = 15
    PASSWORD_RESET_CODE_EXPIRE_MINUTES: int = 15

    STORAGE_BACKEND: str = "local"

    @field_validator("STORAGE_BACKEND")
    @classmethod
    def _validate_storage_backend(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in {"local", "b2"}:
            raise ValueError('STORAGE_BACKEND must be "local" or "b2"')
        return v

    # Storage (Backblaze B2, S3-compatible) — обязательны, только если STORAGE_BACKEND=b2
    B2_KEY_ID: str = ""
    B2_APPLICATION_KEY: str = ""
    B2_BUCKET_NAME: str = ""
    B2_ENDPOINT_URL: str = ""
    B2_REGION: str = ""

    UPLOADS_STORAGE_ROOT: str = "./storage/uploads"

    BACKEND_URL: str = "http://localhost:8000"

    MAX_ZIP_SIZE_MB: int = 500
    MAX_FILES_PER_KIT: int = 2000
    ALLOWED_AUDIO_EXTENSIONS: set[str] = {".wav", ".mp3", ".aiff", ".flac"}

    @model_validator(mode="after")
    def _require_b2_vars_when_selected(self) -> "Settings":
        if self.STORAGE_BACKEND == "b2":
            required = {
                "B2_KEY_ID": self.B2_KEY_ID,
                "B2_APPLICATION_KEY": self.B2_APPLICATION_KEY,
                "B2_BUCKET_NAME": self.B2_BUCKET_NAME,
                "B2_ENDPOINT_URL": self.B2_ENDPOINT_URL,
                "B2_REGION": self.B2_REGION,
            }
            missing = [name for name, value in required.items() if not value]
            if missing:
                raise ValueError(
                    f"STORAGE_BACKEND=b2 requires these env vars to be set: {', '.join(missing)}"
                )
        return self


settings = Settings()