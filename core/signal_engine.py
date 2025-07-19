from utils.indicators import calculate_rsi


class SignalEngine:
    def check_signal(self, symbol_data):
        price_change = float(symbol_data["priceChangePercent"])
        symbol = symbol_data["symbol"]

        if price_change > 25:
            # Простейший фильтр пампа
            return f"\n📉 SHORT SIGNAL on {symbol}: +{price_change:.1f}% in 24h"
        return None
