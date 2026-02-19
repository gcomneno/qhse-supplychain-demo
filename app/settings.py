from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENV: str = "dev"
    DATABASE_URL: str = "sqlite:///./qhse_demo.sqlite3"

    JWT_SECRET: str = "change-me"
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MIN: int = 60

    OUTBOX_BATCH_SIZE: int = 10
    OUTBOX_LOCK_TIMEOUT_SEC: int = 30
    OUTBOX_MAX_ATTEMPTS: int = 5

    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True
    REQUEST_ID_HEADER: str = "X-Request-ID"

    ENABLE_TRACING: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
