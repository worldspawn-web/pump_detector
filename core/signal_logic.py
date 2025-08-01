from datetime import datetime, timedelta
import time
from collections import defaultdict


class PumpDetector:
    def __init__(self, threshold=5, cooldown_minutes=30):
        self.threshold = threshold
        self.cooldowns = {}  # symbol: last_signal_timestamp
        self.cooldown_period = cooldown_minutes * 60

    def _format_volume(self, volume):
        if volume >= 1_000_000_000:
            return f"{volume/1_000_000_000:.1f}B"
        elif volume >= 1_000_000:
            return f"{volume/1_000_000:.1f}M"
        elif volume >= 1_000:
            return f"{volume/1_000:.1f}K"
        else:
            return f"{volume:.1f}"

    def _calculate_rsi(self, candles):
        closes = [float(c[4]) for c in candles[-10:]]
        deltas = [closes[i + 1] - closes[i] for i in range(len(closes) - 1)]
        ups = [d for d in deltas if d > 0]
        downs = [-d for d in deltas if d < 0]
        avg_gain = sum(ups) / len(ups) if ups else 0.0001
        avg_loss = sum(downs) / len(downs) if downs else 0.0001
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _detect_trend(self, candles):
        closes = [float(c[4]) for c in candles[-5:]]
        delta = closes[-1] - closes[0]
        if abs(delta) < closes[0] * 0.002:
            return "🔄 Sideways"
        return "📈 Uptrend" if delta > 0 else "📉 Downtrend"

    def _get_levels(self, candles):
        closes = [round(float(c[4]), 4) for c in candles]
        close_counts = defaultdict(int)
        for close in closes:
            close_counts[close] += 1
        common = [lvl for lvl, count in close_counts.items() if count >= 2]
        support = min(common) if common else min(closes)
        resistance = max(common) if common else max(closes)
        return support, resistance

    def should_alert(self, symbol):
        now = time.time()
        last_alert = self.cooldowns.get(symbol, 0)
        return (now - last_alert) >= self.cooldown_period

    def register_alert(self, symbol):
        self.cooldowns[symbol] = time.time()

    def check_pump(self, symbol, candles, funding="N/A", verbose=False):
        if len(candles) < 2:
            return None

        earliest = float(candles[0][1])
        latest = float(candles[-1][4])
        volume = float(candles[-1][5])
        percent_change = ((latest - earliest) / earliest) * 100
        rsi = self._calculate_rsi(candles)
        trend = self._detect_trend(candles)
        support, resistance = self._get_levels(candles)

        if verbose:
            vol_str = self._format_volume(volume)
            print(
                f"  └─ {symbol}: Price={candles[-1][4]}, Δ5m={percent_change:.2f}%, Vol={vol_str}, RSI={rsi:.1f}, Trend={trend}, Funding={funding}"
            )

        if percent_change >= self.threshold:
            vol_str = self._format_volume(volume)
            return (
                f"🚨 PUMP DETECTED: <code>{symbol}</code>\n"
                f"📈 Price spike: +{percent_change:.2f}% in 5m\n"
                f"📊 RSI: {rsi:.1f}\n"
                f"💰 Funding Rate: {funding}\n"
                f"📉 Volume: {vol_str}\n"
                f"📐 Trend: {trend}\n"
                f"🔍 Levels: S={support:.4f}, R={resistance:.4f}\n"
                f"#pump"
            )
        return None
