#!/usr/bin/env python3
"""Tests for FRED-SOL EverMind memory integration."""

from memory_evermind import (
    TradeMemory,
    EverMindMemory,
)


def test_trade_memory_creation():
    """Test TradeMemory dataclass creation."""
    trade = TradeMemory(
        symbol="SOL/USDC",
        action="BUY",
        reasoning="Momentum breakout",
        probability=0.58,
        confidence=0.65,
        size_usd=100,
        price=96.42
    )
    
    assert trade.symbol == "SOL/USDC"
    assert trade.action == "BUY"
    assert trade.probability == 0.58
    assert trade.timestamp  # Should auto-set


def test_trade_memory_content():
    """Test TradeMemory natural language content generation."""
    trade = TradeMemory(
        symbol="JUP/USDC",
        action="SELL",
        reasoning="Profit taking",
        probability=0.45,
        confidence=0.70,
        size_usd=50,
        price=0.82
    )
    
    content = trade.to_content()
    assert "JUP/USDC" in content
    assert "SELL" in content
    assert "Profit taking" in content


def test_trade_memory_with_outcome():
    """Test TradeMemory with outcome recorded."""
    trade = TradeMemory(
        symbol="SOL/USDC",
        action="BUY",
        reasoning="Test",
        probability=0.60,
        confidence=0.80,
        size_usd=100,
        price=95.00,
        outcome="WIN",
        pnl=15.50
    )
    
    content = trade.to_content()
    assert "WIN" in content
    assert "15.50" in content


def test_memory_init():
    """Test EverMindMemory initialization."""
    memory = EverMindMemory(user_id="test_agent")
    assert memory.user_id == "test_agent"
    assert memory.api_url  # Should have default


def test_memory_disabled_without_httpx():
    """Test graceful degradation without httpx."""
    # When httpx is not installed, should disable gracefully
    memory = EverMindMemory()
    # Should not raise, just return False
    trade = TradeMemory(
        symbol="SOL/USDC",
        action="BUY",
        reasoning="Test",
        probability=0.55,
        confidence=0.70,
        size_usd=50,
        price=100
    )
    # This might return False if disabled, but shouldn't crash
    result = memory.store_trade(trade)
    assert result in [True, False]


def test_get_trading_patterns_empty():
    """Test pattern retrieval with no history."""
    memory = EverMindMemory()
    patterns = memory.get_trading_patterns("UNKNOWN/USDC")
    
    # Should return empty patterns structure
    assert patterns["symbol"] == "UNKNOWN/USDC"
    assert patterns["trades_recalled"] >= 0


def test_should_trade_no_history():
    """Test trading decision with no history."""
    memory = EverMindMemory()
    
    result = memory.should_trade("NEW/USDC", 0.55)
    
    # Without history, should return original probability
    assert result["original_probability"] == 0.55
    # Adjustment should be minimal
    assert abs(result["adjusted_probability"] - 0.55) <= 0.05


def test_memory_adjustment_logic():
    """Test that memory adjustments are bounded."""
    memory = EverMindMemory()
    
    # Test with various probabilities
    for prob in [0.1, 0.5, 0.9]:
        result = memory.should_trade("TEST/USDC", prob)
        
        # Adjusted probability should stay in bounds
        assert 0 <= result["adjusted_probability"] <= 1
        
        # Confidence adjustment should be reasonable
        assert -1 <= result["confidence_adjustment"] <= 1


def test_trade_memory_fields():
    """Test all TradeMemory fields."""
    trade = TradeMemory(
        symbol="SOL/USDC",
        action="BUY",
        reasoning="Strong momentum",
        probability=0.62,
        confidence=0.85,
        size_usd=200,
        price=98.50
    )
    
    # Required fields
    assert trade.symbol
    assert trade.action in ["BUY", "SELL", "SKIP"]
    assert trade.reasoning
    
    # Numerical bounds
    assert 0 <= trade.probability <= 1
    assert 0 <= trade.confidence <= 1
    assert trade.size_usd >= 0
    assert trade.price >= 0
    
    # Optional fields
    assert trade.outcome is None
    assert trade.pnl is None


def test_memory_close():
    """Test memory cleanup."""
    memory = EverMindMemory()
    # Should not raise
    memory.close()


if __name__ == "__main__":
    """Run tests."""
    test_trade_memory_creation()
    print("✓ Trade memory creation")
    
    test_trade_memory_content()
    print("✓ Trade memory content")
    
    test_trade_memory_with_outcome()
    print("✓ Trade memory with outcome")
    
    test_memory_init()
    print("✓ Memory init")
    
    test_get_trading_patterns_empty()
    print("✓ Empty patterns")
    
    test_should_trade_no_history()
    print("✓ Trading decision without history")
    
    test_memory_adjustment_logic()
    print("✓ Adjustment logic bounds")
    
    test_trade_memory_fields()
    print("✓ Trade memory fields")
    
    test_memory_close()
    print("✓ Memory close")
    
    print("\n✅ All memory tests passed")
