"""Core pump detection service - simplified version for watchlist coins."""

from datetime import datetime, timezone

from loguru import logger

from src_core.config import CoreSettings
from src_core.watchlist import WatchlistManager
from src.models.signal import PumpSignal, ExchangeLinks
from src.services.mexc import MEXCClient
from src.services.binance import BinanceClient
from src.services.bybit import ByBitClient
from src.services.bingx import BingXClient
from src.services.chart import ChartGenerator
from src.utils.indicators import calculate_rsi, determine_trend, Trend


class CorePumpDetector:
    """Detects pump anomalies for watchlist coins only."""

    # Number of 1H candles needed for chart
    CHART_CANDLES = 140
    
    # Weeks of data needed for 1W trend
    WEEKS_FOR_TREND = 8

    def __init__(
        self,
        settings: CoreSettings,
        watchlist: WatchlistManager,
        mexc_client: MEXCClient,
        binance_client: BinanceClient,
        bybit_client: ByBitClient,
        bingx_client: BingXClient,
    ) -> None:
        """Initialize the core pump detector.

        Args:
            settings: Core application settings.
            watchlist: Watchlist manager.
            mexc_client: MEXC API client.
            binance_client: Binance API client.
            bybit_client: ByBit API client.
            bingx_client: BingX API client.
        """
        self._settings = settings
        self._watchlist = watchlist
        self._mexc = mexc_client
        self._binance = binance_client
        self._bybit = bybit_client
        self._bingx = bingx_client
        self._chart_generator = ChartGenerator()
        self._alerted_symbols: set[str] = set()
        
        # Cached BTC trend
        self._btc_trend_1d: Trend | None = None
        self._btc_trend_1w: Trend | None = None

    def clear_alerts(self) -> None:
        """Clear the alerted symbols cache."""
        self._alerted_symbols.clear()

    async def scan_for_pumps(self) -> list[PumpSignal]:
        """Scan watchlist coins for pump anomalies.
        
        Only scans coins available on Binance for better data quality
        and to avoid overlap with main detector (which covers all MEXC pairs).

        Returns:
            List of detected pump signals.
        """
        signals: list[PumpSignal] = []

        # Get all tickers from MEXC
        tickers = await self._mexc.get_all_tickers()

        if not tickers:
            logger.warning("No tickers received from MEXC")
            return signals

        # Filter to only watchlist coins that are available on Binance
        watchlist_tickers = [
            t for t in tickers
            if self._watchlist.is_watched(t.get("symbol", ""))
            and self._binance.has_symbol(t.get("symbol", ""))
        ]

        if not watchlist_tickers:
            logger.warning("[CORE] No watchlist coins found on Binance - check if symbols are listed there")
            return signals

        logger.info(f"[CORE] Scanning {len(watchlist_tickers)}/{self._watchlist.count} watchlist coins (on Binance)...")

        # Find potential pumps in watchlist
        potential_pumps = []
        for ticker in watchlist_tickers:
            if self._is_pump(ticker):
                symbol = ticker.get("symbol", "")
                if symbol not in self._alerted_symbols:
                    potential_pumps.append(ticker)

        if not potential_pumps:
            logger.debug("[CORE] No pumps detected in watchlist this cycle")
            return signals

        logger.info(f"[CORE] Found {len(potential_pumps)} pump(s) in watchlist, analyzing...")

        # Fetch BTC trend once
        await self._update_btc_trend()

        # Analyze each pump
        for ticker in potential_pumps:
            signal = await self._analyze_pump(ticker)
            if signal:
                signals.append(signal)
                self._alerted_symbols.add(signal.symbol)
                
                ta_status = f"via {signal.data_source}" if signal.data_source else "no TA"
                chart_status = "with chart" if signal.chart_image else "no chart"
                logger.info(
                    f"[CORE] ✓ {signal.symbol} +{signal.price_change_percent:.2f}% ({ta_status}, {chart_status})"
                )

        return signals

    def _is_pump(self, ticker: dict) -> bool:
        """Check if ticker meets pump threshold and volume requirements."""
        try:
            rise_fall_rate = ticker.get("riseFallRate")
            if rise_fall_rate is None:
                return False

            price_change_percent = float(rise_fall_rate) * 100
            
            # Check pump threshold
            if price_change_percent < self._settings.core_pump_threshold_percent:
                return False
            
            # Check minimum volume
            volume_24h = float(ticker.get("volume24", 0))
            if volume_24h < self._settings.core_min_volume_usd:
                return False
            
            return True

        except (ValueError, TypeError):
            return False

    async def _analyze_pump(self, ticker: dict) -> PumpSignal | None:
        """Perform detailed technical analysis on a pump candidate."""
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

            # Try to get technical data from exchanges
            klines_result = await self._fetch_klines_from_any_exchange(symbol)

            if klines_result:
                data_source, klines = klines_result
                rsi_1m = self._calculate_rsi_from_klines(klines.get("1m", []))
                rsi_1h = self._calculate_rsi_from_klines(klines.get("1h", []))
                trend_1d = self._determine_trend_from_klines(klines.get("1d", []))
                
                # 1W trend
                klines_1w = klines.get("1w", [])
                if len(klines_1w) >= 4:
                    trend_1w = self._determine_trend_from_klines(klines_1w)
                
                is_ath, ath_price = self._check_ath(klines.get("1d", []), current_price)
                
                # Get funding rate
                funding_rate = await self._fetch_funding_rate(symbol, data_source)

                # Generate chart
                klines_1h = klines.get("1h", [])
                if len(klines_1h) >= 35:
                    chart_image = self._chart_generator.generate_chart(klines_1h, symbol)

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
                reversal_history=None,  # No history for core detector
            )

        except Exception as e:
            logger.error(f"Error analyzing pump for {ticker.get('symbol', 'unknown')}: {e}")
            return None

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
                
            logger.debug(f"BTC trend updated: 1D={self._btc_trend_1d}, 1W={self._btc_trend_1w}")
            
        except Exception as e:
            logger.warning(f"Failed to fetch BTC trend: {e}")
            self._btc_trend_1d = None
            self._btc_trend_1w = None

    async def _fetch_klines_from_any_exchange(
        self,
        symbol: str,
    ) -> tuple[str, dict[str, list[dict]]] | None:
        """Try to fetch klines from any available exchange."""
        # Try Binance first
        if self._binance.has_symbol(symbol):
            logger.debug(f"Fetching {symbol} data from Binance...")
            klines = await self._fetch_klines_with_chart_data(self._binance, symbol)
            if self._has_valid_klines(klines):
                return ("Binance", klines)

        # Try ByBit
        if self._bybit.has_symbol(symbol):
            logger.debug(f"Fetching {symbol} data from ByBit...")
            klines = await self._fetch_klines_with_chart_data(self._bybit, symbol)
            if self._has_valid_klines(klines):
                return ("ByBit", klines)

        # Try BingX
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
    ) -> dict[str, list[dict]]:
        """Fetch klines with extra 1H data for chart generation."""
        klines = await client.get_multi_timeframe_klines(symbol)
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
            logger.debug(f"Funding rate fetch error for {symbol}: {e}")
        
        return None

