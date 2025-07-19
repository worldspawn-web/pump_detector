from utils.indicators import calculate_rsi


class SignalEngine:
    def __init__(self, market_data):
        self.market_data = market_data

    def check_signal(self, symbol):
        klines = self.market_data.get_recent_klines(symbol)
        if not klines or len(klines) < 2:
            return None

        prev_close = float(klines[-2][4])  # close of previous candle
        last_close = float(klines[-1][4])  # close of current candle

        change = ((last_close - prev_close) / prev_close) * 100

        if change > 25:
            return f"\n📉 SHORT SIGNAL on {symbol}: +{change:.1f}% in last 15 min"
        return None
