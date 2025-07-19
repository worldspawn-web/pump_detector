from utils.indicators import calculate_rsi


class SignalEngine:
    def __init__(self, market_data):
        self.market_data = market_data

    def check_signal(self, symbol):
        klines = self.market_data.get_recent_klines(symbol)
        if not klines or len(klines) < 15:
            return None

        closes = [float(k[4]) for k in klines]
        volumes = [float(k[5]) for k in klines]

        prev_close = closes[-2]
        last_close = closes[-1]

        change = ((last_close - prev_close) / prev_close) * 100
        rsi = calculate_rsi(closes[-15:])

        avg_volume = sum(volumes[-16:-1]) / 15
        last_volume = volumes[-1]

        volume_spike = last_volume > avg_volume * 3

        if change > 25 and rsi > 85 and volume_spike:
            return (
                f"\n📉 SHORT SIGNAL on {symbol}:"
                f" +{change:.1f}% in last 15 min | RSI: {rsi:.1f} | Vol x{last_volume/avg_volume:.1f}"
            )
        return None
