"""Configuration management for Anomaly Pump Detector."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AnomalySettings(BaseSettings):
    """Anomaly detector settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram configuration
    telegram_bot_token: str = Field(..., description="Telegram bot token")
    anomaly_telegram_chat_id: str = Field(..., description="Anomaly detector Telegram chat/channel ID")

    # Anomaly detection criteria
    anomaly_min_volume_spike: float = Field(
        default=5.0,
        description="Minimum volume spike multiplier (e.g., 5.0 = 5x average volume)",
    )
    anomaly_min_candle_body: float = Field(
        default=3.0,
        description="Minimum candle body size multiplier (e.g., 3.0 = 3x average body)",
    )
    anomaly_min_pump_percent: float = Field(
        default=5.0,
        description="Minimum pump percentage in single candle",
    )

    # Scan settings
    scan_interval_seconds: int = Field(
        default=60,
        description="Interval between scans in seconds",
    )

    # MEXC API settings
    mexc_futures_base_url: str = Field(
        default="https://contract.mexc.com",
        description="MEXC Futures API base URL",
    )

    # Tracking settings
    monitoring_hours: int = Field(
        default=48,
        description="Hours to monitor each pump for reversals",
    )
    min_pumps_for_history: int = Field(
        default=1,
        description="Minimum previous pumps to show coin history in signals",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")


@lru_cache
def get_anomaly_settings() -> AnomalySettings:
    """Get cached anomaly settings instance."""
    return AnomalySettings()

