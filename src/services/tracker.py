"""Pump tracking service - monitors active pumps for reversals."""

from datetime import datetime, timezone, timedelta

from loguru import logger

from src.database.db import Database
from src.database.models import PumpRecord, PumpStatus, CoinStats
from src.services.mexc import MEXCClient


class PumpTracker:
    """Tracks pump reversals and calculates statistics."""
    
    # Monitoring duration in hours
    MONITORING_HOURS = 12
    
    def __init__(self, database: Database, mexc_client: MEXCClient) -> None:
        """Initialize the tracker.
        
        Args:
            database: Database instance.
            mexc_client: MEXC client for fetching current prices.
        """
        self._db = database
        self._mexc = mexc_client
        self._active_pumps: dict[int, PumpRecord] = {}  # id -> record
        self._price_cache: dict[str, float] = {}  # symbol -> price
    
    async def load_active_pumps(self) -> None:
        """Load active pumps from database on startup."""
        pumps = await self._db.get_active_pumps()
        self._active_pumps = {p.id: p for p in pumps}
        logger.info(f"Loaded {len(self._active_pumps)} active pumps for monitoring")
    
    async def record_pump(
        self,
        symbol: str,
        pump_percent: float,
        price_at_detection: float,
    ) -> PumpRecord:
        """Record a new pump and start monitoring.
        
        Args:
            symbol: Trading pair symbol.
            pump_percent: Pump percentage.
            price_at_detection: Price when pump was detected.
            
        Returns:
            The created PumpRecord.
        """
        # Calculate pre-pump price
        price_before_pump = price_at_detection / (1 + pump_percent / 100)
        
        now = datetime.now(timezone.utc)
        monitoring_ends = now + timedelta(hours=self.MONITORING_HOURS)
        
        record = PumpRecord(
            symbol=symbol,
            detected_at=now,
            pump_percent=pump_percent,
            price_at_detection=price_at_detection,
            price_before_pump=price_before_pump,
            highest_price=price_at_detection,
            lowest_price=price_at_detection,
            last_checked_price=price_at_detection,
            status=PumpStatus.MONITORING,
            monitoring_ends_at=monitoring_ends,
        )
        
        # Save to database
        record.id = await self._db.save_pump(record)
        
        # Add to active monitoring
        self._active_pumps[record.id] = record
        
        logger.debug(f"Started monitoring {symbol} pump +{pump_percent:.1f}%")
        
        return record
    
    async def update_prices(self, tickers: list[dict]) -> None:
        """Update price cache from ticker data.
        
        Args:
            tickers: List of ticker data from MEXC.
        """
        for ticker in tickers:
            symbol = ticker.get("symbol", "")
            price = ticker.get("lastPrice")
            if symbol and price:
                self._price_cache[symbol] = float(price)
    
    async def check_active_pumps(self) -> list[PumpRecord]:
        """Check all active pumps and update their status.
        
        Returns:
            List of pumps that completed monitoring this cycle.
        """
        completed = []
        now = datetime.now(timezone.utc)
        
        for pump_id, record in list(self._active_pumps.items()):
            # Get current price
            current_price = self._price_cache.get(record.symbol)
            if current_price is None:
                continue
            
            # Update tracking
            record.last_checked_price = current_price
            record.last_checked_at = now
            
            # Update highest/lowest
            if current_price > record.highest_price:
                record.highest_price = current_price
            if current_price < record.lowest_price:
                record.lowest_price = current_price
            
            # Calculate retrace percentage
            retrace_pct = record.calculate_retrace_percent(current_price)
            
            # Calculate drop from high
            drop_from_high = record.calculate_drop_from_high(current_price)
            if drop_from_high > record.max_drop_from_high_pct:
                record.max_drop_from_high_pct = drop_from_high
            
            # Check milestones
            elapsed_seconds = (now - record.detected_at).total_seconds()
            
            if retrace_pct >= 25 and record.time_to_25pct_retrace is None:
                record.time_to_25pct_retrace = elapsed_seconds
                logger.debug(f"{record.symbol} hit 25% retrace in {elapsed_seconds/60:.1f}m")
            
            if retrace_pct >= 50 and record.time_to_50pct_retrace is None:
                record.time_to_50pct_retrace = elapsed_seconds
                logger.info(f"✓ {record.symbol} hit 50% retrace in {elapsed_seconds/60:.1f}m")
            
            if retrace_pct >= 75 and record.time_to_75pct_retrace is None:
                record.time_to_75pct_retrace = elapsed_seconds
                logger.debug(f"{record.symbol} hit 75% retrace in {elapsed_seconds/60:.1f}m")
            
            if retrace_pct >= 100 and record.time_to_100pct_retrace is None:
                record.time_to_100pct_retrace = elapsed_seconds
                record.returned_to_prepump = True
                logger.info(f"✓✓ {record.symbol} FULL REVERSAL in {elapsed_seconds/60:.1f}m")
            
            # Check if monitoring period ended
            if record.monitoring_ends_at and now >= record.monitoring_ends_at:
                # Determine final status
                if record.time_to_50pct_retrace is not None:
                    record.status = PumpStatus.SUCCESS
                elif record.time_to_25pct_retrace is not None:
                    record.status = PumpStatus.PARTIAL
                else:
                    record.status = PumpStatus.FAILED
                
                record.completed_at = now
                completed.append(record)
                
                # Remove from active monitoring
                del self._active_pumps[pump_id]
                
                logger.info(
                    f"Completed monitoring {record.symbol}: {record.status.value} "
                    f"(max drop: {record.max_drop_from_high_pct:.1f}%)"
                )
            
            # Save updated record
            await self._db.update_pump(record)
        
        return completed
    
    async def get_coin_stats(self, symbol: str) -> CoinStats | None:
        """Get statistics for a specific coin.
        
        Args:
            symbol: Trading pair symbol.
            
        Returns:
            CoinStats or None if not enough data.
        """
        stats = await self._db.get_coin_stats(symbol)
        
        # Require minimum 3 pumps for stats
        if stats and stats.total_pumps >= 3:
            return stats
        
        return None
    
    async def get_coin_last_results(self, symbol: str, n: int = 5) -> list[bool]:
        """Get last N results for a coin.
        
        Args:
            symbol: Trading pair symbol.
            n: Number of results to get.
            
        Returns:
            List of booleans (True = success, False = fail).
        """
        return await self._db.get_last_n_results(symbol, n)
    
    @property
    def active_count(self) -> int:
        """Get number of pumps currently being monitored."""
        return len(self._active_pumps)

