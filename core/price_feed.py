import aiohttp
import asyncio


class BinancePriceFeed:
    BASE_URL = "https://fapi.binance.com"

    def get_watchlist(self):
        with open("config/watchlist.txt", "r") as f:
            return [line.strip().upper() for line in f if line.strip()]

    async def get_recent_1m_candles(self, session, symbol):
        url = f"{self.BASE_URL}/fapi/v1/klines?symbol={symbol}&interval=1m&limit=10"
        try:
            async with session.get(url, timeout=10) as res:
                if res.status != 200:
                    print(
                        f"  [!] Error fetching {symbol}: {res.status} {await res.text()}"
                    )
                    return symbol, None
                data = await res.json()
                return symbol, data
        except Exception as e:
            print(f"  [!] Exception while fetching {symbol}: {e}")
            return symbol, None

    async def get_funding_rate(self, session, symbol):
        url = f"{self.BASE_URL}/fapi/v1/fundingRate?symbol={symbol}&limit=1"
        try:
            async with session.get(url, timeout=10) as res:
                if res.status != 200:
                    return symbol, "N/A"
                data = await res.json()
                if data:
                    return symbol, f"{float(data[0]['fundingRate']) * 100:.4f}%"
                return symbol, "N/A"
        except:
            return symbol, "N/A"

    async def get_all_funding_rates(self):
        watchlist = self.get_watchlist()
        funding_data = {}
        async with aiohttp.ClientSession() as session:
            tasks = [self.get_funding_rate(session, symbol) for symbol in watchlist]
            results = await asyncio.gather(*tasks)
            for symbol, rate in results:
                funding_data[symbol] = rate
        return funding_data

    async def get_all_candles(self):
        watchlist = self.get_watchlist()
        candles_data = {}
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.get_recent_1m_candles(session, symbol) for symbol in watchlist
            ]
            results = await asyncio.gather(*tasks)
            for symbol, candles in results:
                candles_data[symbol] = candles
        return candles_data
