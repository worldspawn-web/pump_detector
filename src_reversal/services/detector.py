"""Reversal signal detector."""

import asyncio
from datetime import datetime, timezone
from typing import Any

from loguru import logger

from src_reversal.config import ReversalSettings
from src_reversal.models.signal import ReversalSignal, ExchangeLinks
from src_reversal.services.mexc import MexcClient
from src_reversal.services.binance import BinanceClient
from src_reversal.services.bybit import BybitClient
from src_reversal.services.bingx import BingXClient
from src_reversal.services.scorer import ReversalScorer, SignalStrength
from src_reversal.services.chart import ChartGenerator
from src_reversal.services.tracker import ReversalTracker
from src_reversal.database.models import ReversalRecord, ReversalStatus


class ReversalDetector:
    """Detects high-probability reversal signals from pump data."""
    
    # Number of 1H candles to fetch (includes warmup for indicators)
    CHART_CANDLES = 140
    
    def __init__(
        self,
        settings: ReversalSettings,
        mexc: MexcClient,
        binance: BinanceClient,
        bybit: BybitClient,
        bingx: BingXClient,
        tracker: ReversalTracker,
    ) -> None:
        """Initialize the detector.
        
        Args:
            settings: Application settings.
            mexc: MEXC API client.
            binance: Binance API client.
            bybit: ByBit API client.
            bingx: BingX API client.
            tracker: Reversal tracker instance.
        """
        self._settings = settings
        self._mexc = mexc
        self._binance = binance
        self._bybit = bybit
        self._bingx = bingx
        self._tracker = tracker
        
        self._scorer = ReversalScorer()
        self._chart_generator = ChartGenerator()
        
        # Track already alerted symbols (prevent duplicate alerts)
        self._alerted_symbols: set[str] = set()
    
    async def load_alerted_symbols(self) -> None:
        """Load symbols currently being monitored to prevent duplicates."""
        symbols = await self._tracker.get_monitoring_symbols()
        self._alerted_symbols = symbols
        logger.info(f"Loaded {len(symbols)} symbols to skip (already monitoring)")
    
    async def scan_for_reversals(
        self,
    ) -> tuple[list[ReversalSignal], dict[str, float]]:
        """Scan for potential reversal signals.
        
        Returns:
            Tuple of (list of reversal signals, price cache for tracking).
        """
        # Get all tickers
        tickers = await self._mexc.get_all_tickers()
        
        if not tickers:
            logger.warning("No tickers received from MEXC")
            return [], {}
        
        logger.info(f"Scanning {len(tickers)} futures pairs for reversals...")
        
        # Build price cache for tracking
        price_cache: dict[str, float] = {}
        
        # Find pumps that might be reversal candidates
        candidates = []
        
        for ticker in tickers:
            symbol = ticker.get("symbol", "")
            if not symbol.endswith("_USDT"):
                continue
            
            try:
                price = float(ticker.get("lastPrice", 0))
                change_pct = float(ticker.get("riseFallRate", 0)) * 100
                volume_24h = float(ticker.get("volume24", 0))
                
                # Store price for tracking
                if price > 0:
                    price_cache[symbol] = price
                
                # Filter: minimum pump %, volume, and not already alerted
                if (
                    change_pct >= self._settings.pump_threshold_percent
                    and volume_24h >= self._settings.min_volume_usd
                    and symbol not in self._alerted_symbols
                ):
                    candidates.append({
                        "symbol": symbol,
                        "price": price,
                        "change_pct": change_pct,
                        "volume_24h": volume_24h,
                    })
            except (ValueError, TypeError):
                continue
        
        # Update tracker price cache
        self._tracker.update_price_cache(price_cache)
        
        if not candidates:
            logger.debug("No pump candidates found")
            return [], price_cache
        
        logger.info(f"Found {len(candidates)} pump candidate(s), analyzing for reversals...")
        
        # Analyze each candidate
        signals = []
        for candidate in candidates:
            signal = await self._analyze_candidate(candidate)
            if signal and signal.score.is_valid_signal():
                signals.append(signal)
                self._alerted_symbols.add(signal.symbol)
                
                # Track in database
                record = ReversalRecord(
                    id=None,
                    symbol=signal.symbol,
                    signal_price=signal.price,
                    pre_pump_price=signal.pre_pump_price,
                    pump_percent=signal.pump_percent,
                    score=signal.score.total_score,
                    strength=signal.score.strength.name,
                    timestamp=signal.timestamp,
                    status=ReversalStatus.MONITORING,
                )
                await self._tracker.add_signal(record)
        
        if signals:
            logger.info(f"Found {len(signals)} reversal signal(s)")
        
        return signals, price_cache
    
    async def _analyze_candidate(
        self,
        candidate: dict[str, Any],
    ) -> ReversalSignal | None:
        """Analyze a pump candidate for reversal signals.
        
        Args:
            candidate: Pump candidate data.
            
        Returns:
            ReversalSignal if it qualifies, None otherwise.
        """
        symbol = candidate["symbol"]
        price = candidate["price"]
        change_pct = candidate["change_pct"]
        volume_24h = candidate["volume_24h"]
        
        try:
            # Determine which exchange to use for data
            klines_1h = []
            klines_4h = []
            klines_1d = []
            klines_1m = []
            funding_rate = None
            sell_ratio = None
            data_source = "MEXC"
            
            # Try Binance first (has sell volume data)
            if self._binance.has_symbol(symbol):
                data_source = "Binance"
                klines_data = await self._binance.get_multi_timeframe_klines(symbol)
                klines_1h = klines_data.get("1h", [])
                klines_4h = klines_data.get("4h", [])
                klines_1d = klines_data.get("1d", [])
                klines_1m = klines_data.get("1m", [])
                
                # Get Binance-specific data
                funding_rate = await self._binance.get_funding_rate(symbol)
                sell_ratio = await self._binance.get_recent_sell_ratio(symbol, "1m", 10)
            
            # Try ByBit
            elif self._bybit.has_symbol(symbol):
                data_source = "ByBit"
                klines_data = await self._bybit.get_multi_timeframe_klines(symbol)
                klines_1h = klines_data.get("1h", [])
                klines_4h = klines_data.get("4h", [])
                klines_1d = klines_data.get("1d", [])
                klines_1m = klines_data.get("1m", [])
                funding_rate = await self._bybit.get_funding_rate(symbol)
            
            # Try BingX
            elif self._bingx.has_symbol(symbol):
                data_source = "BingX"
                klines_data = await self._bingx.get_multi_timeframe_klines(symbol)
                klines_1h = klines_data.get("1h", [])
                klines_4h = klines_data.get("4h", [])
                klines_1d = klines_data.get("1d", [])
                klines_1m = klines_data.get("1m", [])
                funding_rate = await self._bingx.get_funding_rate(symbol)
            
            # If no data from other exchanges, can't properly analyze
            if not klines_1h:
                logger.debug(f"Skipping {symbol}: no kline data available")
                return None
            
            # Calculate reversal score
            score = await self._scorer.calculate_score(
                symbol=symbol,
                current_price=price,
                pump_percent=change_pct,
                klines_1h=klines_1h,
                klines_4h=klines_4h,
                klines_1d=klines_1d,
                klines_1m=klines_1m,
                funding_rate=funding_rate,
                sell_ratio=sell_ratio,
            )
            
            # Skip if not a valid reversal signal
            if not score.is_valid_signal():
                logger.debug(
                    f"Skipping {symbol}: no Tier-1 signal "
                    f"(score: {score.total_score}/{score.max_possible_score})"
                )
                return None
            
            # Generate chart
            chart_image = None
            if len(klines_1h) >= 50:
                chart_image = self._chart_generator.generate_chart(klines_1h, symbol)
            
            # Build exchange links
            exchange_links = ExchangeLinks(
                mexc=MexcClient.get_futures_url(symbol),
                binance=BinanceClient.get_futures_url(symbol) if self._binance.has_symbol(symbol) else None,
                bybit=BybitClient.get_futures_url(symbol) if self._bybit.has_symbol(symbol) else None,
                bingx=BingXClient.get_futures_url(symbol) if self._bingx.has_symbol(symbol) else None,
            )
            
            # Create signal
            signal = ReversalSignal(
                symbol=symbol,
                price=price,
                pump_percent=change_pct,
                volume_24h=volume_24h,
                score=score,
                timestamp=datetime.now(timezone.utc),
                exchange_links=exchange_links,
                chart_image=chart_image,
            )
            
            strength_emoji = signal.strength_emoji
            logger.info(
                f"{strength_emoji} {symbol} +{change_pct:.2f}% "
                f"(score: {score.total_score}/{score.max_possible_score}, via {data_source})"
            )
            
            return signal
        
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return None
    
    def remove_completed_alerts(self, symbols: list[str]) -> None:
        """Remove completed symbols from alerted cache.
        
        Args:
            symbols: List of symbols to remove.
        """
        for symbol in symbols:
            self._alerted_symbols.discard(symbol)

