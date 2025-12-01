"""Binance Futures API client for fast technical data with buy/sell volume."""

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx
from loguru import logger


@dataclass
class KlineWithVolume:
    """Kline data with taker buy/sell volume breakdown."""

    time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    taker_buy_volume: float
    taker_sell_volume: float

    @property
    def sell_ratio(self) -> float:
        """Calculate sell volume ratio (0-1)."""
        if self.volume == 0:
            return 0.5
        return self.taker_sell_volume / self.volume


class BinanceClient:
    """Fast async client for Binance Futures API with volume analysis."""

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
        """Convert MEXC symbol format to Binance format."""
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
        """Get kline data for a symbol (basic format)."""
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

    async def get_klines_with_volume(
        self,
        symbol: str,
        interval: str = "1m",
        limit: int = 50,
    ) -> list[KlineWithVolume]:
        """Get kline data with taker buy/sell volume breakdown.

        Binance kline format:
        [0] Open time
        [1] Open
        [2] High
        [3] Low
        [4] Close
        [5] Volume (total)
        [6] Close time
        [7] Quote asset volume
        [8] Number of trades
        [9] Taker buy base asset volume  <- WE USE THIS
        [10] Taker buy quote asset volume
        [11] Ignore

        Args:
            symbol: MEXC-format symbol (e.g., BTC_USDT).
            interval: Candle interval.
            limit: Number of candles.

        Returns:
            List of KlineWithVolume objects.
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

            klines = []
            for k in raw_klines:
                total_volume = float(k[5])
                taker_buy_volume = float(k[9])
                taker_sell_volume = total_volume - taker_buy_volume

                klines.append(KlineWithVolume(
                    time=k[0],
                    open=float(k[1]),
                    high=float(k[2]),
                    low=float(k[3]),
                    close=float(k[4]),
                    volume=total_volume,
                    taker_buy_volume=taker_buy_volume,
                    taker_sell_volume=taker_sell_volume,
                ))

            return klines

        except Exception as e:
            logger.debug(f"Binance klines with volume error for {symbol}: {e}")
            return []

    async def get_funding_rate(self, symbol: str) -> float | None:
        """Get current funding rate for a symbol.

        Args:
            symbol: MEXC-format symbol.

        Returns:
            Funding rate as percentage (e.g., 0.01 = 0.01%) or None.
        """
        if not self._client:
            return None

        binance_symbol = self._convert_symbol(symbol)
        if not binance_symbol:
            return None

        try:
            response = await self._client.get(
                "/fapi/v1/premiumIndex",
                params={"symbol": binance_symbol},
            )
            response.raise_for_status()
            data = response.json()

            funding_rate = float(data.get("lastFundingRate", 0))
            # Convert to percentage
            return funding_rate * 100

        except Exception as e:
            logger.debug(f"Binance funding rate error for {symbol}: {e}")
            return None

    async def get_recent_sell_ratio(
        self,
        symbol: str,
        interval: str = "1m",
        periods: int = 10,
    ) -> float | None:
        """Calculate recent sell volume ratio.

        Args:
            symbol: MEXC-format symbol.
            interval: Candle interval.
            periods: Number of recent candles to analyze.

        Returns:
            Sell ratio (0-1) where >0.5 means more selling, or None if error.
        """
        klines = await self.get_klines_with_volume(symbol, interval, periods)
        if not klines:
            return None

        total_volume = sum(k.volume for k in klines)
        total_sell = sum(k.taker_sell_volume for k in klines)

        if total_volume == 0:
            return None

        return total_sell / total_volume

    async def get_multi_timeframe_klines(
        self,
        symbol: str,
    ) -> dict[str, list[dict[str, Any]]]:
        """Get klines for multiple timeframes concurrently."""
        intervals = {
            "1m": ("1m", 30),
            "1h": ("1h", 140),  # More for indicator warmup
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
        """Check if a symbol is available on Binance."""
        return self._convert_symbol(mexc_symbol) is not None

    @staticmethod
    def get_futures_url(mexc_symbol: str) -> str:
        """Get the Binance futures trading URL."""
        symbol = mexc_symbol.replace("_", "")
        return f"https://www.binance.com/en/futures/{symbol}"

