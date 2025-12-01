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


def calculate_trend(closes: list[float]) -> Trend:
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


def calculate_ema(values: list[float], period: int) -> list[float]:
    """Calculate Exponential Moving Average.

    Args:
        values: List of values.
        period: EMA period.

    Returns:
        List of EMA values (same length as input, with NaN for initial values).
    """
    if len(values) < period:
        return [float("nan")] * len(values)

    ema = []
    multiplier = 2 / (period + 1)

    # Start with SMA for first EMA value
    sma = sum(values[:period]) / period
    ema.extend([float("nan")] * (period - 1))
    ema.append(sma)

    # Calculate EMA for remaining values
    for i in range(period, len(values)):
        ema_value = (values[i] - ema[-1]) * multiplier + ema[-1]
        ema.append(ema_value)

    return ema


def calculate_macd(
    closes: list[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[list[float], list[float], list[float]]:
    """Calculate MACD (Moving Average Convergence Divergence).

    Args:
        closes: List of closing prices.
        fast_period: Fast EMA period (default 12).
        slow_period: Slow EMA period (default 26).
        signal_period: Signal line period (default 9).

    Returns:
        Tuple of (macd_line, signal_line, histogram).
    """
    if len(closes) < slow_period + signal_period:
        nan_list = [float("nan")] * len(closes)
        return nan_list, nan_list, nan_list

    # Calculate EMAs
    ema_fast = calculate_ema(closes, fast_period)
    ema_slow = calculate_ema(closes, slow_period)

    # MACD line = Fast EMA - Slow EMA
    macd_line = [
        f - s if not (f != f or s != s) else float("nan")  # Check for NaN
        for f, s in zip(ema_fast, ema_slow)
    ]

    # Signal line = EMA of MACD line
    # Filter out NaN values for signal calculation
    valid_macd = [m for m in macd_line if m == m]  # m == m is False for NaN
    if len(valid_macd) >= signal_period:
        signal_values = calculate_ema(valid_macd, signal_period)

        # Reconstruct signal line with proper alignment
        signal_line = []
        valid_idx = 0
        for m in macd_line:
            if m != m:  # is NaN
                signal_line.append(float("nan"))
            else:
                if valid_idx < len(signal_values):
                    signal_line.append(signal_values[valid_idx])
                    valid_idx += 1
                else:
                    signal_line.append(float("nan"))
    else:
        signal_line = [float("nan")] * len(closes)

    # Histogram = MACD - Signal
    histogram = [
        m - s if not (m != m or s != s) else float("nan")
        for m, s in zip(macd_line, signal_line)
    ]

    return macd_line, signal_line, histogram


def calculate_rsi_series(closes: list[float], period: int = 14) -> list[float]:
    """Calculate RSI series for charting.

    Args:
        closes: List of closing prices.
        period: RSI period.

    Returns:
        List of RSI values (with NaN for initial values).
    """
    if len(closes) < period + 1:
        return [float("nan")] * len(closes)

    rsi_values = [float("nan")] * period

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    # First RSI value
    if avg_loss == 0:
        rsi_values.append(100.0)
    else:
        rs = avg_gain / avg_loss
        rsi_values.append(100 - (100 / (1 + rs)))

    # Remaining RSI values
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            rsi_values.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100 - (100 / (1 + rs)))

    return rsi_values


def is_macd_bearish_cross(macd_line: list[float], signal_line: list[float]) -> bool:
    """Check if MACD just crossed below signal line (bearish cross).

    Args:
        macd_line: MACD line values.
        signal_line: Signal line values.

    Returns:
        True if bearish cross detected.
    """
    if len(macd_line) < 2 or len(signal_line) < 2:
        return False

    # Get last two valid values
    valid_pairs = [
        (m, s) for m, s in zip(macd_line[-3:], signal_line[-3:])
        if m == m and s == s  # Not NaN
    ]

    if len(valid_pairs) < 2:
        return False

    # Check for cross: previously above, now below
    prev_m, prev_s = valid_pairs[-2]
    curr_m, curr_s = valid_pairs[-1]

    return prev_m >= prev_s and curr_m < curr_s

