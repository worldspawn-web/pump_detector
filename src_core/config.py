"""Configuration management for Core Pump Detector."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CoreSettings(BaseSettings):
    """Core detector settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram configuration
    telegram_bot_token: str = Field(..., description="Telegram bot token")
    core_telegram_chat_id: str = Field(..., description="Core detector Telegram chat/channel ID")

    # Core pump detection settings
    core_pump_threshold_percent: float = Field(
        default=5.0,
        description="Minimum price increase percentage to trigger alert",
    )
    core_min_volume_usd: int = Field(
        default=500_000,
        description="Minimum 24h volume in USD to track a pump",
    )
    
    # Scan settings
    scan_interval_seconds: int = Field(
        default=60,
        description="Interval between scans in seconds",
    )

    # Watchlist settings
    watchlist_file: str = Field(
        default="watchlist.txt",
        description="Path to watchlist file with coin symbols",
    )

    # MEXC API settings
    mexc_futures_base_url: str = Field(
        default="https://contract.mexc.com",
        description="MEXC Futures API base URL",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")


@lru_cache
def get_core_settings() -> CoreSettings:
    """Get cached core settings instance."""
    return CoreSettings()

