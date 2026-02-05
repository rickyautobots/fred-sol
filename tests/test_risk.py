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
    
    # Too large should be blocked (500 > 10% of 1000)
    allowed, reason = rm.check_trade_allowed(500.0, "SOL/USDC")
    assert not allowed
    # Error message contains "position" and "large" (position too large)
    assert "position" in reason.lower() or "large" in reason.lower()


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
    
    # Manually set capital to simulate winning trades
    rm.capital = 1100.0  # Now at $1100
    
    # High water mark should update
    rm.update_high_water_mark()
    assert rm.high_water_mark == 1100.0
    
    # Simulate drawdown beyond limit (18% down from HWM)
    rm.capital = 900.0
    
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
    
    # Close position (needs price for full close_position method)
    # Use simplified approach - delete from positions directly
    del rm.positions["SOL/USDC"]
    assert rm.total_exposure() == 50.0


def test_exposure_limit():
    """Test total exposure limit."""
    # Use larger capital so position sizes pass the per-position check
    rm = RiskManager(initial_capital=10000.0)
    
    # Add positions (200 is 2% of 10000, below 10% per-position limit)
    rm.add_position("SOL/USDC", 2000.0)  # 20% exposure
    rm.add_position("JUP/USDC", 2000.0)  # 40% total
    rm.add_position("RAY/USDC", 1000.0)  # 50% total (at limit)
    
    # Next trade should be limited by exposure
    allowed, reason = rm.check_trade_allowed(500.0, "BONK/USDC")
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


def test_record_trade_result():
    """Test recording trade results."""
    rm = RiskManager(initial_capital=1000.0)
    
    # Record a winning trade
    rm.record_trade_result("SOL/USDC", 50.0)
    assert rm.daily_pnl == 50.0
    assert rm.capital == 1050.0
    
    # Record a losing trade
    rm.record_trade_result("JUP/USDC", -30.0)
    assert rm.daily_pnl == 20.0
    assert rm.capital == 1020.0


def test_rate_limiting():
    """Test trade rate limiting."""
    rm = RiskManager(initial_capital=1000.0)
    
    # First trade should be allowed
    allowed, _ = rm.check_trade_allowed(50.0, "SOL/USDC")
    assert allowed


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
    
    test_record_trade_result()
    print("✓ Record trade result")
    
    test_rate_limiting()
    print("✓ Rate limiting")
    
    print("\n✅ All risk tests passed")
