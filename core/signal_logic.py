from datetime import datetime, timedelta
import time


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

    def should_alert(self, symbol):
        now = time.time()
        last_alert = self.cooldowns.get(symbol, 0)
        return (now - last_alert) >= self.cooldown_period

    def register_alert(self, symbol):
        self.cooldowns[symbol] = time.time()

    def check_pump(self, symbol, candles, verbose=False):
        if len(candles) < 2:
            return None

        earliest = float(candles[0][1])  # open price 5 мин назад
        latest = float(candles[-1][4])  # close последней свечи
        volume = float(candles[-1][5])
        percent_change = ((latest - earliest) / earliest) * 100

        if verbose:
            vol_str = self._format_volume(volume)
            print(
                f"  └─ {symbol}: Price={candles[-1][4]}, Δ5m={percent_change:.2f}%, Vol={vol_str}"
            )

        if percent_change >= self.threshold:
            timestamp = int(candles[-1][0]) // 1000
            time_str = datetime.utcfromtimestamp(timestamp).strftime("%H:%M UTC")
            return (
                f"🚨 PUMP DETECTED: ${symbol}\n"
                f"📈 Price spike: +{percent_change:.2f}% in 5m\n"
                f"🕒 Time: {time_str}\n"
                f"#pump"
            )
        return None
