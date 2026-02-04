#!/usr/bin/env python3
"""Tests for FRED-SOL scanner."""

import asyncio
import pytest
from scanner import SolanaScanner, Market


def test_market_dataclass():
    """Test Market dataclass creation."""
    m = Market(
        id="test_1",
        question="SOL/USD",
        outcomes=[{"name": "price", "value": 100.0}],
        volume_24h=1000000,
        liquidity=500000,
        source="test"
    )
    assert m.id == "test_1"
    assert m.volume_24h == 1000000


@pytest.mark.asyncio
async def test_scanner_init():
    """Test scanner initialization."""
    scanner = SolanaScanner()
    assert scanner.client is not None
    await scanner.close()


@pytest.mark.asyncio
async def test_scan_all_returns_list():
    """Test scan_all returns a list."""
    scanner = SolanaScanner()
    try:
        markets = await scanner.scan_all(limit=5)
        assert isinstance(markets, list)
    finally:
        await scanner.close()


def test_kelly_sizing():
    """Test Kelly criterion calculation."""
    from main import FredSol
    
    agent = FredSol()
    
    # 60% edge, 2:1 odds, full confidence
    size = agent.kelly_size(0.6, 2.0, 1.0)
    assert 0 < size <= 0.10  # Capped at 10%
    
    # No edge
    size = agent.kelly_size(0.5, 2.0, 1.0)
    assert size == 0
    
    # Low confidence reduces size
    size_high = agent.kelly_size(0.6, 2.0, 1.0)
    size_low = agent.kelly_size(0.6, 2.0, 0.5)
    assert size_low < size_high


if __name__ == "__main__":
    # Run basic tests
    test_market_dataclass()
    print("✓ Market dataclass")
    
    test_kelly_sizing()
    print("✓ Kelly sizing")
    
    asyncio.run(test_scanner_init())
    print("✓ Scanner init")
    
    print("\n✅ All tests passed")
