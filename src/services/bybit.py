"""ByBit Futures API client for technical data."""

import asyncio
from typing import Any

import httpx
from loguru import logger


class ByBitClient:
    """Fast async client for ByBit Futures API (public data only)."""

    BASE_URL = "https://api.bybit.com"

    def __init__(self) -> None:
        """Initialize the ByBit client."""
        self._client: httpx.AsyncClient | None = None
        self._available_symbols: set[str] | None = None

    async def __aenter__(self) -> "ByBitClient":
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
        """Load available ByBit linear futures symbols."""
        try:
            response = await self._client.get(
                "/v5/market/instruments-info",
                params={"category": "linear"}
            )
            response.raise_for_status()
            data = response.json()

            if data.get("retCode") == 0:
                self._available_symbols = {
                    s["symbol"] for s in data.get("result", {}).get("list", [])
                    if s.get("status") == "Trading"
                }
                logger.info(f"Loaded {len(self._available_symbols)} ByBit futures symbols")
            else:
                self._available_symbols = set()
        except Exception as e:
            logger.warning(f"Failed to load ByBit symbols: {e}")
            self._available_symbols = set()

    def _convert_symbol(self, mexc_symbol: str) -> str | None:
        """Convert MEXC symbol to ByBit format.

        Args:
            mexc_symbol: MEXC symbol (e.g., BTC_USDT)

        Returns:
            ByBit symbol (e.g., BTCUSDT) or None if not available.
        """
        bybit_symbol = mexc_symbol.replace("_", "")

        if self._available_symbols and bybit_symbol in self._available_symbols:
            return bybit_symbol
        return None

    async def get_klines(
        self,
        symbol: str,
        interval: str = "1",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get kline data for a symbol.

        Args:
            symbol: MEXC-format symbol (e.g., BTC_USDT).
            interval: Candle interval (1, 5, 15, 60, 240, D).
            limit: Number of candles to fetch.

        Returns:
            List of kline data.
        """
        if not self._client:
            return []

        bybit_symbol = self._convert_symbol(symbol)
        if not bybit_symbol:
            return []

        try:
            response = await self._client.get(
                "/v5/market/kline",
                params={
                    "category": "linear",
                    "symbol": bybit_symbol,
                    "interval": interval,
                    "limit": limit,
                },
            )
            response.raise_for_status()
            data = response.json()

            if data.get("retCode") != 0:
                return []

            raw_klines = data.get("result", {}).get("list", [])

            # ByBit returns newest first, we need oldest first
            # Format: [startTime, open, high, low, close, volume, turnover]
            klines = []
            for k in reversed(raw_klines):
                klines.append({
                    "time": int(k[0]),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                })

            return klines

        except Exception as e:
            logger.debug(f"ByBit klines error for {symbol}: {e}")
            return []

    async def get_multi_timeframe_klines(
        self,
        symbol: str,
    ) -> dict[str, list[dict[str, Any]]]:
        """Get klines for multiple timeframes concurrently."""
        intervals = {
            "1m": ("1", 30),
            "1h": ("60", 30),
            "4h": ("240", 25),
            "1d": ("D", 100),
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
        """Check if a symbol is available on ByBit."""
        return self._convert_symbol(mexc_symbol) is not None

    @staticmethod
    def get_futures_url(mexc_symbol: str) -> str:
        """Get the ByBit futures trading URL."""
        symbol = mexc_symbol.replace("_", "")
        return f"https://www.bybit.com/trade/usdt/{symbol}"

