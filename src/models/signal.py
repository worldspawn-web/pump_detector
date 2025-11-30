"""Signal data models."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class PumpSignal:
    """Represents a detected pump signal."""

    symbol: str
    price_change_percent: float
    volume_24h: float
    current_price: float
    detected_at: datetime

    def format_message(self) -> str:
        """Format signal as a Telegram message."""
        return (
            f"🚀 <b>PUMP DETECTED</b> 🚀\n\n"
            f"<b>Coin:</b> {self.symbol}\n"
            f"<b>Change:</b> +{self.price_change_percent:.2f}%\n"
            f"<b>Price:</b> ${self.current_price:.6f}\n"
            f"<b>Volume 24h:</b> ${self.volume_24h:,.0f}\n"
            f"<b>Time:</b> {self.detected_at.strftime('%H:%M:%S UTC')}"
        )

