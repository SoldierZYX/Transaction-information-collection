"""Typed application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration defaults approved for the MVP foundation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="ASHARE_",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    business_timezone: str = "Asia/Shanghai"
    storage_timezone: str = "UTC"
    database_url: str = "sqlite:///data/ashare_review.sqlite3"
    data_dir: Path = Path("data")
    reports_dir: Path = Path("reports")
    ai_enabled: bool = False
    email_enabled: bool = False
    openai_api_key: SecretStr | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None

    @field_validator("business_timezone", "storage_timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        """Reject invalid IANA timezone names during startup."""
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            message = f"Unknown IANA timezone: {value}"
            raise ValueError(message) from error
        return value


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide immutable settings instance."""
    return Settings()
