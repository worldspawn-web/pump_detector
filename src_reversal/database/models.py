"""Database models for reversal tracking."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ReversalStatus(Enum):
    """Status of a reversal signal."""
    
    MONITORING = "monitoring"  # Currently tracking
    SUCCESS = "success"        # Hit 50% retrace target
    FAILED = "failed"          # Went 5%+ higher than signal price
    EXPIRED = "expired"        # 12h window passed without success or failure


@dataclass
class ReversalRecord:
    """Record of a reversal signal in the database."""
    
    id: int | None
    symbol: str
    signal_price: float
    pre_pump_price: float
    pump_percent: float
    score: int
    strength: str
    timestamp: datetime
    status: ReversalStatus
    
    # Tracking data
    highest_price: float = 0.0
    lowest_price: float = 0.0
    retrace_percent: float = 0.0
    
    # Completion data
    completed_at: datetime | None = None
    
    @property
    def target_price(self) -> float:
        """Calculate 50% retrace target price."""
        pump_amount = self.signal_price - self.pre_pump_price
        return self.signal_price - (pump_amount * 0.5)
    
    @property
    def failure_price(self) -> float:
        """Calculate failure threshold (5% above signal)."""
        return self.signal_price * 1.05


@dataclass
class ReversalStats:
    """Statistics for reversal signals."""
    
    total_signals: int
    successful: int
    failed: int
    expired: int
    monitoring: int
    
    @property
    def completed(self) -> int:
        """Total completed signals."""
        return self.successful + self.failed + self.expired
    
    @property
    def success_rate(self) -> float:
        """Success rate percentage."""
        if self.completed == 0:
            return 0.0
        return (self.successful / self.completed) * 100
    
    @property
    def failure_rate(self) -> float:
        """Failure rate percentage."""
        if self.completed == 0:
            return 0.0
        return (self.failed / self.completed) * 100


@dataclass
class CoinReversalStats:
    """Statistics for a specific coin's reversal signals."""
    
    symbol: str
    total_signals: int
    successful: int
    failed: int
    avg_retrace_percent: float
    
    @property
    def success_rate(self) -> float:
        """Success rate percentage."""
        completed = self.successful + self.failed
        if completed == 0:
            return 0.0
        return (self.successful / completed) * 100

