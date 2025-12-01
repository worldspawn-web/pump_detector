"""MEXC Futures API client."""

import asyncio
from typing import Any

import httpx
from loguru import logger

from src_reversal.config import ReversalSettings


class MexcClient:
    """Async client for MEXC Futures API."""

    # MEXC kline intervals
    INTERVAL_1M = "Min1"
    INTERVAL_5M = "Min5"
    INTERVAL_15M = "Min15"
    INTERVAL_1H = "Min60"
    INTERVAL_4H = "Hour4"
    INTERVAL_1D = "Day1"
    INTERVAL_1W = "Week1"

    def __init__(self, settings: ReversalSettings) -> None:
        """Initialize the MEXC client."""
        self._base_url = settings.mexc_futures_base_url
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "MexcClient":
        """Enter async context."""
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(60.0, connect=10.0),
            headers={"Content-Type": "application/json"},
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context."""
        if self._client:
            await self._client.aclose()

    async def _request(
        self,
        endpoint: str,
        params: dict | None = None,
        retries: int = 3,
    ) -> dict:
        """Make an API request with retry logic."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        last_error = None
        for attempt in range(retries):
            try:
                response = await self._client.get(endpoint, params=params)
                response.raise_for_status()
                return response.json()
            except (httpx.TimeoutException, httpx.HTTPStatusError) as e:
                last_error = e
                if attempt < retries - 1:
                    wait_time = (attempt + 1) * 2
                    logger.debug(f"Request failed, retrying in {wait_time}s... ({e})")
                    await asyncio.sleep(wait_time)
                continue
            except httpx.HTTPError as e:
                last_error = e
                break

        raise last_error if last_error else httpx.HTTPError("Unknown error")

    async def get_all_tickers(self) -> list[dict[str, Any]]:
        """Get ticker data for all futures symbols."""
        try:
            data = await self._request("/api/v1/contract/ticker")

            if data.get("success") and "data" in data:
                return data["data"]

            logger.warning(f"Unexpected ticker response format: {data}")
            return []

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch tickers: {e}")
            return []

    async def get_funding_rate(self, symbol: str) -> float | None:
        """Get current funding rate for a symbol.

        Args:
            symbol: Trading pair symbol (e.g., BTC_USDT).

        Returns:
            Funding rate as percentage or None if unavailable.
        """
        try:
            data = await self._request(
                "/api/v1/contract/funding_rate",
                params={"symbol": symbol},
                retries=2,
            )

            if data.get("success") and "data" in data:
                rate = data["data"].get("fundingRate")
                if rate is not None:
                    # Convert to percentage
                    return float(rate) * 100
            return None

        except Exception as e:
            logger.debug(f"Failed to fetch funding rate for {symbol}: {e}")
            return None

    async def get_klines(
        self,
        symbol: str,
        interval: str = "Min1",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get kline (candlestick) data for a symbol."""
        try:
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": limit,
            }
            data = await self._request("/api/v1/contract/kline", params=params, retries=2)

            if data.get("success") and "data" in data:
                klines = data["data"]
                if isinstance(klines, dict) and "time" in klines:
                    return self._parse_kline_arrays(klines)
                elif isinstance(klines, list):
                    if klines and "time" in klines[0]:
                        klines.sort(key=lambda x: x["time"])
                    return klines

            return []

        except Exception as e:
            logger.warning(f"Failed to fetch klines for {symbol} ({interval}): {type(e).__name__}")
            return []

    def _parse_kline_arrays(self, data: dict) -> list[dict]:
        """Parse kline data when returned as parallel arrays."""
        try:
            times = data.get("time", [])
            opens = data.get("open", [])
            closes = data.get("close", [])
            highs = data.get("high", [])
            lows = data.get("low", [])
            vols = data.get("vol", [])

            klines = []
            for i in range(len(times)):
                klines.append({
                    "time": times[i],
                    "open": opens[i] if i < len(opens) else 0,
                    "close": closes[i] if i < len(closes) else 0,
                    "high": highs[i] if i < len(highs) else 0,
                    "low": lows[i] if i < len(lows) else 0,
                    "vol": vols[i] if i < len(vols) else 0,
                })

            return klines

        except Exception as e:
            logger.debug(f"Error parsing kline arrays: {e}")
            return []

    async def get_htf_klines(
        self,
        symbol: str,
    ) -> dict[str, list[dict[str, Any]]]:
        """Get higher timeframe klines for resistance detection.

        Fetches 4H, 1D, and 1W klines.
        """
        intervals = {
            "4h": (self.INTERVAL_4H, 100),
            "1d": (self.INTERVAL_1D, 100),
            "1w": (self.INTERVAL_1W, 52),
        }

        results = {}
        for name, (interval, limit) in intervals.items():
            try:
                klines = await self.get_klines(symbol, interval, limit)
                results[name] = klines
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.debug(f"Error fetching {interval} klines for {symbol}: {e}")
                results[name] = []

        return results

    @staticmethod
    def get_futures_url(symbol: str) -> str:
        """Get the MEXC futures trading URL for a symbol."""
        return f"https://futures.mexc.com/exchange/{symbol}"

