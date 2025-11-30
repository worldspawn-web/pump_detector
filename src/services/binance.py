"""Binance Futures API client for fast technical data."""

import asyncio
from typing import Any

import httpx
from loguru import logger


class BinanceClient:
    """Fast async client for Binance Futures API (public data only)."""

    BASE_URL = "https://fapi.binance.com"

    def __init__(self) -> None:
        """Initialize the Binance client."""
        self._client: httpx.AsyncClient | None = None
        self._available_symbols: set[str] | None = None

    async def __aenter__(self) -> "BinanceClient":
        """Enter async context."""
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=httpx.Timeout(10.0, connect=5.0),
            headers={"Content-Type": "application/json"},
        )
        # Pre-fetch available symbols
        await self._load_symbols()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context."""
        if self._client:
            await self._client.aclose()

    async def _load_symbols(self) -> None:
        """Load available Binance futures symbols."""
        try:
            response = await self._client.get("/fapi/v1/exchangeInfo")
            response.raise_for_status()
            data = response.json()
            self._available_symbols = {
                s["symbol"] for s in data.get("symbols", [])
                if s.get("status") == "TRADING"
            }
            logger.info(f"Loaded {len(self._available_symbols)} Binance futures symbols")
        except Exception as e:
            logger.warning(f"Failed to load Binance symbols: {e}")
            self._available_symbols = set()

    def _convert_symbol(self, mexc_symbol: str) -> str | None:
        """Convert MEXC symbol format to Binance format.

        Args:
            mexc_symbol: MEXC symbol (e.g., BTC_USDT)

        Returns:
            Binance symbol (e.g., BTCUSDT) or None if not available.
        """
        # MEXC: BTC_USDT -> Binance: BTCUSDT
        binance_symbol = mexc_symbol.replace("_", "")

        if self._available_symbols and binance_symbol in self._available_symbols:
            return binance_symbol
        return None

    async def get_klines(
        self,
        symbol: str,
        interval: str = "1m",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get kline (candlestick) data for a symbol.

        Args:
            symbol: MEXC-format symbol (e.g., BTC_USDT).
            interval: Candle interval (1m, 5m, 15m, 1h, 4h, 1d).
            limit: Number of candles to fetch.

        Returns:
            List of kline data with keys: time, open, high, low, close, volume.
        """
        if not self._client:
            return []

        binance_symbol = self._convert_symbol(symbol)
        if not binance_symbol:
            return []

        try:
            response = await self._client.get(
                "/fapi/v1/klines",
                params={
                    "symbol": binance_symbol,
                    "interval": interval,
                    "limit": limit,
                },
            )
            response.raise_for_status()
            raw_klines = response.json()

            # Convert Binance format to our standard format
            # Binance: [openTime, open, high, low, close, volume, closeTime, ...]
            klines = []
            for k in raw_klines:
                klines.append({
                    "time": k[0],
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                })

            return klines

        except Exception as e:
            logger.debug(f"Binance klines error for {symbol}: {e}")
            return []

    async def get_multi_timeframe_klines(
        self,
        symbol: str,
    ) -> dict[str, list[dict[str, Any]]]:
        """Get klines for multiple timeframes concurrently.

        Args:
            symbol: MEXC-format symbol (e.g., BTC_USDT).

        Returns:
            Dict mapping interval name to kline data.
        """
        intervals = {
            "1m": ("1m", 30),
            "1h": ("1h", 30),
            "4h": ("4h", 25),
            "1d": ("1d", 100),
        }

        # Fetch all timeframes concurrently (Binance is fast!)
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
        """Check if a symbol is available on Binance.

        Args:
            mexc_symbol: MEXC-format symbol.

        Returns:
            True if symbol exists on Binance.
        """
        return self._convert_symbol(mexc_symbol) is not None

