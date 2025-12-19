"""Anomaly pump detection service - detects ultra-fast single-candle pumps."""

from datetime import datetime, timezone
from typing import Any

from loguru import logger

from src_anomaly.config import AnomalySettings
from src.models.signal import PumpSignal, ExchangeLinks, ReversalHistory
from src.services.mexc import MEXCClient
from src.services.binance import BinanceClient
from src.services.bybit import ByBitClient
from src.services.bingx import BingXClient
from src.services.chart import ChartGenerator
from src.services.tracker import PumpTracker
from src.utils.indicators import calculate_rsi, determine_trend, Trend


class AnomalyPumpDetector:
    """Detects anomaly pumps - ultra-fast single-candle pumps with volume spikes."""

    # Number of 1H candles needed for chart
    CHART_CANDLES = 140
    
    # Weeks of data needed for 1W trend
    WEEKS_FOR_TREND = 8
    
    # Number of candles to analyze for anomaly detection
    ANOMALY_LOOKBACK_CANDLES = 24

    def __init__(
        self,
        settings: AnomalySettings,
        mexc_client: MEXCClient,
        binance_client: BinanceClient,
        bybit_client: ByBitClient,
        bingx_client: BingXClient,
        tracker: PumpTracker | None = None,
    ) -> None:
        """Initialize the anomaly pump detector.

        Args:
            settings: Anomaly application settings.
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
        
        # Cached BTC trend
        self._btc_trend_1d: Trend | None = None
        self._btc_trend_1w: Trend | None = None

    async def load_alerted_symbols(self) -> None:
        """Load currently monitored symbols from database to prevent duplicates on restart."""
        if not self._tracker:
            return
        
        active_pumps = await self._tracker._db.get_active_pumps()
        self._alerted_symbols = {p.symbol for p in active_pumps}
        
        logger.info(f"[ANOMALY] Loaded {len(self._alerted_symbols)} currently monitored symbols")

    def clear_alerts(self) -> None:
        """Clear the alerted symbols cache."""
        self._alerted_symbols.clear()

    def remove_completed_alerts(self, symbols: list[str]) -> None:
        """Remove completed symbols from alerted cache so they can pump again.
        
        Args:
            symbols: List of symbols to remove.
        """
        for symbol in symbols:
            self._alerted_symbols.discard(symbol)

    async def scan_for_pumps(self) -> list[PumpSignal]:
        """Scan all futures for anomaly pumps.

        Returns:
            List of detected anomaly pump signals with technical analysis.
        """
        signals: list[PumpSignal] = []

        tickers = await self._mexc.get_all_tickers()

        if not tickers:
            logger.warning("[ANOMALY] No tickers received from MEXC")
            return signals, tickers

        logger.info(f"[ANOMALY] Scanning {len(tickers)} futures pairs for anomalies...")

        # Update tracker price cache
        if self._tracker:
            await self._tracker.update_prices(tickers)

        # First pass: identify potential anomaly pumps
        potential_pumps = []
        for ticker in tickers:
            symbol = ticker.get("symbol", "")
            if symbol not in self._alerted_symbols:
                # Check basic pump criteria first (cheaper)
                if await self._is_anomaly_pump(ticker):
                    potential_pumps.append(ticker)

        if not potential_pumps:
            logger.debug("[ANOMALY] No anomaly pumps detected in this cycle")
            return signals, tickers

        logger.info(f"[ANOMALY] Found {len(potential_pumps)} anomaly pump(s), analyzing...")

        # Fetch BTC trend once for all signals
        await self._update_btc_trend()

        # Second pass: perform detailed analysis
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
                    f"[ANOMALY] ✓ {signal.symbol} +{signal.price_change_percent:.2f}% ({ta_status}, {chart_status}, {history_status})"
                )

        return signals, tickers

    async def _is_anomaly_pump(self, ticker: dict) -> bool:
        """Check if ticker is an anomaly pump (volume spike + price spike in single candle).
        
        Args:
            ticker: MEXC ticker data.
            
        Returns:
            True if this is an anomaly pump.
        """
        try:
            symbol = ticker.get("symbol", "")
            
            # Check basic pump threshold first
            rise_fall_rate = ticker.get("riseFallRate")
            if rise_fall_rate is None:
                return False

            price_change_percent = float(rise_fall_rate) * 100
            
            if price_change_percent < self._settings.anomaly_min_pump_percent:
                return False

            # Fetch recent 1H candles to check for anomaly
            klines = await self._fetch_klines_for_anomaly_check(symbol)
            
            if not klines or len(klines) < self.ANOMALY_LOOKBACK_CANDLES + 1:
                logger.debug(f"[ANOMALY] Not enough candles for {symbol} anomaly check")
                return False

            # Check for volume and candle body anomaly
            return self._check_anomaly_conditions(klines)

        except Exception as e:
            logger.debug(f"[ANOMALY] Error checking anomaly for {ticker.get('symbol', 'unknown')}: {e}")
            return False

    async def _fetch_klines_for_anomaly_check(self, symbol: str) -> list[dict] | None:
        """Fetch recent 1H candles for anomaly detection.
        
        Args:
            symbol: Symbol to fetch.
            
        Returns:
            List of kline data or None.
        """
        # Try exchanges in priority order
        for client in [self._binance, self._bybit, self._bingx]:
            if client.has_symbol(symbol):
                klines = await client.get_klines(symbol, "1h", self.ANOMALY_LOOKBACK_CANDLES + 1)
                if klines:
                    return klines
        
        return None

    def _check_anomaly_conditions(self, klines: list[dict]) -> bool:
        """Check if current candle is an anomaly compared to recent candles.
        
        Args:
            klines: List of kline data (oldest to newest).
            
        Returns:
            True if anomaly conditions are met.
        """
        try:
            # Current candle (last one)
            current_candle = klines[-1]
            
            # Historical candles (excluding current)
            historical_candles = klines[:-1]
            
            # Extract current candle data
            current_volume = float(current_candle.get("volume", 0))
            current_open = float(current_candle.get("open", 0))
            current_close = float(current_candle.get("close", 0))
            current_body = abs(current_close - current_open)
            
            # Calculate averages from historical candles
            historical_volumes = [float(k.get("volume", 0)) for k in historical_candles]
            historical_bodies = [
                abs(float(k.get("close", 0)) - float(k.get("open", 0)))
                for k in historical_candles
            ]
            
            avg_volume = sum(historical_volumes) / len(historical_volumes) if historical_volumes else 1
            avg_body = sum(historical_bodies) / len(historical_bodies) if historical_bodies else 1
            
            # Avoid division by zero
            if avg_volume == 0 or avg_body == 0:
                return False
            
            # Calculate spike ratios
            volume_spike_ratio = current_volume / avg_volume
            body_spike_ratio = current_body / avg_body
            
            # Check if both conditions are met
            volume_condition = volume_spike_ratio >= self._settings.anomaly_min_volume_spike
            body_condition = body_spike_ratio >= self._settings.anomaly_min_candle_body
            
            if volume_condition and body_condition:
                logger.debug(
                    f"[ANOMALY] Spike detected: volume {volume_spike_ratio:.1f}x, body {body_spike_ratio:.1f}x"
                )
                return True
            
            return False

        except Exception as e:
            logger.debug(f"[ANOMALY] Error checking anomaly conditions: {e}")
            return False

    async def _analyze_pump(self, ticker: dict) -> PumpSignal | None:
        """Perform detailed technical analysis on an anomaly pump.

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
            trend_1d = Trend.NEUTRAL
            trend_1w = None
            funding_rate = None
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
                trend_1d = self._determine_trend_from_klines(klines.get("1d", []))
                
                # 1W trend - only if we have at least 4 weeks of data
                klines_1w = klines.get("1w", [])
                if len(klines_1w) >= 4:
                    trend_1w = self._determine_trend_from_klines(klines_1w)
                
                is_ath, ath_price = self._check_ath(klines.get("1d", []), current_price)
                
                # Get funding rate from the same exchange
                funding_rate = await self._fetch_funding_rate(symbol, data_source)

                # Generate chart from 1H klines
                klines_1h = klines.get("1h", [])
                if len(klines_1h) >= 35:
                    logger.debug(f"[ANOMALY] Generating chart for {symbol}...")
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
                trend_1d=trend_1d,
                trend_1w=trend_1w,
                btc_trend_1d=self._btc_trend_1d,
                btc_trend_1w=self._btc_trend_1w,
                funding_rate=funding_rate,
                is_ath=is_ath,
                ath_price=ath_price,
                links=links,
                data_source=data_source,
                chart_image=chart_image,
                reversal_history=reversal_history,
            )

        except Exception as e:
            logger.error(f"[ANOMALY] Error analyzing pump for {ticker.get('symbol', 'unknown')}: {e}")
            return None

    async def _get_reversal_history(self, symbol: str) -> ReversalHistory | None:
        """Get reversal history for a coin from tracker."""
        if not self._tracker:
            return None

        stats = await self._tracker.get_coin_stats(
            symbol,
            min_pumps=self._settings.min_pumps_for_history,
        )
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

    async def _update_btc_trend(self) -> None:
        """Fetch BTC klines and update cached BTC trend."""
        try:
            btc_symbol = "BTCUSDT"
            
            klines_1d = await self._binance.get_klines(btc_symbol, "1d", 100)
            klines_1w = await self._binance.get_klines(btc_symbol, "1w", 8)
            
            if klines_1d and len(klines_1d) >= 20:
                self._btc_trend_1d = self._determine_trend_from_klines(klines_1d)
            else:
                self._btc_trend_1d = None
                
            if klines_1w and len(klines_1w) >= 4:
                self._btc_trend_1w = self._determine_trend_from_klines(klines_1w)
            else:
                self._btc_trend_1w = None
                
            logger.debug(f"[ANOMALY] BTC trend updated: 1D={self._btc_trend_1d}, 1W={self._btc_trend_1w}")
            
        except Exception as e:
            logger.warning(f"[ANOMALY] Failed to fetch BTC trend: {e}")
            self._btc_trend_1d = None
            self._btc_trend_1w = None

    async def _fetch_klines_from_any_exchange(
        self,
        symbol: str,
    ) -> tuple[str, dict[str, list[dict[str, Any]]]] | None:
        """Try to fetch klines from any available exchange."""
        # Try Binance first (fastest and most reliable)
        if self._binance.has_symbol(symbol):
            logger.debug(f"[ANOMALY] Fetching {symbol} data from Binance...")
            klines = await self._fetch_klines_with_chart_data(self._binance, symbol)
            if self._has_valid_klines(klines):
                return ("Binance", klines)

        # Try ByBit second
        if self._bybit.has_symbol(symbol):
            logger.debug(f"[ANOMALY] Fetching {symbol} data from ByBit...")
            klines = await self._fetch_klines_with_chart_data(self._bybit, symbol)
            if self._has_valid_klines(klines):
                return ("ByBit", klines)

        # Try BingX last
        if self._bingx.has_symbol(symbol):
            logger.debug(f"[ANOMALY] Fetching {symbol} data from BingX...")
            klines = await self._fetch_klines_with_chart_data(self._bingx, symbol)
            if self._has_valid_klines(klines):
                return ("BingX", klines)

        logger.debug(f"[ANOMALY] {symbol} not available on any exchange for TA")
        return None

    async def _fetch_klines_with_chart_data(
        self,
        client: BinanceClient | ByBitClient | BingXClient,
        symbol: str,
    ) -> dict[str, list[dict[str, Any]]]:
        """Fetch klines with extra 1H data for chart generation."""
        # Get standard multi-timeframe data
        klines = await client.get_multi_timeframe_klines(symbol)

        # Fetch additional 1H candles for chart
        klines_1h_extended = await client.get_klines(symbol, "1h", self.CHART_CANDLES)
        if klines_1h_extended:
            klines["1h"] = klines_1h_extended

        return klines

    def _has_valid_klines(self, klines: dict[str, list]) -> bool:
        """Check if klines data has enough data for analysis."""
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
            logger.debug(f"[ANOMALY] RSI calculation error: {e}")
            return None

    def _determine_trend_from_klines(self, klines: list[dict]) -> Trend:
        """Determine trend from kline data."""
        if not klines or len(klines) < 20:
            return Trend.NEUTRAL

        try:
            closes = [float(k.get("close", 0)) for k in klines]
            return determine_trend(closes)
        except (ValueError, TypeError) as e:
            logger.debug(f"[ANOMALY] Trend calculation error: {e}")
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
            logger.debug(f"[ANOMALY] ATH check error: {e}")
            return False, None

    async def _fetch_funding_rate(
        self,
        symbol: str,
        data_source: str,
    ) -> float | None:
        """Fetch funding rate from the specified exchange."""
        try:
            if data_source == "Binance":
                return await self._binance.get_funding_rate(symbol)
            elif data_source == "ByBit":
                return await self._bybit.get_funding_rate(symbol)
            elif data_source == "BingX":
                return await self._bingx.get_funding_rate(symbol)
        except Exception as e:
            logger.debug(f"[ANOMALY] Funding rate fetch error for {symbol}: {e}")
        
        return None

