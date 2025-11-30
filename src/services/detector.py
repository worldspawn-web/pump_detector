"""Pump detection service."""

from datetime import datetime, timezone

from loguru import logger

from src.config import Settings
from src.models.signal import PumpSignal
from src.services.mexc import MEXCClient


class PumpDetector:
    """Detects pump anomalies in MEXC futures."""

    def __init__(self, settings: Settings, mexc_client: MEXCClient) -> None:
        """Initialize the pump detector.

        Args:
            settings: Application settings.
            mexc_client: MEXC API client.
        """
        self._settings = settings
        self._mexc = mexc_client
        self._alerted_symbols: set[str] = set()  # Track recently alerted symbols

    def clear_alerts(self) -> None:
        """Clear the alerted symbols cache."""
        self._alerted_symbols.clear()

    async def scan_for_pumps(self) -> list[PumpSignal]:
        """Scan all futures for pump anomalies.

        Returns:
            List of detected pump signals.
        """
        signals: list[PumpSignal] = []

        tickers = await self._mexc.get_all_tickers()

        if not tickers:
            logger.warning("No tickers received from MEXC")
            return signals

        logger.info(f"Scanning {len(tickers)} futures pairs...")

        for ticker in tickers:
            signal = self._analyze_ticker(ticker)
            if signal and signal.symbol not in self._alerted_symbols:
                signals.append(signal)
                self._alerted_symbols.add(signal.symbol)
                logger.info(
                    f"Pump detected: {signal.symbol} +{signal.price_change_percent:.2f}%"
                )

        return signals

    def _analyze_ticker(self, ticker: dict) -> PumpSignal | None:
        """Analyze a single ticker for pump conditions.

        Args:
            ticker: Ticker data from MEXC API.

        Returns:
            PumpSignal if pump detected, None otherwise.
        """
        try:
            symbol = ticker.get("symbol", "")
            
            # Get price change percentage from rise_fall_rate (it's already a ratio)
            rise_fall_rate = ticker.get("riseFallRate")
            if rise_fall_rate is None:
                return None

            # Convert to percentage (API returns as decimal, e.g., 0.07 for 7%)
            price_change_percent = float(rise_fall_rate) * 100

            # Check if it meets the pump threshold
            if price_change_percent < self._settings.pump_threshold_percent:
                return None

            # Extract other data
            volume_24h = float(ticker.get("volume24", 0))
            current_price = float(ticker.get("lastPrice", 0))

            return PumpSignal(
                symbol=symbol,
                price_change_percent=price_change_percent,
                volume_24h=volume_24h,
                current_price=current_price,
                detected_at=datetime.now(timezone.utc),
            )

        except (ValueError, TypeError, KeyError) as e:
            logger.debug(f"Error analyzing ticker {ticker.get('symbol', 'unknown')}: {e}")
            return None

