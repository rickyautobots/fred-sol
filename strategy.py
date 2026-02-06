#!/usr/bin/env python3
"""
FRED-SOL: Trading Strategies
Pluggable strategy framework for automated trading

Built: 2026-02-06 07:45 CST by Ricky
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from enum import Enum
import statistics


class Signal(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class MarketData:
    """Market data for strategy analysis"""
    symbol: str
    timestamp: datetime
    price: float
    volume_24h: float
    high_24h: float
    low_24h: float
    change_24h: float
    liquidity: float = 0.0
    
    @property
    def volatility(self) -> float:
        """Simple volatility estimate"""
        if self.low_24h == 0:
            return 0.0
        return (self.high_24h - self.low_24h) / self.low_24h


@dataclass
class TradeSignal:
    """Trading signal from strategy"""
    signal: Signal
    symbol: str
    confidence: float  # 0.0 - 1.0
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    size_pct: float = 0.0  # Suggested position size
    reasoning: str = ""
    metadata: Dict = None


class Strategy(ABC):
    """
    Base class for trading strategies
    
    Implement generate_signal() to create custom strategies.
    """
    
    name: str = "base_strategy"
    description: str = "Base strategy class"
    
    @abstractmethod
    def generate_signal(self, data: MarketData, context: Dict = None) -> TradeSignal:
        """
        Generate trading signal from market data
        
        Args:
            data: Current market data
            context: Additional context (portfolio, history, etc.)
            
        Returns:
            TradeSignal with recommendation
        """
        pass
    
    def calculate_position_size(
        self,
        signal: TradeSignal,
        portfolio_value: float,
        max_position_pct: float = 0.05
    ) -> float:
        """Calculate position size based on signal confidence"""
        if signal.signal == Signal.HOLD:
            return 0.0
        
        # Kelly-inspired sizing: confidence * edge
        base_size = signal.confidence * max_position_pct
        return min(base_size, max_position_pct) * portfolio_value


class MomentumStrategy(Strategy):
    """
    Momentum-based trading strategy
    
    Buys on positive momentum, sells on negative.
    Uses 24h change and volume as indicators.
    """
    
    name = "momentum"
    description = "Trade based on price momentum and volume"
    
    def __init__(
        self,
        min_change_pct: float = 5.0,
        min_volume: float = 100000,
        volume_surge_threshold: float = 2.0
    ):
        self.min_change_pct = min_change_pct
        self.min_volume = min_volume
        self.volume_surge_threshold = volume_surge_threshold
    
    def generate_signal(self, data: MarketData, context: Dict = None) -> TradeSignal:
        context = context or {}
        avg_volume = context.get("avg_volume", data.volume_24h)
        
        # Check volume threshold
        if data.volume_24h < self.min_volume:
            return TradeSignal(
                signal=Signal.HOLD,
                symbol=data.symbol,
                confidence=0.0,
                reasoning="Insufficient volume"
            )
        
        # Volume surge indicator
        volume_ratio = data.volume_24h / avg_volume if avg_volume > 0 else 1.0
        volume_surge = volume_ratio > self.volume_surge_threshold
        
        # Generate signal based on momentum
        if data.change_24h > self.min_change_pct:
            confidence = min(data.change_24h / 20.0, 0.9)
            if volume_surge:
                confidence = min(confidence + 0.1, 0.95)
            
            return TradeSignal(
                signal=Signal.BUY,
                symbol=data.symbol,
                confidence=confidence,
                entry_price=data.price,
                stop_loss=data.price * 0.95,
                take_profit=data.price * 1.15,
                size_pct=confidence * 0.05,
                reasoning=f"Positive momentum: +{data.change_24h:.1f}%{' with volume surge' if volume_surge else ''}"
            )
        
        elif data.change_24h < -self.min_change_pct:
            confidence = min(abs(data.change_24h) / 20.0, 0.8)
            
            return TradeSignal(
                signal=Signal.SELL,
                symbol=data.symbol,
                confidence=confidence,
                reasoning=f"Negative momentum: {data.change_24h:.1f}%"
            )
        
        return TradeSignal(
            signal=Signal.HOLD,
            symbol=data.symbol,
            confidence=0.0,
            reasoning=f"No significant momentum: {data.change_24h:+.1f}%"
        )


class MeanReversionStrategy(Strategy):
    """
    Mean reversion strategy
    
    Buys oversold conditions, sells overbought.
    Uses deviation from moving average.
    """
    
    name = "mean_reversion"
    description = "Trade reversions to mean price"
    
    def __init__(
        self,
        oversold_threshold: float = -10.0,
        overbought_threshold: float = 15.0,
        min_liquidity: float = 50000
    ):
        self.oversold_threshold = oversold_threshold
        self.overbought_threshold = overbought_threshold
        self.min_liquidity = min_liquidity
    
    def generate_signal(self, data: MarketData, context: Dict = None) -> TradeSignal:
        context = context or {}
        
        # Check liquidity
        if data.liquidity < self.min_liquidity:
            return TradeSignal(
                signal=Signal.HOLD,
                symbol=data.symbol,
                confidence=0.0,
                reasoning="Insufficient liquidity"
            )
        
        # Use price history if available
        price_history = context.get("price_history", [])
        if price_history:
            avg_price = statistics.mean(price_history[-20:])
            deviation = ((data.price - avg_price) / avg_price) * 100
        else:
            deviation = data.change_24h
        
        # Oversold → Buy
        if deviation < self.oversold_threshold:
            confidence = min(abs(deviation) / 25.0, 0.85)
            
            return TradeSignal(
                signal=Signal.BUY,
                symbol=data.symbol,
                confidence=confidence,
                entry_price=data.price,
                stop_loss=data.price * 0.92,
                take_profit=data.price * 1.08,
                size_pct=confidence * 0.04,
                reasoning=f"Oversold: {deviation:.1f}% below average"
            )
        
        # Overbought → Sell
        elif deviation > self.overbought_threshold:
            confidence = min(deviation / 30.0, 0.80)
            
            return TradeSignal(
                signal=Signal.SELL,
                symbol=data.symbol,
                confidence=confidence,
                reasoning=f"Overbought: {deviation:.1f}% above average"
            )
        
        return TradeSignal(
            signal=Signal.HOLD,
            symbol=data.symbol,
            confidence=0.0,
            reasoning=f"Within normal range: {deviation:+.1f}%"
        )


class BreakoutStrategy(Strategy):
    """
    Breakout trading strategy
    
    Trades breakouts from consolidation ranges.
    """
    
    name = "breakout"
    description = "Trade price breakouts from ranges"
    
    def __init__(
        self,
        volatility_threshold: float = 0.05,
        breakout_pct: float = 3.0
    ):
        self.volatility_threshold = volatility_threshold
        self.breakout_pct = breakout_pct
    
    def generate_signal(self, data: MarketData, context: Dict = None) -> TradeSignal:
        context = context or {}
        
        # Need price history for range detection
        price_history = context.get("price_history", [])
        if len(price_history) < 10:
            return TradeSignal(
                signal=Signal.HOLD,
                symbol=data.symbol,
                confidence=0.0,
                reasoning="Insufficient price history"
            )
        
        # Calculate recent range
        recent_high = max(price_history[-10:])
        recent_low = min(price_history[-10:])
        range_pct = ((recent_high - recent_low) / recent_low) * 100
        
        # Low volatility = consolidation
        if data.volatility < self.volatility_threshold:
            # Check for breakout
            if data.price > recent_high * (1 + self.breakout_pct / 100):
                return TradeSignal(
                    signal=Signal.BUY,
                    symbol=data.symbol,
                    confidence=0.75,
                    entry_price=data.price,
                    stop_loss=recent_high * 0.98,
                    take_profit=data.price * 1.10,
                    size_pct=0.04,
                    reasoning=f"Bullish breakout above {recent_high:.4f}"
                )
            
            elif data.price < recent_low * (1 - self.breakout_pct / 100):
                return TradeSignal(
                    signal=Signal.SELL,
                    symbol=data.symbol,
                    confidence=0.70,
                    reasoning=f"Bearish breakdown below {recent_low:.4f}"
                )
        
        return TradeSignal(
            signal=Signal.HOLD,
            symbol=data.symbol,
            confidence=0.0,
            reasoning=f"No breakout detected (range: {range_pct:.1f}%)"
        )


class CompositeStrategy(Strategy):
    """
    Combines multiple strategies with weighted voting
    """
    
    name = "composite"
    description = "Weighted combination of multiple strategies"
    
    def __init__(self, strategies: List[tuple] = None):
        """
        Args:
            strategies: List of (Strategy, weight) tuples
        """
        self.strategies = strategies or [
            (MomentumStrategy(), 0.4),
            (MeanReversionStrategy(), 0.35),
            (BreakoutStrategy(), 0.25)
        ]
    
    def generate_signal(self, data: MarketData, context: Dict = None) -> TradeSignal:
        buy_score = 0.0
        sell_score = 0.0
        reasons = []
        
        for strategy, weight in self.strategies:
            signal = strategy.generate_signal(data, context)
            
            if signal.signal == Signal.BUY:
                buy_score += signal.confidence * weight
                reasons.append(f"{strategy.name}: BUY ({signal.confidence:.0%})")
            elif signal.signal == Signal.SELL:
                sell_score += signal.confidence * weight
                reasons.append(f"{strategy.name}: SELL ({signal.confidence:.0%})")
        
        # Determine final signal
        if buy_score > sell_score and buy_score > 0.3:
            return TradeSignal(
                signal=Signal.BUY,
                symbol=data.symbol,
                confidence=buy_score,
                entry_price=data.price,
                stop_loss=data.price * 0.95,
                take_profit=data.price * 1.12,
                size_pct=min(buy_score * 0.05, 0.05),
                reasoning=" | ".join(reasons)
            )
        
        elif sell_score > buy_score and sell_score > 0.3:
            return TradeSignal(
                signal=Signal.SELL,
                symbol=data.symbol,
                confidence=sell_score,
                reasoning=" | ".join(reasons)
            )
        
        return TradeSignal(
            signal=Signal.HOLD,
            symbol=data.symbol,
            confidence=0.0,
            reasoning=f"No consensus (buy: {buy_score:.0%}, sell: {sell_score:.0%})"
        )


# Strategy registry
STRATEGIES = {
    "momentum": MomentumStrategy,
    "mean_reversion": MeanReversionStrategy,
    "breakout": BreakoutStrategy,
    "composite": CompositeStrategy
}


def get_strategy(name: str, **kwargs) -> Strategy:
    """Get strategy by name"""
    if name not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGIES.keys())}")
    return STRATEGIES[name](**kwargs)


if __name__ == "__main__":
    # Demo
    data = MarketData(
        symbol="SOL/USDC",
        timestamp=datetime.now(timezone.utc),
        price=98.50,
        volume_24h=5_000_000,
        high_24h=102.00,
        low_24h=95.00,
        change_24h=7.5,
        liquidity=1_000_000
    )
    
    context = {
        "avg_volume": 3_000_000,
        "price_history": [95, 96, 97, 96, 97, 98, 97, 98, 99, 98.5]
    }
    
    print("=" * 50)
    print(f"Market: {data.symbol} @ ${data.price}")
    print(f"24h Change: {data.change_24h:+.1f}%")
    print(f"Volume: ${data.volume_24h:,.0f}")
    print("=" * 50)
    
    for name in STRATEGIES:
        strategy = get_strategy(name)
        signal = strategy.generate_signal(data, context)
        
        emoji = "🟢" if signal.signal == Signal.BUY else "🔴" if signal.signal == Signal.SELL else "⚪"
        print(f"\n{emoji} {strategy.name}:")
        print(f"   Signal: {signal.signal.value.upper()}")
        print(f"   Confidence: {signal.confidence:.0%}")
        print(f"   Reason: {signal.reasoning}")
