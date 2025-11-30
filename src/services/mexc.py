"""MEXC Futures API client."""

from typing import Any

import httpx
from loguru import logger

from src.config import Settings


class MEXCClient:
    """Async client for MEXC Futures API."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the MEXC client.

        Args:
            settings: Application settings.
        """
        self._base_url = settings.mexc_futures_base_url
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "MEXCClient":
        """Enter async context."""
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=30.0,
            headers={"Content-Type": "application/json"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context."""
        if self._client:
            await self._client.aclose()

    async def _request(self, endpoint: str, params: dict | None = None) -> dict:
        """Make an API request.

        Args:
            endpoint: API endpoint.
            params: Query parameters.

        Returns:
            JSON response data.

        Raises:
            httpx.HTTPError: If request fails.
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        response = await self._client.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()

    async def get_all_tickers(self) -> list[dict[str, Any]]:
        """Get ticker data for all futures symbols.

        Returns:
            List of ticker data dictionaries.
        """
        try:
            data = await self._request("/api/v1/contract/ticker")

            if data.get("success") and "data" in data:
                return data["data"]

            logger.warning(f"Unexpected ticker response format: {data}")
            return []

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch tickers: {e}")
            return []

    async def get_klines(
        self,
        symbol: str,
        interval: str = "Min1",
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Get kline (candlestick) data for a symbol.

        Args:
            symbol: Trading pair symbol.
            interval: Candle interval (Min1, Min5, Min15, Min30, Min60, Hour4, Hour8, Day1, Week1, Month1).
            limit: Number of candles to fetch.

        Returns:
            List of kline data.
        """
        try:
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": limit,
            }
            data = await self._request("/api/v1/contract/kline", params=params)

            if data.get("success") and "data" in data:
                return data["data"]

            return []

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch klines for {symbol}: {e}")
            return []

