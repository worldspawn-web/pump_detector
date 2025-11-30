"""Technical indicators calculations."""

from enum import Enum


class Trend(Enum):
    """Market trend direction."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


def calculate_rsi(closes: list[float], period: int = 14) -> float | None:
    """Calculate RSI (Relative Strength Index).

    Args:
        closes: List of closing prices (oldest to newest).
        period: RSI period (default 14).

    Returns:
        RSI value (0-100) or None if insufficient data.
    """
    if len(closes) < period + 1:
        return None

    # Calculate price changes
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

    # Separate gains and losses
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    # Calculate initial average gain/loss
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    # Smooth averages using Wilder's method
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return round(rsi, 2)


def determine_trend(closes: list[float]) -> Trend:
    """Determine trend direction from price data.

    Uses simple moving average comparison and price position.

    Args:
        closes: List of closing prices (oldest to newest).

    Returns:
        Trend enum value.
    """
    if len(closes) < 20:
        return Trend.NEUTRAL

    # Calculate SMAs
    sma_short = sum(closes[-10:]) / 10
    sma_long = sum(closes[-20:]) / 20

    current_price = closes[-1]

    # Trend logic
    if sma_short > sma_long and current_price > sma_short:
        return Trend.BULLISH
    elif sma_short < sma_long and current_price < sma_short:
        return Trend.BEARISH
    else:
        return Trend.NEUTRAL


def get_trend_emoji(trend: Trend) -> str:
    """Get emoji for trend direction.

    Args:
        trend: Trend enum value.

    Returns:
        Emoji string.
    """
    return {
        Trend.BULLISH: "🟢",
        Trend.BEARISH: "🔴",
        Trend.NEUTRAL: "🟡",
    }[trend]


def get_rsi_emoji(rsi: float | None) -> str:
    """Get emoji indicating RSI zone.

    Args:
        rsi: RSI value.

    Returns:
        Emoji string.
    """
    if rsi is None:
        return "⚪"
    if rsi >= 70:
        return "🔴"  # Overbought
    elif rsi <= 30:
        return "🟢"  # Oversold
    else:
        return "🟡"  # Neutral

