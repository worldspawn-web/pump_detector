"""Pump detection service with technical analysis."""

from datetime import datetime, timezone

from loguru import logger

from src.config import Settings
from src.models.signal import PumpSignal
from src.services.mexc import MEXCClient
from src.services.binance import BinanceClient
from src.utils.indicators import calculate_rsi, determine_trend, Trend


class PumpDetector:
    """Detects pump anomalies in MEXC futures with technical analysis."""

    def __init__(
        self,
        settings: Settings,
        mexc_client: MEXCClient,
        binance_client: BinanceClient,
    ) -> None:
        """Initialize the pump detector.

        Args:
            settings: Application settings.
            mexc_client: MEXC API client.
            binance_client: Binance API client for fast technical data.
        """
        self._settings = settings
        self._mexc = mexc_client
        self._binance = binance_client
        self._alerted_symbols: set[str] = set()

    def clear_alerts(self) -> None:
        """Clear the alerted symbols cache."""
        self._alerted_symbols.clear()

    async def scan_for_pumps(self) -> list[PumpSignal]:
        """Scan all futures for pump anomalies.

        Returns:
            List of detected pump signals with technical analysis.
        """
        signals: list[PumpSignal] = []

        tickers = await self._mexc.get_all_tickers()

        if not tickers:
            logger.warning("No tickers received from MEXC")
            return signals

        logger.info(f"Scanning {len(tickers)} futures pairs...")

        # First pass: identify potential pumps
        potential_pumps = []
        for ticker in tickers:
            if self._is_pump(ticker):
                symbol = ticker.get("symbol", "")
                if symbol not in self._alerted_symbols:
                    potential_pumps.append(ticker)

        if not potential_pumps:
            logger.debug("No pumps detected in this cycle")
            return signals

        logger.info(f"Found {len(potential_pumps)} potential pump(s), analyzing...")

        # Second pass: perform detailed analysis on pumps
        for ticker in potential_pumps:
            signal = await self._analyze_pump(ticker)
            if signal:
                signals.append(signal)
                self._alerted_symbols.add(signal.symbol)
                logger.info(
                    f"✓ {signal.symbol} +{signal.price_change_percent:.2f}% "
                    f"RSI(1m)={signal.rsi_1m or 'N/A'} RSI(1h)={signal.rsi_1h or 'N/A'}"
                )

        return signals

    def _is_pump(self, ticker: dict) -> bool:
        """Check if ticker meets pump threshold.

        Args:
            ticker: Ticker data from MEXC API.

        Returns:
            True if pump threshold met.
        """
        try:
            rise_fall_rate = ticker.get("riseFallRate")
            if rise_fall_rate is None:
                return False

            price_change_percent = float(rise_fall_rate) * 100
            return price_change_percent >= self._settings.pump_threshold_percent

        except (ValueError, TypeError):
            return False

    async def _analyze_pump(self, ticker: dict) -> PumpSignal | None:
        """Perform detailed technical analysis on a pump candidate.

        Uses Binance for fast technical data, falls back to basic signal
        if coin is not on Binance.

        Args:
            ticker: Ticker data from MEXC API.

        Returns:
            PumpSignal with analysis data.
        """
        try:
            symbol = ticker.get("symbol", "")

            # Basic data from MEXC ticker
            price_change_percent = float(ticker.get("riseFallRate", 0)) * 100
            volume_24h = float(ticker.get("volume24", 0))
            current_price = float(ticker.get("lastPrice", 0))

            # Technical analysis data
            rsi_1m = None
            rsi_1h = None
            trend_4h = Trend.NEUTRAL
            trend_1d = Trend.NEUTRAL
            is_ath = False
            ath_price = None

            # Try to get technical data from Binance (fast!)
            if self._binance.has_symbol(symbol):
                logger.debug(f"Fetching Binance data for {symbol}...")
                klines_data = await self._binance.get_multi_timeframe_klines(symbol)

                rsi_1m = self._calculate_rsi_from_klines(klines_data.get("1m", []))
                rsi_1h = self._calculate_rsi_from_klines(klines_data.get("1h", []))
                trend_4h = self._determine_trend_from_klines(klines_data.get("4h", []))
                trend_1d = self._determine_trend_from_klines(klines_data.get("1d", []))
                is_ath, ath_price = self._check_ath(klines_data.get("1d", []), current_price)
            else:
                logger.debug(f"{symbol} not on Binance, skipping technical analysis")

            # Generate MEXC URL
            mexc_url = MEXCClient.get_futures_url(symbol)

            return PumpSignal(
                symbol=symbol,
                price_change_percent=price_change_percent,
                volume_24h=volume_24h,
                current_price=current_price,
                detected_at=datetime.now(timezone.utc),
                rsi_1m=rsi_1m,
                rsi_1h=rsi_1h,
                trend_4h=trend_4h,
                trend_1d=trend_1d,
                is_ath=is_ath,
                ath_price=ath_price,
                mexc_url=mexc_url,
            )

        except Exception as e:
            logger.error(f"Error analyzing pump for {ticker.get('symbol', 'unknown')}: {e}")
            return self._create_basic_signal(ticker)

    def _create_basic_signal(self, ticker: dict) -> PumpSignal | None:
        """Create a basic signal without technical analysis.

        Args:
            ticker: Ticker data from MEXC API.

        Returns:
            PumpSignal with basic data only.
        """
        try:
            symbol = ticker.get("symbol", "")
            price_change_percent = float(ticker.get("riseFallRate", 0)) * 100
            volume_24h = float(ticker.get("volume24", 0))
            current_price = float(ticker.get("lastPrice", 0))

            return PumpSignal(
                symbol=symbol,
                price_change_percent=price_change_percent,
                volume_24h=volume_24h,
                current_price=current_price,
                detected_at=datetime.now(timezone.utc),
                mexc_url=MEXCClient.get_futures_url(symbol),
            )
        except Exception as e:
            logger.error(f"Error creating basic signal: {e}")
            return None

    def _calculate_rsi_from_klines(self, klines: list[dict]) -> float | None:
        """Calculate RSI from kline data."""
        if not klines or len(klines) < 15:
            return None

        try:
            closes = [float(k.get("close", 0)) for k in klines]
            return calculate_rsi(closes, period=14)
        except (ValueError, TypeError) as e:
            logger.debug(f"RSI calculation error: {e}")
            return None

    def _determine_trend_from_klines(self, klines: list[dict]) -> Trend:
        """Determine trend from kline data."""
        if not klines or len(klines) < 20:
            return Trend.NEUTRAL

        try:
            closes = [float(k.get("close", 0)) for k in klines]
            return determine_trend(closes)
        except (ValueError, TypeError) as e:
            logger.debug(f"Trend calculation error: {e}")
            return Trend.NEUTRAL

    def _check_ath(
        self,
        klines: list[dict],
        current_price: float,
    ) -> tuple[bool, float | None]:
        """Check if current price is at all-time high (within available data)."""
        if not klines:
            return False, None

        try:
            highs = [float(k.get("high", 0)) for k in klines]
            if not highs:
                return False, None

            ath_price = max(highs)
            is_ath = current_price >= ath_price * 0.99

            return is_ath, ath_price

        except (ValueError, TypeError) as e:
            logger.debug(f"ATH check error: {e}")
            return False, None
