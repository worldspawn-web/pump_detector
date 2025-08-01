import requests


class BinancePriceFeed:
    BASE_URL = "https://fapi.binance.com"

    def get_watchlist(self):
        with open("config/watchlist.txt", "r") as f:
            return [line.strip().upper() for line in f if line.strip()]

    def get_recent_1m_candles(self, symbol):
        url = f"{self.BASE_URL}/fapi/v1/klines?symbol={symbol}&interval=1m&limit=10"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code != 200:
                print(f"  [!] Error fetching {symbol}: {res.status_code} {res.text}")
                return None
            data = res.json()
            if not data:
                print(f"  [!] Empty response for {symbol}")
                return None
            return data
        except Exception as e:
            print(f"  [!] Exception while fetching {symbol}: {e}")
            return None
