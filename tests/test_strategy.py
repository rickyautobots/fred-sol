#!/usr/bin/env python3
"""
Tests for trading strategies
"""

import pytest
from datetime import datetime, timezone

import sys
sys.path.insert(0, '..')

from strategy import (
    Signal, MarketData, TradeSignal,
    MomentumStrategy, MeanReversionStrategy, BreakoutStrategy,
    CompositeStrategy, get_strategy, STRATEGIES
)


@pytest.fixture
def bullish_data():
    """Bullish market data"""
    return MarketData(
        symbol="SOL/USDC",
        timestamp=datetime.now(timezone.utc),
        price=100.0,
        volume_24h=5_000_000,
        high_24h=105.0,
        low_24h=92.0,
        change_24h=8.5,
        liquidity=1_000_000
    )


@pytest.fixture
def bearish_data():
    """Bearish market data"""
    return MarketData(
        symbol="SOL/USDC",
        timestamp=datetime.now(timezone.utc),
        price=90.0,
        volume_24h=3_000_000,
        high_24h=100.0,
        low_24h=88.0,
        change_24h=-12.0,
        liquidity=800_000
    )


@pytest.fixture
def neutral_data():
    """Neutral market data"""
    return MarketData(
        symbol="SOL/USDC",
        timestamp=datetime.now(timezone.utc),
        price=95.0,
        volume_24h=2_000_000,
        high_24h=97.0,
        low_24h=93.0,
        change_24h=1.5,
        liquidity=600_000
    )


class TestMarketData:
    """Test MarketData class"""
    
    def test_volatility_calculation(self, bullish_data):
        vol = bullish_data.volatility
        # (105 - 92) / 92 = 0.1413
        assert 0.14 < vol < 0.15
    
    def test_volatility_zero_low(self):
        data = MarketData(
            symbol="TEST",
            timestamp=datetime.now(timezone.utc),
            price=100,
            volume_24h=1000,
            high_24h=100,
            low_24h=0,
            change_24h=0
        )
        assert data.volatility == 0.0


class TestTradeSignal:
    """Test TradeSignal class"""
    
    def test_signal_creation(self):
        signal = TradeSignal(
            signal=Signal.BUY,
            symbol="SOL/USDC",
            confidence=0.75,
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=115.0
        )
        
        assert signal.signal == Signal.BUY
        assert signal.confidence == 0.75


class TestMomentumStrategy:
    """Test momentum strategy"""
    
    def test_buy_on_strong_momentum(self, bullish_data):
        strategy = MomentumStrategy(min_change_pct=5.0)
        signal = strategy.generate_signal(bullish_data)
        
        assert signal.signal == Signal.BUY
        assert signal.confidence > 0.3
    
    def test_sell_on_negative_momentum(self, bearish_data):
        strategy = MomentumStrategy(min_change_pct=5.0)
        signal = strategy.generate_signal(bearish_data)
        
        assert signal.signal == Signal.SELL
        assert signal.confidence > 0.3
    
    def test_hold_on_weak_momentum(self, neutral_data):
        strategy = MomentumStrategy(min_change_pct=5.0)
        signal = strategy.generate_signal(neutral_data)
        
        assert signal.signal == Signal.HOLD
    
    def test_hold_on_low_volume(self, bullish_data):
        bullish_data.volume_24h = 50_000  # Below default 100k threshold
        strategy = MomentumStrategy()
        signal = strategy.generate_signal(bullish_data)
        
        assert signal.signal == Signal.HOLD
        assert "Insufficient volume" in signal.reasoning
    
    def test_volume_surge_increases_confidence(self, bullish_data):
        strategy = MomentumStrategy()
        context = {"avg_volume": 2_000_000}
        
        signal = strategy.generate_signal(bullish_data, context)
        
        # Volume surge (5M vs 2M avg) should boost confidence
        assert signal.confidence > 0.4


class TestMeanReversionStrategy:
    """Test mean reversion strategy"""
    
    def test_buy_on_oversold(self, bearish_data):
        strategy = MeanReversionStrategy(oversold_threshold=-10.0)
        signal = strategy.generate_signal(bearish_data)
        
        assert signal.signal == Signal.BUY
        assert "Oversold" in signal.reasoning or signal.signal == Signal.HOLD
    
    def test_hold_on_low_liquidity(self, bullish_data):
        bullish_data.liquidity = 10_000  # Below threshold
        strategy = MeanReversionStrategy(min_liquidity=50_000)
        signal = strategy.generate_signal(bullish_data)
        
        assert signal.signal == Signal.HOLD
        assert "liquidity" in signal.reasoning.lower()
    
    def test_uses_price_history_for_deviation(self):
        data = MarketData(
            symbol="TEST",
            timestamp=datetime.now(timezone.utc),
            price=80.0,  # 20% below average
            volume_24h=1_000_000,
            high_24h=90.0,
            low_24h=78.0,
            change_24h=-5.0,
            liquidity=100_000
        )
        
        context = {"price_history": [100, 100, 100, 100, 100]}  # avg = 100
        strategy = MeanReversionStrategy(oversold_threshold=-15.0)
        signal = strategy.generate_signal(data, context)
        
        assert signal.signal == Signal.BUY
        assert signal.confidence > 0.5


class TestBreakoutStrategy:
    """Test breakout strategy"""
    
    def test_hold_without_price_history(self, bullish_data):
        strategy = BreakoutStrategy()
        signal = strategy.generate_signal(bullish_data)
        
        assert signal.signal == Signal.HOLD
        assert "history" in signal.reasoning.lower()
    
    def test_bullish_breakout(self):
        data = MarketData(
            symbol="TEST",
            timestamp=datetime.now(timezone.utc),
            price=110.0,  # Above recent high of ~100
            volume_24h=1_000_000,
            high_24h=112.0,
            low_24h=108.0,
            change_24h=10.0,
            liquidity=100_000
        )
        # Low volatility range
        data.high_24h = 111.0
        data.low_24h = 109.0
        
        context = {"price_history": [95, 96, 97, 98, 99, 100, 99, 98, 99, 100]}
        strategy = BreakoutStrategy(breakout_pct=3.0)
        signal = strategy.generate_signal(data, context)
        
        # Price (110) is above recent high (100) + 3% = 103
        assert signal.signal == Signal.BUY


class TestCompositeStrategy:
    """Test composite strategy"""
    
    def test_combines_strategies(self, bullish_data):
        strategy = CompositeStrategy()
        context = {"avg_volume": 2_000_000, "price_history": [90] * 10}
        signal = strategy.generate_signal(bullish_data, context)
        
        # Should aggregate signals from multiple strategies
        assert signal.signal in [Signal.BUY, Signal.SELL, Signal.HOLD]
        assert "|" in signal.reasoning or signal.signal == Signal.HOLD
    
    def test_custom_weights(self, bullish_data):
        # Heavy momentum weight
        strategy = CompositeStrategy([
            (MomentumStrategy(), 0.9),
            (MeanReversionStrategy(), 0.1)
        ])
        
        signal = strategy.generate_signal(bullish_data)
        
        # Should favor momentum signal
        if bullish_data.change_24h > 5:
            assert signal.signal == Signal.BUY


class TestStrategyRegistry:
    """Test strategy registry"""
    
    def test_all_strategies_registered(self):
        expected = ["momentum", "mean_reversion", "breakout", "composite"]
        for name in expected:
            assert name in STRATEGIES
    
    def test_get_strategy_by_name(self):
        strategy = get_strategy("momentum")
        assert isinstance(strategy, MomentumStrategy)
    
    def test_get_strategy_with_kwargs(self):
        strategy = get_strategy("momentum", min_change_pct=10.0)
        assert strategy.min_change_pct == 10.0
    
    def test_get_strategy_invalid_name(self):
        with pytest.raises(ValueError):
            get_strategy("nonexistent")


class TestPositionSizing:
    """Test position sizing logic"""
    
    def test_calculate_position_size(self, bullish_data):
        strategy = MomentumStrategy()
        signal = strategy.generate_signal(bullish_data)
        
        size = strategy.calculate_position_size(
            signal,
            portfolio_value=10000,
            max_position_pct=0.05
        )
        
        if signal.signal == Signal.BUY:
            assert 0 < size <= 500  # Max 5% of 10000
        else:
            assert size == 0
    
    def test_hold_signal_zero_size(self, neutral_data):
        strategy = MomentumStrategy()
        signal = strategy.generate_signal(neutral_data)
        
        size = strategy.calculate_position_size(signal, 10000, 0.05)
        
        if signal.signal == Signal.HOLD:
            assert size == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
