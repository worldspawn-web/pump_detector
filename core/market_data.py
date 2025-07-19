import time
import requests


class BinanceMarketData:
    BASE_URL = "https://fapi.binance.com"

    def get_active_symbols(self):
        url = f"{self.BASE_URL}/fapi/v1/ticker/24hr"
        res = requests.get(url)
        data = res.json()
        symbols = [
            s
            for s in data
            if s["symbol"].endswith("USDT") and float(s["quoteVolume"]) > 10000000
        ]
        return symbols

    def get_recent_klines(self, symbol, interval="15m", limit=100):
        url = f"{self.BASE_URL}/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
        res = requests.get(url)
        if res.status_code != 200:
            return None
        return res.json()
