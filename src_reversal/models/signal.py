"""Reversal signal data models."""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum

from src_reversal.services.scorer import ReversalScore, SignalStrength


class SignalStrength(Enum):
    """Signal strength level."""
    
    STRONG = 3  # ⚡⚡⚡
    MEDIUM = 2  # ⚡⚡
    WEAK = 1    # ⚡


@dataclass
class ExchangeLinks:
    """Exchange availability and links."""
    
    mexc: str = ""
    binance: str | None = None
    bybit: str | None = None
    bingx: str | None = None


@dataclass
class ReversalSignal:
    """A reversal signal with all analysis data."""
    
    symbol: str
    price: float
    pump_percent: float
    volume_24h: float
    score: ReversalScore
    timestamp: datetime
    exchange_links: ExchangeLinks
    chart_image: bytes | None = None
    
    # For tracking
    pre_pump_price: float = 0.0
    
    def __post_init__(self):
        """Calculate pre-pump price."""
        if self.pre_pump_price == 0.0 and self.pump_percent > 0:
            self.pre_pump_price = self.price / (1 + self.pump_percent / 100)
    
    @property
    def strength_emoji(self) -> str:
        """Get strength indicator emoji."""
        strength = self.score.strength
        if strength == SignalStrength.STRONG:
            return "⚡⚡⚡"
        elif strength == SignalStrength.MEDIUM:
            return "⚡⚡"
        elif strength == SignalStrength.WEAK:
            return "⚡"
        return ""
    
    @property
    def coin_name(self) -> str:
        """Get clean coin name."""
        return self.symbol.replace("_USDT", "").replace("_", "")
    
    def format_message(self) -> str:
        """Format the signal as a Telegram message.
        
        Returns:
            Formatted message string.
        """
        # UTC+3 time
        utc3 = timezone(timedelta(hours=3))
        time_str = self.timestamp.astimezone(utc3).strftime("%H:%M:%S")
        
        lines = []
        
        # Header with strength
        lines.append(f"{self.strength_emoji} {self.coin_name}")
        lines.append("")
        
        # Basic info
        lines.append(f"📈 Pump: +{self.pump_percent:.2f}%")
        lines.append(f"💰 Price: ${self._format_price(self.price)}")
        lines.append(f"📊 24h Vol: ${self._format_volume(self.volume_24h)}")
        lines.append("")
        
        # Core Analysis section
        lines.append("━━━ Core Analysis ━━━")
        
        # HTF Resistance
        if self.score.nearest_resistance:
            res = self.score.nearest_resistance
            distance_pct = (res.price - self.price) / self.price * 100
            lines.append(f"✅ Resistance: ${self._format_price(res.price)} ({res.timeframe}, {res.touches} touches, {distance_pct:.1f}% away)")
        else:
            lines.append("❌ Resistance: None nearby")
        
        # RSI
        rsi_1m = self.score.rsi_1m
        rsi_1h = self.score.rsi_1h
        
        # Check for valid RSI (not None and not NaN)
        rsi_1m_valid = rsi_1m is not None and rsi_1m == rsi_1m  # NaN != NaN
        rsi_1h_valid = rsi_1h is not None and rsi_1h == rsi_1h
        
        rsi_status = "✅" if (rsi_1m_valid and rsi_1m >= 80) or (rsi_1h_valid and rsi_1h >= 80) else "❌"
        rsi_1m_str = f"{rsi_1m:.0f}" if rsi_1m_valid else "N/A"
        rsi_1h_str = f"{rsi_1h:.0f}" if rsi_1h_valid else "N/A"
        lines.append(f"{rsi_status} RSI: {rsi_1m_str} (1M) | {rsi_1h_str} (1H)")
        
        # MACD
        macd_status = "✅" if self.score.macd_bearish else "❌"
        macd_text = "Bearish cross" if self.score.macd_bearish else "No bearish cross"
        lines.append(f"{macd_status} MACD: {macd_text}")
        
        # Funding Rate
        if self.score.funding_rate is not None:
            fr = self.score.funding_rate
            if fr >= 0.2:
                fr_status = "✅"
            elif fr < -0.1:
                fr_status = "⚠️"
            else:
                fr_status = "❌"
            lines.append(f"{fr_status} Funding: {fr:+.4f}%")
        else:
            lines.append("❌ Funding: N/A")
        
        lines.append("")
        
        # Additional Data section (optional factors)
        has_additional = self.score.sell_ratio is not None or self.score.volume_ratio is not None
        
        if has_additional:
            lines.append("━━━ Additional Data ━━━")
            
            # Sell Volume (Binance only)
            if self.score.sell_ratio is not None:
                sr = self.score.sell_ratio
                sr_status = "✅" if sr >= 0.65 else "❌"
                lines.append(f"{sr_status} Sell Volume: {sr*100:.0f}%")
            else:
                lines.append("❌ Sell Volume: N/A (Binance only)")
            
            # Volume Ratio
            if self.score.volume_ratio is not None:
                vr = self.score.volume_ratio
                vr_status = "✅" if vr >= 3.0 else "❌"
                lines.append(f"{vr_status} Volume Spike: {vr:.1f}x average")
            
            lines.append("")
        
        # Warnings
        if self.score.warnings:
            for warning in self.score.warnings:
                lines.append(warning)
            lines.append("")
        
        # Footer
        lines.append(f"⏰ {time_str} (UTC+3)")
        
        # Exchange links
        links = []
        links.append(f"[MEXC]({self.exchange_links.mexc})")
        if self.exchange_links.binance:
            links.append(f"[Binance]({self.exchange_links.binance})")
        if self.exchange_links.bybit:
            links.append(f"[ByBit]({self.exchange_links.bybit})")
        if self.exchange_links.bingx:
            links.append(f"[BingX]({self.exchange_links.bingx})")
        
        lines.append("📈 " + " · ".join(links))
        
        return "\n".join(lines)
    
    def _format_price(self, price: float) -> str:
        """Format price for display."""
        if price >= 1000:
            return f"{price:,.2f}"
        elif price >= 1:
            return f"{price:.4f}"
        elif price >= 0.0001:
            return f"{price:.6f}"
        else:
            return f"{price:.8f}"
    
    def _format_volume(self, volume: float) -> str:
        """Format volume for display."""
        if volume >= 1_000_000_000:
            return f"{volume / 1_000_000_000:.2f}B"
        elif volume >= 1_000_000:
            return f"{volume / 1_000_000:.2f}M"
        elif volume >= 1_000:
            return f"{volume / 1_000:.2f}K"
        else:
            return f"{volume:.2f}"

