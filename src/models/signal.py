"""Signal data models."""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta

from src.utils.indicators import Trend, get_trend_emoji, get_rsi_emoji


# UTC+3 timezone
UTC_PLUS_3 = timezone(timedelta(hours=3))


@dataclass
class ExchangeLinks:
    """Links to the coin on various exchanges."""

    mexc: str = ""
    binance: str | None = None
    bybit: str | None = None
    bingx: str | None = None


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
    trend_1h: Trend = Trend.NEUTRAL
    trend_4h: Trend = Trend.NEUTRAL
    trend_1d: Trend = Trend.NEUTRAL

    # ATH data
    is_ath: bool = False
    ath_price: float | None = None

    # Exchange links
    links: ExchangeLinks = field(default_factory=ExchangeLinks)

    # Data source (which exchange provided technical data)
    data_source: str | None = None

    # Chart image (PNG bytes)
    chart_image: bytes | None = None

    @property
    def has_technical_data(self) -> bool:
        """Check if technical analysis data is available."""
        return self.data_source is not None

    @property
    def coin_name(self) -> str:
        """Get clean coin name without _USDT suffix."""
        return self.symbol.replace("_USDT", "")

    def format_message(self) -> str:
        """Format signal as a Telegram message."""
        # Convert to UTC+3
        local_time = self.detected_at.astimezone(UTC_PLUS_3)

        lines = [
            f"🚀 <b>{self.symbol}</b> 🚀",
            "",
            f"<b>Change:</b> +{self.price_change_percent:.2f}%",
            f"<b>Price:</b> ${self.current_price:.6f}",
            f"<b>Volume 24h:</b> ${self.volume_24h:,.0f}",
        ]

        # Technical analysis section
        lines.extend(
            [
                "",
                "<b>━━━ Technical Analysis ━━━</b>",
            ]
        )

        if self.has_technical_data:
            # RSI formatting
            rsi_1m_text = f"{self.rsi_1m:.0f}" if self.rsi_1m is not None else "N/A"
            rsi_1h_text = f"{self.rsi_1h:.0f}" if self.rsi_1h is not None else "N/A"
            rsi_1m_emoji = get_rsi_emoji(self.rsi_1m)
            rsi_1h_emoji = get_rsi_emoji(self.rsi_1h)

            # Trend formatting
            trend_1h_emoji = get_trend_emoji(self.trend_1h)
            trend_4h_emoji = get_trend_emoji(self.trend_4h)
            trend_1d_emoji = get_trend_emoji(self.trend_1d)

            lines.extend(
                [
                    "",
                    f"<b>RSI:</b> {rsi_1m_emoji} 1M: {rsi_1m_text} | {rsi_1h_emoji} 1H: {rsi_1h_text}",
                    f"<b>Trend:</b> {trend_1h_emoji} 1H | {trend_4h_emoji} 4H | {trend_1d_emoji} 1D",
                ]
            )

            # ATH formatting
            if self.ath_price:
                ath_emoji = "❌" if self.is_ath else "✅"
                if self.is_ath:
                    ath_text = f"ATH: {ath_emoji} ${self.ath_price:.6f}"
                else:
                    ath_diff = (
                        (self.ath_price - self.current_price) / self.current_price
                    ) * 100
                    ath_text = f"ATH: {ath_emoji} ${self.ath_price:.6f} ({ath_diff:.1f}% below)"
                lines.append(f"<b>{ath_text}</b>")
        else:
            # Technical analysis unavailable
            lines.extend(
                [
                    "",
                    "<i>⚠️ Analysis unavailable for MEXC-only pairs</i>",
                ]
            )

        lines.extend(
            [
                "",
                f"<b>Time:</b> {local_time.strftime('%H:%M:%S')} (UTC+3)",
                "",
            ]
        )

        # Exchange links
        exchange_links = self._format_exchange_links()
        if exchange_links:
            lines.append(exchange_links)

        return "\n".join(lines)

    def _format_exchange_links(self) -> str:
        """Format exchange links as italic text."""
        links_parts = []

        # MEXC is always available
        links_parts.append(f'<a href="{self.links.mexc}"><i>MEXC</i></a>')

        if self.links.binance:
            links_parts.append(f'<a href="{self.links.binance}"><i>Binance</i></a>')

        if self.links.bybit:
            links_parts.append(f'<a href="{self.links.bybit}"><i>ByBit</i></a>')

        if self.links.bingx:
            links_parts.append(f'<a href="{self.links.bingx}"><i>BingX</i></a>')

        return "📈 " + " · ".join(links_parts)
