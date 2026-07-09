from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Session (для oauth state/nonce)
    SESSION_SECRET_KEY: str

    # Email (Resend)
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = ""
    VERIFICATION_CODE_EXPIRE_MINUTES: int = 15
    PASSWORD_RESET_CODE_EXPIRE_MINUTES: int = 15

    # Storage (drumkit)
    UPLOADS_STORAGE_ROOT: str = "./storage/uploads"
    PUBLIC_STORAGE_ROOT: str = "./storage/public"
    MAX_ZIP_SIZE_MB: int = 500
    MAX_FILES_PER_KIT: int = 2000
    ALLOWED_AUDIO_EXTENSIONS: set[str] = {".wav", ".mp3", ".aiff", ".flac"}


settings = Settings()