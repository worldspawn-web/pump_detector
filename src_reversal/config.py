"""Configuration management for reversal detector."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ReversalSettings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields from main script's .env
    )

    # Telegram configuration (same bot, different channel)
    telegram_bot_token: str = Field(..., description="Telegram bot token")
    telegram_reversal_channel_id: str = Field(
        ..., 
        description="Telegram channel ID for reversal signals"
    )

    # Detection settings
    pump_threshold_percent: float = Field(
        default=7.0,
        description="Minimum pump percentage to analyze",
    )
    min_volume_usd: float = Field(
        default=1_000_000,
        description="Minimum 24h volume in USD",
    )
    scan_interval_seconds: int = Field(
        default=15,
        description="Interval between scans in seconds",
    )

    # Reversal tracking settings
    success_retrace_percent: float = Field(
        default=50.0,
        description="Percentage retrace to count as success",
    )
    failure_increase_percent: float = Field(
        default=5.0,
        description="Percentage increase above signal to count as failure",
    )
    monitoring_hours: int = Field(
        default=12,
        description="Hours to monitor each signal",
    )

    # API settings
    mexc_futures_base_url: str = Field(
        default="https://contract.mexc.com",
        description="MEXC Futures API base URL",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")


@lru_cache
def get_reversal_settings() -> ReversalSettings:
    """Get cached settings instance."""
    return ReversalSettings()

