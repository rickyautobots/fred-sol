#!/usr/bin/env python3
"""Tests for FRED-SOL risk management."""

import pytest
from risk import RiskManager, RiskConfig, TradingLimits


def test_risk_config_defaults():
    """Test default risk config values."""
    config = RiskConfig()
    assert config.max_position_pct == 0.10
    assert config.max_total_exposure == 0.50
    assert config.max_daily_loss_pct == 0.05
    assert config.max_drawdown_pct == 0.15


def test_risk_manager_init():
    """Test risk manager initialization."""
    rm = RiskManager(initial_capital=1000.0)
    assert rm.capital == 1000.0
    assert rm.high_water_mark == 1000.0
    assert rm.daily_pnl == 0.0


def test_max_position_size():
    """Test position size limits."""
    rm = RiskManager(initial_capital=1000.0)
    
    # Should cap at max_position_pct (10% = $100)
    assert rm.max_position_size() == 100.0
    
    # Custom config
    config = RiskConfig(max_position_pct=0.25)
    rm2 = RiskManager(initial_capital=1000.0, config=config)
    assert rm2.max_position_size() == 250.0


def test_check_trade_allowed():
    """Test trade permission checks."""
    rm = RiskManager(initial_capital=1000.0)
    
    # Small trade should be allowed
    allowed, reason = rm.check_trade_allowed(50.0, "SOL/USDC")
    assert allowed
    
    # Too large should be blocked
    allowed, reason = rm.check_trade_allowed(500.0, "SOL/USDC")
    assert not allowed
    assert "exceeds max" in reason.lower()


def test_daily_loss_limit():
    """Test daily loss limit enforcement."""
    rm = RiskManager(initial_capital=1000.0)
    
    # Should start allowed
    allowed, _ = rm.check_trade_allowed(50.0, "SOL/USDC")
    assert allowed
    
    # Simulate daily loss
    rm.record_trade_result("SOL/USDC", -60.0)  # 6% loss
    
    # Should now be blocked
    allowed, reason = rm.check_trade_allowed(50.0, "SOL/USDC")
    assert not allowed
    assert "daily loss limit" in reason.lower()


def test_drawdown_protection():
    """Test max drawdown enforcement."""
    rm = RiskManager(initial_capital=1000.0)
    
    # Record winning trade
    rm.record_trade_result("SOL/USDC", 100.0)
    rm.capital += 100  # Now at $1100
    
    # High water mark should update
    rm.update_high_water_mark()
    assert rm.high_water_mark == 1100.0
    
    # Simulate drawdown beyond limit
    rm.capital = 900.0  # 18% down from HWM
    
    # Should be blocked
    allowed, reason = rm.check_drawdown()
    assert not allowed
    assert "drawdown" in reason.lower()


def test_position_tracking():
    """Test open position tracking."""
    rm = RiskManager(initial_capital=1000.0)
    
    # Track position
    rm.add_position("SOL/USDC", 100.0)
    assert rm.total_exposure() == 100.0
    
    # Multiple positions
    rm.add_position("JUP/USDC", 50.0)
    assert rm.total_exposure() == 150.0
    
    # Close position
    rm.close_position("SOL/USDC")
    assert rm.total_exposure() == 50.0


def test_exposure_limit():
    """Test total exposure limit."""
    rm = RiskManager(initial_capital=1000.0)
    
    # Add positions up to limit
    rm.add_position("SOL/USDC", 200.0)
    rm.add_position("JUP/USDC", 200.0)
    
    # Next trade should be limited
    allowed, reason = rm.check_trade_allowed(200.0, "BONK/USDC")
    assert not allowed
    assert "exposure" in reason.lower()


def test_trading_limits_dataclass():
    """Test TradingLimits dataclass."""
    limits = TradingLimits(
        max_trades_per_hour=10,
        min_trade_interval_sec=60,
        cooldown_after_loss_sec=300
    )
    assert limits.max_trades_per_hour == 10
    assert limits.min_trade_interval_sec == 60


if __name__ == "__main__":
    """Run tests."""
    test_risk_config_defaults()
    print("✓ Risk config defaults")
    
    test_risk_manager_init()
    print("✓ Risk manager init")
    
    test_max_position_size()
    print("✓ Max position size")
    
    test_check_trade_allowed()
    print("✓ Trade allowed check")
    
    test_daily_loss_limit()
    print("✓ Daily loss limit")
    
    test_drawdown_protection()
    print("✓ Drawdown protection")
    
    test_position_tracking()
    print("✓ Position tracking")
    
    test_exposure_limit()
    print("✓ Exposure limit")
    
    test_trading_limits_dataclass()
    print("✓ Trading limits dataclass")
    
    print("\n✅ All risk tests passed")
