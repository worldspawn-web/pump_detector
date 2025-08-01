from datetime import datetime


class PumpDetector:
    def _format_volume(self, volume):
        if volume >= 1_000_000_000:
            return f"{volume/1_000_000_000:.1f}B"
        elif volume >= 1_000_000:
            return f"{volume/1_000_000:.1f}M"
        elif volume >= 1_000:
            return f"{volume/1_000:.1f}K"
        else:
            return f"{volume:.1f}"

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

        if percent_change >= 5:
            timestamp = int(candles[-1][0]) // 1000
            time_str = datetime.utcfromtimestamp(timestamp).strftime("%H:%M UTC")
            return (
                f"🚨 PUMP DETECTED: ${symbol}\n"
                f"📈 Price spike: +{percent_change:.2f}% in 5m\n"
                f"🕒 Time: {time_str}\n"
                f"#pump"
            )
        return None
