"""Configuration management using pydantic-settings."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Telegram configuration
    telegram_bot_token: str = Field(..., description="Telegram bot token")
    telegram_chat_id: str = Field(..., description="Telegram chat/channel ID")

    # Pump detection settings
    pump_threshold_percent: float = Field(
        default=7.0,
        description="Minimum price increase percentage to trigger alert",
    )
    scan_interval_seconds: int = Field(
        default=60,
        description="Interval between scans in seconds",
    )
    candle_interval: str = Field(
        default="Min1",
        description="Candle interval for analysis (Min1, Min5, Min15, etc.)",
    )
    candles_to_analyze: int = Field(
        default=5,
        description="Number of recent candles to analyze for pump detection",
    )

    # MEXC API settings
    mexc_futures_base_url: str = Field(
        default="https://contract.mexc.com",
        description="MEXC Futures API base URL",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

