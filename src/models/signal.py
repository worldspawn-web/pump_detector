"""Signal data models."""

from dataclasses import dataclass
from datetime import datetime

from src.utils.indicators import Trend, get_trend_emoji, get_rsi_emoji


@dataclass
class PumpSignal:
    """Represents a detected pump signal with technical analysis."""

    symbol: str
    price_change_percent: float
    volume_24h: float
    current_price: float
    detected_at: datetime

    # RSI values
    rsi_1m: float | None = None
    rsi_1h: float | None = None

    # Trend analysis
    trend_4h: Trend = Trend.NEUTRAL
    trend_1d: Trend = Trend.NEUTRAL

    # ATH data
    is_ath: bool = False
    ath_price: float | None = None

    # Link
    mexc_url: str = ""

    def format_message(self) -> str:
        """Format signal as a Telegram message."""
        # ATH indicator
        if self.ath_price:
            ath_emoji = "❌" if self.is_ath else "✅"
            ath_text = f"ATH: {ath_emoji}"
            if not self.is_ath:
                ath_diff = ((self.ath_price - self.current_price) / self.current_price) * 100
                ath_text += f" ({ath_diff:.1f}% below)"
        else:
            ath_text = "ATH: ⚪ N/A"

        # RSI formatting
        rsi_1m_text = f"{self.rsi_1m:.0f}" if self.rsi_1m is not None else "N/A"
        rsi_1h_text = f"{self.rsi_1h:.0f}" if self.rsi_1h is not None else "N/A"
        rsi_1m_emoji = get_rsi_emoji(self.rsi_1m)
        rsi_1h_emoji = get_rsi_emoji(self.rsi_1h)

        # Trend formatting
        trend_4h_emoji = get_trend_emoji(self.trend_4h)
        trend_1d_emoji = get_trend_emoji(self.trend_1d)

        return (
            f"🚀 <b>PUMP DETECTED</b> 🚀\n"
            f"\n"
            f"<b>Coin:</b> {self.symbol}\n"
            f"<b>Change:</b> +{self.price_change_percent:.2f}%\n"
            f"<b>Price:</b> ${self.current_price:.6f}\n"
            f"<b>Volume 24h:</b> ${self.volume_24h:,.0f}\n"
            f"\n"
            f"<b>━━━ Technical Analysis ━━━</b>\n"
            f"\n"
            f"<b>RSI:</b> {rsi_1m_emoji} 1m: {rsi_1m_text} | {rsi_1h_emoji} 1h: {rsi_1h_text}\n"
            f"<b>Trend:</b> {trend_4h_emoji} 4H | {trend_1d_emoji} 1D\n"
            f"<b>{ath_text}</b>\n"
            f"\n"
            f"<b>Time:</b> {self.detected_at.strftime('%H:%M:%S UTC')}\n"
            f"\n"
            f"<a href=\"{self.mexc_url}\">📈 Open on MEXC</a>"
        )
