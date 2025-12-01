"""Reversal signal tracking and monitoring."""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any

from loguru import logger

from src_reversal.database.db import ReversalDatabase
from src_reversal.database.models import ReversalRecord, ReversalStatus, ReversalStats


class ReversalTracker:
    """Tracks and monitors reversal signals for success/failure."""
    
    def __init__(
        self,
        database: ReversalDatabase,
        monitoring_hours: int = 12,
        success_retrace_pct: float = 50.0,
        failure_increase_pct: float = 5.0,
    ) -> None:
        """Initialize the tracker.
        
        Args:
            database: Database instance.
            monitoring_hours: Hours to monitor each signal.
            success_retrace_pct: Percentage retrace for success.
            failure_increase_pct: Percentage increase for failure.
        """
        self._db = database
        self._monitoring_hours = monitoring_hours
        self._success_retrace_pct = success_retrace_pct
        self._failure_increase_pct = failure_increase_pct
        
        # Cache of active signals for fast lookup
        self._active_signals: dict[int, ReversalRecord] = {}
        # Price cache for monitoring
        self._price_cache: dict[str, float] = {}
    
    async def load_active_signals(self) -> int:
        """Load active signals from database on startup.
        
        Returns:
            Number of signals loaded.
        """
        signals = await self._db.get_monitoring_signals()
        
        for signal in signals:
            self._active_signals[signal.id] = signal
        
        logger.info(f"Loaded {len(signals)} active reversal signals to monitor")
        return len(signals)
    
    async def add_signal(self, record: ReversalRecord) -> int:
        """Add a new signal to tracking.
        
        Args:
            record: Reversal record to track.
            
        Returns:
            Database ID of the signal.
        """
        signal_id = await self._db.add_signal(record)
        record.id = signal_id
        self._active_signals[signal_id] = record
        
        logger.info(
            f"Tracking reversal signal: {record.symbol} @ ${record.signal_price:.6f} "
            f"(target: ${record.target_price:.6f}, failure: ${record.failure_price:.6f})"
        )
        
        return signal_id
    
    def update_price_cache(self, prices: dict[str, float]) -> None:
        """Update price cache with current prices.
        
        Args:
            prices: Dict mapping symbol to current price.
        """
        self._price_cache.update(prices)
    
    async def check_signals(self) -> list[ReversalRecord]:
        """Check all active signals and update their status.
        
        Returns:
            List of completed (success/failed/expired) signals.
        """
        completed = []
        now = datetime.now(timezone.utc)
        
        for signal_id, signal in list(self._active_signals.items()):
            current_price = self._price_cache.get(signal.symbol)
            
            if current_price is None:
                continue
            
            # Update highest/lowest prices
            new_highest = max(signal.highest_price, current_price)
            new_lowest = min(signal.lowest_price, current_price)
            
            # Calculate current retrace from signal price
            if signal.signal_price > signal.pre_pump_price:
                pump_amount = signal.signal_price - signal.pre_pump_price
                if pump_amount > 0:
                    retrace = (signal.signal_price - current_price) / pump_amount * 100
                    retrace = max(0, min(100, retrace))  # Clamp 0-100
                else:
                    retrace = 0
            else:
                retrace = 0
            
            # Check for success (50% retrace)
            if retrace >= self._success_retrace_pct:
                signal.status = ReversalStatus.SUCCESS
                signal.retrace_percent = retrace
                completed.append(signal)
                
                await self._db.update_signal(
                    signal_id,
                    status=ReversalStatus.SUCCESS,
                    highest_price=new_highest,
                    lowest_price=new_lowest,
                    retrace_percent=retrace,
                )
                
                del self._active_signals[signal_id]
                logger.info(
                    f"✅ SUCCESS: {signal.symbol} retraced {retrace:.1f}% "
                    f"(price: ${current_price:.6f})"
                )
                continue
            
            # Check for failure (price went 5% higher)
            increase_pct = (current_price - signal.signal_price) / signal.signal_price * 100
            if increase_pct >= self._failure_increase_pct:
                signal.status = ReversalStatus.FAILED
                signal.retrace_percent = retrace
                completed.append(signal)
                
                await self._db.update_signal(
                    signal_id,
                    status=ReversalStatus.FAILED,
                    highest_price=new_highest,
                    lowest_price=new_lowest,
                    retrace_percent=retrace,
                )
                
                del self._active_signals[signal_id]
                logger.info(
                    f"❌ FAILED: {signal.symbol} went +{increase_pct:.1f}% higher "
                    f"(price: ${current_price:.6f})"
                )
                continue
            
            # Check for expiration (12 hours)
            elapsed = now - signal.timestamp
            if elapsed > timedelta(hours=self._monitoring_hours):
                signal.status = ReversalStatus.EXPIRED
                signal.retrace_percent = retrace
                completed.append(signal)
                
                await self._db.update_signal(
                    signal_id,
                    status=ReversalStatus.EXPIRED,
                    highest_price=new_highest,
                    lowest_price=new_lowest,
                    retrace_percent=retrace,
                )
                
                del self._active_signals[signal_id]
                logger.info(
                    f"⏰ EXPIRED: {signal.symbol} after {self._monitoring_hours}h "
                    f"(retrace: {retrace:.1f}%)"
                )
                continue
            
            # Update tracking data
            if new_highest != signal.highest_price or new_lowest != signal.lowest_price:
                await self._db.update_signal(
                    signal_id,
                    highest_price=new_highest,
                    lowest_price=new_lowest,
                    retrace_percent=retrace,
                )
                signal.highest_price = new_highest
                signal.lowest_price = new_lowest
                signal.retrace_percent = retrace
        
        return completed
    
    @property
    def active_count(self) -> int:
        """Number of signals currently being monitored."""
        return len(self._active_signals)
    
    async def get_global_stats(self) -> ReversalStats:
        """Get global statistics."""
        return await self._db.get_global_stats()
    
    async def get_today_stats(self) -> ReversalStats:
        """Get today's statistics."""
        return await self._db.get_today_stats()
    
    async def get_monitoring_symbols(self) -> set[str]:
        """Get symbols currently being monitored."""
        return await self._db.get_monitoring_symbols()

