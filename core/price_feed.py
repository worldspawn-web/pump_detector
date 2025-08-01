import requests


class MexcPriceFeed:
    BASE_URL = "https://api.mexc.com"

    def get_watchlist(self):
        with open("config/watchlist.txt", "r") as f:
            return [line.strip().upper() for line in f if line.strip()]

    def get_recent_1m_candles(self, symbol):
        url = f"{self.BASE_URL}/api/v3/klines?symbol={symbol}&interval=1m&limit=10"
        res = requests.get(url)
        if res.status_code != 200:
            return None
        return res.json()
