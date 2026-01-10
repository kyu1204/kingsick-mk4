"""
Configuration settings for KingSick backend.

Uses pydantic-settings for type-safe configuration management
with automatic environment variable loading.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be overridden by environment variables.
    For example, DATABASE_URL env var will override database_url setting.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application settings
    app_name: str = "KingSick"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False

    # Database settings
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/kingsick"

    # Redis settings
    redis_url: str = "redis://localhost:6379/0"

    # JWT settings
    jwt_secret: str = "change-this-secret-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Encryption settings
    encryption_key: str = "change-this-32-byte-key-in-prod"

    # CORS settings
    cors_origins: list[str] = ["http://localhost:3000"]

    # API settings
    api_v1_prefix: str = "/api/v1"

    # KIS API settings
    kis_app_key: str = ""
    kis_app_secret: str = ""
    kis_account_no: str = ""
    kis_is_mock: bool = True

    # Telegram Bot settings
    telegram_bot_token: str = ""
    telegram_bot_username: str = ""
    telegram_webhook_secret: str = ""
    telegram_webhook_url: str = ""
    telegram_enabled: bool = False


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure settings are loaded only once
    and the same instance is reused throughout the application.

    Returns:
        Settings: The application settings instance.
    """
    return Settings()
