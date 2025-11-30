"""Database models for pump tracking."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class PumpStatus(Enum):
    """Status of a pump record."""
    MONITORING = "monitoring"
    SUCCESS = "success"  # Hit 50% retrace
    PARTIAL = "partial"  # Some retrace but not 50%
    FAILED = "failed"    # No significant retrace


@dataclass
class PumpRecord:
    """Record of a detected pump and its outcome."""
    
    id: int | None = None
    symbol: str = ""
    detected_at: datetime = field(default_factory=datetime.utcnow)
    pump_percent: float = 0.0
    
    # Prices
    price_at_detection: float = 0.0
    price_before_pump: float = 0.0  # Calculated from pump %
    
    # Tracking (updated during monitoring)
    highest_price: float = 0.0
    lowest_price: float = 0.0
    last_checked_price: float = 0.0
    last_checked_at: datetime | None = None
    
    # Option A: Time milestones (seconds, None if not reached)
    time_to_25pct_retrace: float | None = None
    time_to_50pct_retrace: float | None = None
    time_to_75pct_retrace: float | None = None
    time_to_100pct_retrace: float | None = None
    
    # Option B: Max drop from high
    max_drop_from_high_pct: float = 0.0
    
    # Option C: Full reversal
    returned_to_prepump: bool = False
    
    # Status
    status: PumpStatus = PumpStatus.MONITORING
    monitoring_ends_at: datetime | None = None
    completed_at: datetime | None = None
    
    def calculate_retrace_percent(self, current_price: float) -> float:
        """Calculate how much the price has retraced from pump.
        
        Returns percentage of pump that has been retraced (0-100+).
        100% means price returned to pre-pump level.
        """
        if self.price_at_detection <= self.price_before_pump:
            return 0.0
        
        pump_amount = self.price_at_detection - self.price_before_pump
        retrace_amount = self.price_at_detection - current_price
        
        if pump_amount == 0:
            return 0.0
        
        return (retrace_amount / pump_amount) * 100
    
    def calculate_drop_from_high(self, current_price: float) -> float:
        """Calculate percentage drop from highest price."""
        if self.highest_price == 0:
            return 0.0
        
        return ((self.highest_price - current_price) / self.highest_price) * 100


@dataclass
class CoinStats:
    """Aggregated statistics for a coin."""
    
    symbol: str = ""
    total_pumps: int = 0
    
    # Option A: Retrace timing stats
    pumps_hit_25pct: int = 0
    pumps_hit_50pct: int = 0
    pumps_hit_75pct: int = 0
    pumps_hit_100pct: int = 0
    avg_time_to_50pct_seconds: float | None = None
    avg_time_to_100pct_seconds: float | None = None
    
    # Option B: Drop from high stats
    avg_max_drop_from_high: float = 0.0
    
    # Option C: Full reversal stats
    full_reversal_count: int = 0
    
    # Computed
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def pct_hit_50pct(self) -> float:
        """Percentage of pumps that hit 50% retrace."""
        if self.total_pumps == 0:
            return 0.0
        return (self.pumps_hit_50pct / self.total_pumps) * 100
    
    @property
    def pct_full_reversal(self) -> float:
        """Percentage of pumps with full reversal."""
        if self.total_pumps == 0:
            return 0.0
        return (self.full_reversal_count / self.total_pumps) * 100
    
    @property
    def reliability_emoji(self) -> str:
        """Get reliability emoji based on 50% retrace rate."""
        pct = self.pct_hit_50pct
        if pct >= 70:
            return "⚡⚡⚡"
        elif pct >= 40:
            return "🌙"
        else:
            return "❗"
    
    @property
    def avg_time_to_50pct_formatted(self) -> str:
        """Format average time to 50% retrace."""
        if self.avg_time_to_50pct_seconds is None:
            return "N/A"
        
        hours = self.avg_time_to_50pct_seconds / 3600
        if hours < 1:
            minutes = self.avg_time_to_50pct_seconds / 60
            return f"{minutes:.0f}m"
        return f"{hours:.1f}h"
    
    @property
    def avg_time_to_100pct_formatted(self) -> str:
        """Format average time to full reversal."""
        if self.avg_time_to_100pct_seconds is None:
            return "N/A"
        
        hours = self.avg_time_to_100pct_seconds / 3600
        if hours < 1:
            minutes = self.avg_time_to_100pct_seconds / 60
            return f"{minutes:.0f}m"
        return f"{hours:.1f}h"


@dataclass 
class GlobalStats:
    """Global statistics across all coins."""
    
    total_pumps: int = 0
    active_monitoring: int = 0
    
    # Success rates
    total_hit_50pct: int = 0
    total_full_reversal: int = 0
    avg_time_to_50pct_seconds: float | None = None
    
    # Today's stats
    today_pumps: int = 0
    today_hit_50pct: int = 0
    
    # Top/bottom performers
    top_coins: list[tuple[str, float, int]] = field(default_factory=list)  # (symbol, rate, count)
    worst_coins: list[tuple[str, float, int]] = field(default_factory=list)
    
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def pct_hit_50pct(self) -> float:
        """Overall 50% retrace rate."""
        completed = self.total_pumps - self.active_monitoring
        if completed == 0:
            return 0.0
        return (self.total_hit_50pct / completed) * 100
    
    @property
    def pct_full_reversal(self) -> float:
        """Overall full reversal rate."""
        completed = self.total_pumps - self.active_monitoring
        if completed == 0:
            return 0.0
        return (self.total_full_reversal / completed) * 100
    
    @property
    def today_success_rate(self) -> float:
        """Today's success rate."""
        if self.today_pumps == 0:
            return 0.0
        return (self.today_hit_50pct / self.today_pumps) * 100

