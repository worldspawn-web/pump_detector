"""BingX Futures API client for technical data."""

import asyncio
from typing import Any

import httpx
from loguru import logger


class BingXClient:
    """Fast async client for BingX Futures API (public data only)."""

    BASE_URL = "https://open-api.bingx.com"

    def __init__(self) -> None:
        """Initialize the BingX client."""
        self._client: httpx.AsyncClient | None = None
        self._available_symbols: set[str] | None = None

    async def __aenter__(self) -> "BingXClient":
        """Enter async context."""
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=httpx.Timeout(10.0, connect=5.0),
            headers={"Content-Type": "application/json"},
        )
        await self._load_symbols()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context."""
        if self._client:
            await self._client.aclose()

    async def _load_symbols(self) -> None:
        """Load available BingX perpetual futures symbols."""
        try:
            response = await self._client.get("/openApi/swap/v2/quote/contracts")
            response.raise_for_status()
            data = response.json()

            if data.get("code") == 0:
                self._available_symbols = {
                    s["symbol"] for s in data.get("data", [])
                    if s.get("status") == 1
                }
                logger.info(f"Loaded {len(self._available_symbols)} BingX futures symbols")
            else:
                self._available_symbols = set()
        except Exception as e:
            logger.warning(f"Failed to load BingX symbols: {e}")
            self._available_symbols = set()

    def _convert_symbol(self, mexc_symbol: str) -> str | None:
        """Convert MEXC symbol to BingX format."""
        bingx_symbol = mexc_symbol.replace("_", "-")

        if self._available_symbols and bingx_symbol in self._available_symbols:
            return bingx_symbol
        return None

    async def get_klines(
        self,
        symbol: str,
        interval: str = "1m",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get kline data for a symbol."""
        if not self._client:
            return []

        bingx_symbol = self._convert_symbol(symbol)
        if not bingx_symbol:
            return []

        try:
            response = await self._client.get(
                "/openApi/swap/v3/quote/klines",
                params={
                    "symbol": bingx_symbol,
                    "interval": interval,
                    "limit": limit,
                },
            )
            response.raise_for_status()
            data = response.json()

            if data.get("code") != 0:
                return []

            raw_klines = data.get("data", [])

            klines = []
            for k in raw_klines:
                klines.append({
                    "time": int(k.get("time", 0)),
                    "open": float(k.get("open", 0)),
                    "high": float(k.get("high", 0)),
                    "low": float(k.get("low", 0)),
                    "close": float(k.get("close", 0)),
                    "volume": float(k.get("volume", 0)),
                })

            klines.sort(key=lambda x: x["time"])
            return klines

        except Exception as e:
            logger.debug(f"BingX klines error for {symbol}: {e}")
            return []

    async def get_funding_rate(self, symbol: str) -> float | None:
        """Get current funding rate for a symbol.

        Returns:
            Funding rate as percentage or None.
        """
        if not self._client:
            return None

        bingx_symbol = self._convert_symbol(symbol)
        if not bingx_symbol:
            return None

        try:
            response = await self._client.get(
                "/openApi/swap/v2/quote/premiumIndex",
                params={"symbol": bingx_symbol},
            )
            response.raise_for_status()
            data = response.json()

            if data.get("code") == 0:
                rate = data.get("data", {}).get("lastFundingRate")
                if rate:
                    return float(rate) * 100

            return None

        except Exception as e:
            logger.debug(f"BingX funding rate error for {symbol}: {e}")
            return None

    async def get_multi_timeframe_klines(
        self,
        symbol: str,
    ) -> dict[str, list[dict[str, Any]]]:
        """Get klines for multiple timeframes concurrently."""
        intervals = {
            "1m": ("1m", 30),
            "1h": ("1h", 140),
            "4h": ("4h", 100),
            "1d": ("1d", 100),
        }

        tasks = {
            name: self.get_klines(symbol, interval, limit)
            for name, (interval, limit) in intervals.items()
        }

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        return {
            name: result if isinstance(result, list) else []
            for name, result in zip(tasks.keys(), results)
        }

    def has_symbol(self, mexc_symbol: str) -> bool:
        """Check if a symbol is available on BingX."""
        return self._convert_symbol(mexc_symbol) is not None

    @staticmethod
    def get_futures_url(mexc_symbol: str) -> str:
        """Get the BingX futures trading URL."""
        symbol = mexc_symbol.replace("_", "-")
        return f"https://bingx.com/en/perpetual/{symbol}/"

