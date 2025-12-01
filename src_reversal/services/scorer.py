"""Confluence scoring system for reversal probability."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loguru import logger

from src_reversal.utils.indicators import (
    calculate_rsi,
    calculate_macd,
    calculate_trend,
    is_macd_bearish_cross,
    Trend,
)
from src_reversal.utils.levels import (
    detect_support_resistance,
    find_nearest_resistance,
    LevelType,
    PriceLevel,
)


class SignalStrength(Enum):
    """Signal strength level."""
    
    STRONG = 3  # ⚡⚡⚡
    MEDIUM = 2  # ⚡⚡
    WEAK = 1    # ⚡
    NONE = 0    # Not a reversal signal


@dataclass
class ScoringFactor:
    """Individual scoring factor result."""
    
    name: str
    score: int
    max_score: int
    triggered: bool
    value: Any = None
    description: str = ""


@dataclass
class ReversalScore:
    """Complete reversal scoring result."""
    
    total_score: int
    max_possible_score: int
    strength: SignalStrength
    factors: list[ScoringFactor] = field(default_factory=list)
    has_tier1_signal: bool = False
    warnings: list[str] = field(default_factory=list)
    
    # Key values for display
    nearest_resistance: PriceLevel | None = None
    rsi_1m: float | None = None
    rsi_1h: float | None = None
    funding_rate: float | None = None
    sell_ratio: float | None = None
    macd_bearish: bool = False
    volume_ratio: float | None = None
    
    @property
    def score_percent(self) -> float:
        """Get score as percentage."""
        if self.max_possible_score == 0:
            return 0
        return (self.total_score / self.max_possible_score) * 100
    
    def is_valid_signal(self) -> bool:
        """Check if this qualifies as a reversal signal."""
        return self.has_tier1_signal and self.strength != SignalStrength.NONE


class ReversalScorer:
    """Calculates confluence score for reversal probability."""
    
    # CORE REQUIREMENT (must have)
    CORE_HTF_RESISTANCE = 50     # Near high timeframe resistance - MANDATORY
    
    # Confluence factors (additional confirmation)
    FACTOR_SELL_VOLUME = 35      # High sell volume ratio (>65%)
    FACTOR_FUNDING_HIGH = 30     # High positive funding (0.2-1%)
    FACTOR_FUNDING_EXTREME = 40  # Extreme positive funding (>1%)
    FACTOR_RSI_HIGH = 25         # RSI > 70 on multiple timeframes
    FACTOR_MACD_BEARISH = 25     # MACD bearish cross
    FACTOR_VOLUME_SPIKE = 15     # Volume much higher than average
    FACTOR_UPPER_WICK = 10       # Long upper wicks (selling pressure)
    
    # Thresholds
    RESISTANCE_DISTANCE_PCT = 1.5   # Max distance to resistance (%) - tighter
    RSI_OVERBOUGHT = 70             # Lowered from 80 for more signals with resistance
    SELL_VOLUME_THRESHOLD = 0.60    # 60% sell volume
    FUNDING_HIGH_THRESHOLD = 0.1    # 0.1%
    FUNDING_EXTREME_THRESHOLD = 0.5 # 0.5%
    FUNDING_DANGER_THRESHOLD = -0.05 # Negative funding warning
    VOLUME_SPIKE_MULTIPLIER = 2.5   # 2.5x average volume
    
    # Minimum confluence required (besides resistance)
    MIN_CONFLUENCE_SCORE = 35  # Need at least this many points from other factors
    
    # Strength thresholds (percentage of max score)
    STRONG_THRESHOLD = 65    # 65%+ = Strong signal (⚡⚡⚡)
    MEDIUM_THRESHOLD = 45    # 45-65% = Medium signal (⚡⚡)
    WEAK_THRESHOLD = 30      # 30-45% = Weak signal (⚡)
    
    def __init__(self) -> None:
        """Initialize the scorer."""
        pass
    
    async def calculate_score(
        self,
        symbol: str,
        current_price: float,
        pump_percent: float,
        klines_1h: list[dict],
        klines_4h: list[dict] | None = None,
        klines_1d: list[dict] | None = None,
        klines_1m: list[dict] | None = None,
        funding_rate: float | None = None,
        sell_ratio: float | None = None,
    ) -> ReversalScore:
        """Calculate confluence score for reversal probability.
        
        Args:
            symbol: Trading pair symbol.
            current_price: Current price.
            pump_percent: Pump percentage.
            klines_1h: 1-hour kline data.
            klines_4h: 4-hour kline data (optional).
            klines_1d: Daily kline data (optional).
            klines_1m: 1-minute kline data (optional).
            funding_rate: Current funding rate percentage (optional).
            sell_ratio: Sell volume ratio 0-1 (optional).
            
        Returns:
            ReversalScore with all factors.
        """
        factors = []
        warnings = []
        has_resistance = False  # CORE requirement
        confluence_score = 0    # Score from other factors
        
        # Calculate max possible score based on available data
        max_score = self.CORE_HTF_RESISTANCE + self.FACTOR_RSI_HIGH + self.FACTOR_MACD_BEARISH
        
        if sell_ratio is not None:
            max_score += self.FACTOR_SELL_VOLUME
        if funding_rate is not None:
            max_score += self.FACTOR_FUNDING_EXTREME  # Use max possible
        if klines_1m:
            max_score += self.FACTOR_VOLUME_SPIKE + self.FACTOR_UPPER_WICK
        
        # === CORE REQUIREMENT: HTF Resistance ===
        # Without nearby resistance, NO signal will be sent
        nearest_resistance = None
        if klines_4h or klines_1d:
            nearest_resistance = self._check_htf_resistance(
                current_price,
                klines_4h or [],
                klines_1d or [],
            )
            
            if nearest_resistance:
                has_resistance = True
                distance_pct = (nearest_resistance.price - current_price) / current_price * 100
                factors.append(ScoringFactor(
                    name="HTF Resistance",
                    score=self.CORE_HTF_RESISTANCE,
                    max_score=self.CORE_HTF_RESISTANCE,
                    triggered=True,
                    value=nearest_resistance.price,
                    description=f"Within {distance_pct:.1f}% of {nearest_resistance.timeframe} resistance",
                ))
            else:
                factors.append(ScoringFactor(
                    name="HTF Resistance",
                    score=0,
                    max_score=self.CORE_HTF_RESISTANCE,
                    triggered=False,
                    description="No nearby resistance - signal rejected",
                ))
        
        # === CONFLUENCE: Sell Volume Ratio ===
        if sell_ratio is not None:
            if sell_ratio >= self.SELL_VOLUME_THRESHOLD:
                confluence_score += self.FACTOR_SELL_VOLUME
                factors.append(ScoringFactor(
                    name="Sell Volume",
                    score=self.FACTOR_SELL_VOLUME,
                    max_score=self.FACTOR_SELL_VOLUME,
                    triggered=True,
                    value=sell_ratio,
                    description=f"{sell_ratio*100:.0f}% sell volume",
                ))
            else:
                factors.append(ScoringFactor(
                    name="Sell Volume",
                    score=0,
                    max_score=self.FACTOR_SELL_VOLUME,
                    triggered=False,
                    value=sell_ratio,
                    description=f"{sell_ratio*100:.0f}% sell (need {self.SELL_VOLUME_THRESHOLD*100:.0f}%+)",
                ))
        
        # === CONFLUENCE: Funding Rate ===
        if funding_rate is not None:
            if funding_rate >= self.FUNDING_EXTREME_THRESHOLD:
                # Extreme positive funding - very bullish for shorting
                confluence_score += self.FACTOR_FUNDING_EXTREME
                factors.append(ScoringFactor(
                    name="Funding Rate",
                    score=self.FACTOR_FUNDING_EXTREME,
                    max_score=self.FACTOR_FUNDING_EXTREME,
                    triggered=True,
                    value=funding_rate,
                    description=f"Extreme +{funding_rate:.3f}% (longs pay heavily)",
                ))
            elif funding_rate >= self.FUNDING_HIGH_THRESHOLD:
                # High positive funding
                confluence_score += self.FACTOR_FUNDING_HIGH
                factors.append(ScoringFactor(
                    name="Funding Rate",
                    score=self.FACTOR_FUNDING_HIGH,
                    max_score=self.FACTOR_FUNDING_EXTREME,
                    triggered=True,
                    value=funding_rate,
                    description=f"High +{funding_rate:.3f}%",
                ))
            elif funding_rate < self.FUNDING_DANGER_THRESHOLD:
                # Negative funding - WARNING
                warnings.append(f"⚠️ Negative funding {funding_rate:.3f}% - short squeeze risk")
                factors.append(ScoringFactor(
                    name="Funding Rate",
                    score=0,
                    max_score=self.FACTOR_FUNDING_EXTREME,
                    triggered=False,
                    value=funding_rate,
                    description=f"Negative {funding_rate:.3f}% - squeeze risk!",
                ))
            else:
                factors.append(ScoringFactor(
                    name="Funding Rate",
                    score=0,
                    max_score=self.FACTOR_FUNDING_EXTREME,
                    triggered=False,
                    value=funding_rate,
                    description=f"Neutral {funding_rate:.3f}%",
                ))
        
        # === CONFLUENCE: RSI ===
        rsi_1h = None
        rsi_1m = None
        rsi_score = 0
        
        if klines_1h:
            closes_1h = [k["close"] for k in klines_1h]
            rsi_1h = calculate_rsi(closes_1h)
        
        if klines_1m:
            closes_1m = [k["close"] for k in klines_1m]
            rsi_1m = calculate_rsi(closes_1m)
        
        # Check for valid RSI (not None and not NaN)
        rsi_1m_valid = rsi_1m is not None and rsi_1m == rsi_1m  # NaN != NaN
        rsi_1h_valid = rsi_1h is not None and rsi_1h == rsi_1h
        
        if rsi_1h_valid and rsi_1h >= self.RSI_OVERBOUGHT:
            rsi_score += 15
        if rsi_1m_valid and rsi_1m >= self.RSI_OVERBOUGHT:
            rsi_score += 10
        
        confluence_score += rsi_score
        
        rsi_1m_str = f"{rsi_1m:.0f}" if rsi_1m_valid else "N/A"
        rsi_1h_str = f"{rsi_1h:.0f}" if rsi_1h_valid else "N/A"
        
        factors.append(ScoringFactor(
            name="RSI",
            score=rsi_score,
            max_score=self.FACTOR_RSI_HIGH,
            triggered=rsi_score > 0,
            value=(rsi_1m, rsi_1h),
            description=f"1M: {rsi_1m_str} | 1H: {rsi_1h_str}",
        ))
        
        # === CONFLUENCE: MACD Bearish Cross ===
        macd_bearish = False
        if klines_1h:
            closes_1h = [k["close"] for k in klines_1h]
            macd_line, signal_line, _ = calculate_macd(closes_1h)
            macd_bearish = is_macd_bearish_cross(macd_line, signal_line)
        
        if macd_bearish:
            confluence_score += self.FACTOR_MACD_BEARISH
        
        factors.append(ScoringFactor(
            name="MACD",
            score=self.FACTOR_MACD_BEARISH if macd_bearish else 0,
            max_score=self.FACTOR_MACD_BEARISH,
            triggered=macd_bearish,
            description="Bearish cross ✓" if macd_bearish else "No bearish cross",
        ))
        
        # === CONFLUENCE: Volume Spike ===
        volume_ratio = None
        if klines_1m and len(klines_1m) >= 20:
            recent_vol = sum(k.get("volume", k.get("vol", 0)) for k in klines_1m[-5:]) / 5
            avg_vol = sum(k.get("volume", k.get("vol", 0)) for k in klines_1m[:-5]) / max(len(klines_1m) - 5, 1)
            
            if avg_vol > 0:
                volume_ratio = recent_vol / avg_vol
                
                if volume_ratio >= self.VOLUME_SPIKE_MULTIPLIER:
                    confluence_score += self.FACTOR_VOLUME_SPIKE
                    factors.append(ScoringFactor(
                        name="Volume Spike",
                        score=self.FACTOR_VOLUME_SPIKE,
                        max_score=self.FACTOR_VOLUME_SPIKE,
                        triggered=True,
                        value=volume_ratio,
                        description=f"{volume_ratio:.1f}x average volume",
                    ))
                else:
                    factors.append(ScoringFactor(
                        name="Volume Spike",
                        score=0,
                        max_score=self.FACTOR_VOLUME_SPIKE,
                        triggered=False,
                        value=volume_ratio,
                        description=f"{volume_ratio:.1f}x avg (need {self.VOLUME_SPIKE_MULTIPLIER}x)",
                    ))
        
        # === CONFLUENCE: Upper Wick Analysis ===
        if klines_1m and len(klines_1m) >= 5:
            wick_score = self._analyze_upper_wicks(klines_1m[-10:])
            if wick_score > 0:
                confluence_score += wick_score
            factors.append(ScoringFactor(
                name="Upper Wicks",
                score=wick_score,
                max_score=self.FACTOR_UPPER_WICK,
                triggered=wick_score > 0,
                description="Selling pressure detected" if wick_score > 0 else "Normal wicks",
            ))
        
        # Calculate total score
        total_score = sum(f.score for f in factors)
        
        # Determine strength
        # CORE REQUIREMENT: Must have resistance nearby
        # CONFLUENCE REQUIREMENT: Must have minimum additional factors
        score_pct = (total_score / max_score * 100) if max_score > 0 else 0
        
        if not has_resistance:
            # No resistance = no signal, period
            strength = SignalStrength.NONE
        elif confluence_score < self.MIN_CONFLUENCE_SCORE:
            # Has resistance but not enough confluence
            strength = SignalStrength.NONE
        elif score_pct >= self.STRONG_THRESHOLD:
            strength = SignalStrength.STRONG
        elif score_pct >= self.MEDIUM_THRESHOLD:
            strength = SignalStrength.MEDIUM
        elif score_pct >= self.WEAK_THRESHOLD:
            strength = SignalStrength.WEAK
        else:
            strength = SignalStrength.NONE
        
        # Log rejection reasons
        if has_resistance and confluence_score < self.MIN_CONFLUENCE_SCORE:
            logger.debug(
                f"{symbol}: Has resistance but confluence too low "
                f"({confluence_score}/{self.MIN_CONFLUENCE_SCORE} needed)"
            )
        
        return ReversalScore(
            total_score=total_score,
            max_possible_score=max_score,
            strength=strength,
            factors=factors,
            has_tier1_signal=has_resistance and confluence_score >= self.MIN_CONFLUENCE_SCORE,
            warnings=warnings,
            nearest_resistance=nearest_resistance,
            rsi_1m=rsi_1m,
            rsi_1h=rsi_1h,
            funding_rate=funding_rate,
            sell_ratio=sell_ratio,
            macd_bearish=macd_bearish,
            volume_ratio=volume_ratio,
        )
    
    def _check_htf_resistance(
        self,
        current_price: float,
        klines_4h: list[dict],
        klines_1d: list[dict],
    ) -> PriceLevel | None:
        """Check for nearby high timeframe resistance.
        
        Args:
            current_price: Current price.
            klines_4h: 4-hour klines.
            klines_1d: Daily klines.
            
        Returns:
            Nearest resistance level or None.
        """
        # Try daily first (stronger levels)
        if klines_1d and len(klines_1d) >= 20:
            highs = [k["high"] for k in klines_1d]
            lows = [k["low"] for k in klines_1d]
            closes = [k["close"] for k in klines_1d]
            
            resistance = find_nearest_resistance(
                highs, lows, closes, current_price,
                max_distance_pct=self.RESISTANCE_DISTANCE_PCT,
            )
            if resistance:
                resistance.timeframe = "1D"
                return resistance
        
        # Try 4H
        if klines_4h and len(klines_4h) >= 20:
            highs = [k["high"] for k in klines_4h]
            lows = [k["low"] for k in klines_4h]
            closes = [k["close"] for k in klines_4h]
            
            resistance = find_nearest_resistance(
                highs, lows, closes, current_price,
                max_distance_pct=self.RESISTANCE_DISTANCE_PCT,
            )
            if resistance:
                resistance.timeframe = "4H"
                return resistance
        
        return None
    
    def _analyze_upper_wicks(self, klines: list[dict]) -> int:
        """Analyze upper wicks for selling pressure.
        
        Long upper wicks indicate selling pressure.
        
        Args:
            klines: Recent klines.
            
        Returns:
            Score (0 to TIER2_UPPER_WICK).
        """
        if not klines:
            return 0
        
        long_wick_count = 0
        
        for k in klines:
            high = k["high"]
            low = k["low"]
            open_p = k["open"]
            close = k["close"]
            
            body = abs(close - open_p)
            upper_wick = high - max(open_p, close)
            total_range = high - low
            
            if total_range > 0 and body > 0:
                # Upper wick is more than 50% of body = long wick
                if upper_wick > body * 0.5:
                    long_wick_count += 1
        
        # If more than 30% of candles have long upper wicks
        if len(klines) > 0 and long_wick_count / len(klines) >= 0.3:
            return self.FACTOR_UPPER_WICK
        elif long_wick_count >= 2:
            return self.FACTOR_UPPER_WICK // 2
        
        return 0

