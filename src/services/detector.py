"""Pump detection service with technical analysis."""

from datetime import datetime, timezone
from typing import Any

from loguru import logger

from src.config import Settings
from src.models.signal import PumpSignal, ExchangeLinks, ReversalHistory
from src.services.mexc import MEXCClient
from src.services.binance import BinanceClient
from src.services.bybit import ByBitClient
from src.services.bingx import BingXClient
from src.services.chart import ChartGenerator
from src.services.tracker import PumpTracker
from src.utils.indicators import calculate_rsi, determine_trend, Trend


class PumpDetector:
    """Detects pump anomalies in MEXC futures with technical analysis."""

    # Number of 1H candles needed for chart
    # We fetch extra for indicator warmup (40) + display (60) = 100 visible after trim
    CHART_CANDLES = 140

    def __init__(
        self,
        settings: Settings,
        mexc_client: MEXCClient,
        binance_client: BinanceClient,
        bybit_client: ByBitClient,
        bingx_client: BingXClient,
        tracker: PumpTracker | None = None,
    ) -> None:
        """Initialize the pump detector.

        Args:
            settings: Application settings.
            mexc_client: MEXC API client.
            binance_client: Binance API client.
            bybit_client: ByBit API client.
            bingx_client: BingX API client.
            tracker: Pump tracker for recording and monitoring pumps.
        """
        self._settings = settings
        self._mexc = mexc_client
        self._binance = binance_client
        self._bybit = bybit_client
        self._bingx = bingx_client
        self._tracker = tracker
        self._chart_generator = ChartGenerator()
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
            return signals, tickers

        logger.info(f"Scanning {len(tickers)} futures pairs...")

        # Update tracker price cache
        if self._tracker:
            await self._tracker.update_prices(tickers)

        # First pass: identify potential pumps
        potential_pumps = []
        for ticker in tickers:
            if self._is_pump(ticker):
                symbol = ticker.get("symbol", "")
                if symbol not in self._alerted_symbols:
                    potential_pumps.append(ticker)

        if not potential_pumps:
            logger.debug("No pumps detected in this cycle")
            return signals, tickers

        logger.info(f"Found {len(potential_pumps)} potential pump(s), analyzing...")

        # Second pass: perform detailed analysis on pumps
        for ticker in potential_pumps:
            signal = await self._analyze_pump(ticker)
            if signal:
                signals.append(signal)
                self._alerted_symbols.add(signal.symbol)

                # Record pump in tracker
                if self._tracker:
                    await self._tracker.record_pump(
                        symbol=signal.symbol,
                        pump_percent=signal.price_change_percent,
                        price_at_detection=signal.current_price,
                    )

                ta_status = f"via {signal.data_source}" if signal.data_source else "no TA"
                chart_status = "with chart" if signal.chart_image else "no chart"
                history_status = f"{signal.reversal_history.total_pumps} prev" if signal.reversal_history else "new"
                logger.info(
                    f"✓ {signal.symbol} +{signal.price_change_percent:.2f}% ({ta_status}, {chart_status}, {history_status})"
                )

        return signals, tickers

    def _is_pump(self, ticker: dict) -> bool:
        """Check if ticker meets pump threshold."""
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

        Tries exchanges in order: Binance -> ByBit -> BingX
        """
        try:
            symbol = ticker.get("symbol", "")

            # Basic data from MEXC ticker
            price_change_percent = float(ticker.get("riseFallRate", 0)) * 100
            volume_24h = float(ticker.get("volume24", 0))
            current_price = float(ticker.get("lastPrice", 0))

            # Build exchange links
            links = self._build_exchange_links(symbol)

            # Technical analysis data (default empty)
            rsi_1m = None
            rsi_1h = None
            trend_1h = Trend.NEUTRAL
            trend_4h = Trend.NEUTRAL
            trend_1d = Trend.NEUTRAL
            is_ath = False
            ath_price = None
            data_source = None
            chart_image = None

            # Try to get technical data from exchanges (in priority order)
            klines_result = await self._fetch_klines_from_any_exchange(symbol)

            if klines_result:
                data_source, klines = klines_result
                rsi_1m = self._calculate_rsi_from_klines(klines.get("1m", []))
                rsi_1h = self._calculate_rsi_from_klines(klines.get("1h", []))
                trend_1h = self._determine_trend_from_klines(klines.get("1h", []))
                trend_4h = self._determine_trend_from_klines(klines.get("4h", []))
                trend_1d = self._determine_trend_from_klines(klines.get("1d", []))
                is_ath, ath_price = self._check_ath(klines.get("1d", []), current_price)

                # Generate chart from 1H klines
                klines_1h = klines.get("1h", [])
                if len(klines_1h) >= 35:
                    logger.debug(f"Generating chart for {symbol}...")
                    chart_image = self._chart_generator.generate_chart(klines_1h, symbol)

            # Get reversal history
            reversal_history = await self._get_reversal_history(symbol)

            return PumpSignal(
                symbol=symbol,
                price_change_percent=price_change_percent,
                volume_24h=volume_24h,
                current_price=current_price,
                detected_at=datetime.now(timezone.utc),
                rsi_1m=rsi_1m,
                rsi_1h=rsi_1h,
                trend_1h=trend_1h,
                trend_4h=trend_4h,
                trend_1d=trend_1d,
                is_ath=is_ath,
                ath_price=ath_price,
                links=links,
                data_source=data_source,
                chart_image=chart_image,
                reversal_history=reversal_history,
            )

        except Exception as e:
            logger.error(f"Error analyzing pump for {ticker.get('symbol', 'unknown')}: {e}")
            return None

    async def _get_reversal_history(self, symbol: str) -> ReversalHistory | None:
        """Get reversal history for a coin from tracker."""
        if not self._tracker:
            return None

        stats = await self._tracker.get_coin_stats(symbol)
        if not stats:
            return None

        last_results = await self._tracker.get_coin_last_results(symbol, 5)

        return ReversalHistory(
            total_pumps=stats.total_pumps,
            avg_time_to_50pct=stats.avg_time_to_50pct_formatted,
            pct_hit_50pct=stats.pct_hit_50pct,
            avg_time_to_100pct=stats.avg_time_to_100pct_formatted,
            pct_full_reversal=stats.pct_full_reversal,
            avg_max_drop=stats.avg_max_drop_from_high,
            last_results=last_results,
            reliability_emoji=stats.reliability_emoji,
        )

    def _build_exchange_links(self, symbol: str) -> ExchangeLinks:
        """Build exchange links for a symbol."""
        links = ExchangeLinks(mexc=MEXCClient.get_futures_url(symbol))

        if self._binance.has_symbol(symbol):
            links.binance = BinanceClient.get_futures_url(symbol)

        if self._bybit.has_symbol(symbol):
            links.bybit = ByBitClient.get_futures_url(symbol)

        if self._bingx.has_symbol(symbol):
            links.bingx = BingXClient.get_futures_url(symbol)

        return links

    async def _fetch_klines_from_any_exchange(
        self,
        symbol: str,
    ) -> tuple[str, dict[str, list[dict[str, Any]]]] | None:
        """Try to fetch klines from any available exchange.

        Tries in order: Binance (fastest) -> ByBit -> BingX
        Fetches extra 1H candles for chart generation.

        Returns:
            Tuple of (exchange_name, klines_data) or None if not available.
        """
        # Try Binance first (fastest and most reliable)
        if self._binance.has_symbol(symbol):
            logger.debug(f"Fetching {symbol} data from Binance...")
            klines = await self._fetch_klines_with_chart_data(self._binance, symbol)
            if self._has_valid_klines(klines):
                return ("Binance", klines)

        # Try ByBit second
        if self._bybit.has_symbol(symbol):
            logger.debug(f"Fetching {symbol} data from ByBit...")
            klines = await self._fetch_klines_with_chart_data(self._bybit, symbol)
            if self._has_valid_klines(klines):
                return ("ByBit", klines)

        # Try BingX last
        if self._bingx.has_symbol(symbol):
            logger.debug(f"Fetching {symbol} data from BingX...")
            klines = await self._fetch_klines_with_chart_data(self._bingx, symbol)
            if self._has_valid_klines(klines):
                return ("BingX", klines)

        logger.debug(f"{symbol} not available on any exchange for TA")
        return None

    async def _fetch_klines_with_chart_data(
        self,
        client: BinanceClient | ByBitClient | BingXClient,
        symbol: str,
    ) -> dict[str, list[dict[str, Any]]]:
        """Fetch klines with extra 1H data for chart generation."""
        # Get standard multi-timeframe data
        klines = await client.get_multi_timeframe_klines(symbol)

        # Fetch additional 1H candles for chart (100 candles)
        klines_1h_extended = await client.get_klines(symbol, "1h", self.CHART_CANDLES)
        if klines_1h_extended:
            klines["1h"] = klines_1h_extended

        return klines

    def _has_valid_klines(self, klines: dict[str, list]) -> bool:
        """Check if klines data has enough data for analysis."""
        # Need at least 15 candles in 1m or 1h for RSI
        return (
            len(klines.get("1m", [])) >= 15 or
            len(klines.get("1h", [])) >= 15
        )

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
        """Check if current price is at all-time high."""
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
