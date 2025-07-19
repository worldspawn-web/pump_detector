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
