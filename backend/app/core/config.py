"""Environment-backed application configuration."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings with safe development defaults."""

    app_name: str = Field(default="HAVCAN API", validation_alias="APP_NAME")
    app_env: str = Field(default="development", validation_alias="APP_ENV")
    api_prefix: str = Field(default="/api", validation_alias="API_PREFIX")
    host: str = Field(default="127.0.0.1", validation_alias="HOST")
    port: int = Field(default=8000, validation_alias="PORT")
    log_level: str = Field(default="info", validation_alias="LOG_LEVEL")
    mongo_uri: str | None = Field(default=None, validation_alias="MONGO_URI")
    mongo_database: str = Field(default="havcan", validation_alias="MONGO_DATABASE")
    session_cookie_name: str = Field(
        default="havcan_session",
        validation_alias="AUTH_SESSION_COOKIE",
    )
    session_ttl_seconds: int = Field(
        default=60 * 60 * 24 * 14,
        validation_alias="AUTH_SESSION_TTL_SECONDS",
    )
    password_reset_ttl_seconds: int = Field(
        default=60 * 60,
        validation_alias="AUTH_PASSWORD_RESET_TTL_SECONDS",
    )
    auth_cookie_secure: bool = Field(
        default=False,
        validation_alias="AUTH_COOKIE_SECURE",
    )
    allowed_origins: str = Field(
        default="http://127.0.0.1:4173,http://localhost:4173",
        validation_alias="ALLOWED_ORIGINS",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        """Return normalized origins for FastAPI's CORS middleware."""

        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings object."""

    return Settings()