from datetime import datetime, timedelta
import time
from collections import defaultdict


class PumpDetector:
    def __init__(self, threshold=5, cooldown_minutes=30):
        self.threshold = threshold
        self.cooldowns = {}
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
        closes = [float(c[4]) for c in candles[-14:]]
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
            return "🔄 <code>Sideways</code>"
        return "📈 <code>Uptrend</code>" if delta > 0 else "📉 <code>Downtrend</code>"

    def _get_levels(self, candles):
        closes = [round(float(c[4]), 6) for c in candles]
        close_counts = defaultdict(int)
        for close in closes:
            close_counts[close] += 1
        common = [lvl for lvl, count in close_counts.items() if count >= 2]
        support = min(common) if common else min(closes)
        resistance = max(common) if common else max(closes)
        return support, resistance

    def _calculate_atr(self, candles, period=14):
        trs = []
        for i in range(1, len(candles)):
            high = float(candles[i][2])
            low = float(candles[i][3])
            prev_close = float(candles[i - 1][4])
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)
        return sum(trs[-period:]) / period if len(trs) >= period else 0

    def _calculate_vwap(self, candles):
        total_volume = 0
        total_vp = 0
        for c in candles:
            high = float(c[2])
            low = float(c[3])
            close = float(c[4])
            volume = float(c[5])
            typical_price = (high + low + close) / 3
            total_vp += typical_price * volume
            total_volume += volume
        return total_vp / total_volume if total_volume else 0

    def should_alert(self, symbol):
        now = time.time()
        last_alert = self.cooldowns.get(symbol, 0)
        return (now - last_alert) >= self.cooldown_period

    def register_alert(self, symbol):
        self.cooldowns[symbol] = time.time()

    def check_pump(self, symbol, candles, funding="N/A", verbose=False):
        if len(candles) < 2:
            return None

        earliest = float(candles[-6][1])  # open 6 свечей назад (5 минут назад)
        latest = float(candles[-1][4])  # последний close
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
                f"🚨 <b>SIGNAL</b> 🚨\n"
                f"Coin: <code>{symbol}</code>\n"
                f"━━━━━━━━━━━━━\n"
                f"📈 Price spike: <code>+{percent_change:.2f}%</code> in 5m\n"
                f"📊 RSI: <code>{rsi:.1f}</code>\n"
                f"💰 Funding Rate: <code>{funding}</code>\n"
                f"📉 Volume: <code>{vol_str}</code>\n"
                f"📐 Trend: {trend}\n"
                f"🔍 Levels: S=<code>{support:.6f}</code>, R=<code>{resistance:.6f}</code>\n"
                f"#pump"
            )
        return None

    def predict_scenario(self, candles, support, resistance):
        if len(candles) < 15:
            return "<i>Not enough data</i>"

        close = float(candles[-1][4])
        volume_now = float(candles[-1][5])
        volume_prev = float(candles[-2][5])
        rsi = self._calculate_rsi(candles)
        atr = self._calculate_atr(candles)
        vwap = self._calculate_vwap(candles)
        trend = self._detect_trend(candles)

        reversal_chance = 0
        continuation_chance = 0

        # Цена близка к сопротивлению → шанс отката
        if resistance and (resistance - close) / close < 0.01:
            reversal_chance += 1

        # RSI > 70 — перекупленность
        if rsi > 70:
            reversal_chance += 1
        elif rsi < 30:
            continuation_chance += 1

        # Объём резко вырос — всплеск
        if volume_now > volume_prev * 1.5:
            reversal_chance += 1

        # Цена выше VWAP более чем на 1%
        if close > vwap * 1.01:
            reversal_chance += 1

        # Тренд ап — шанс на продолжение
        if "Uptrend" in trend:
            continuation_chance += 1
        elif "Downtrend" in trend:
            reversal_chance += 1

        if reversal_chance >= 3:
            return "<b>Likely Reversal</b> 🔻"
        elif continuation_chance >= 2:
            return "<b>Likely Continuation</b> 🔼"
        else:
            return "<b>Sideways or Unclear</b> 🔄"
