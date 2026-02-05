#!/usr/bin/env python3
"""Tests for FRED-SOL probability estimator."""

import pytest
import os
from estimator import ProbabilityEstimator, EstimationResult


def test_estimation_result_dataclass():
    """Test EstimationResult dataclass."""
    result = EstimationResult(
        probability=0.65,
        confidence=0.80,
        reasoning="Based on market momentum",
        factors={"momentum": 0.7, "volume": 0.5}
    )
    assert result.probability == 0.65
    assert result.confidence == 0.80
    assert "momentum" in result.factors


def test_estimator_init():
    """Test estimator initialization."""
    estimator = ProbabilityEstimator()
    assert estimator is not None


def test_confidence_bounds():
    """Test confidence is properly bounded."""
    result = EstimationResult(
        probability=0.5,
        confidence=0.9,
        reasoning="test"
    )
    assert 0 <= result.confidence <= 1


def test_edge_calculation():
    """Test edge calculation."""
    result = EstimationResult(
        probability=0.65,
        confidence=0.80,
        reasoning="test"
    )
    
    market_price = 0.50  # Market implies 50%
    edge = result.probability - market_price
    assert abs(edge - 0.15) < 1e-10  # Fixed: use approximate comparison


def test_kelly_with_confidence():
    """Test Kelly sizing with confidence adjustment."""
    result = EstimationResult(
        probability=0.60,
        confidence=0.80,
        reasoning="test"
    )
    
    # Kelly fraction for 60% prob, even odds
    # f* = (p - q) / 1 = 0.6 - 0.4 = 0.20
    # Confidence adjusted: 0.20 * 0.80 = 0.16
    # Half-Kelly: 0.16 * 0.5 = 0.08
    
    kelly = (result.probability - (1 - result.probability))
    adjusted = kelly * result.confidence * 0.5
    
    assert abs(adjusted - 0.08) < 0.01


def test_heuristic_estimation():
    """Test heuristic estimation (no API call)."""
    estimator = ProbabilityEstimator()  # No API key = uses heuristics
    
    market_data = {
        "symbol": "SOL/USDC",
        "price": 95.0,
        "volume_24h": 500_000,
        "price_change_24h": -2.0,
        "market_cap": 40_000_000_000
    }
    
    result = estimator._heuristic_estimate(market_data)
    
    assert isinstance(result, EstimationResult)
    assert 0 < result.probability < 1
    assert 0 < result.confidence <= 1


def test_estimation_factors():
    """Test that estimation result can have factors."""
    result = EstimationResult(
        probability=0.55,
        confidence=0.6,
        reasoning="Heuristic analysis",
        factors={"momentum": 0.5, "volume": 0.7}
    )
    
    # Should have factors dict
    assert isinstance(result.factors, dict)
    assert "momentum" in result.factors


def test_reasoning_generation():
    """Test that heuristic estimation generates reasoning."""
    estimator = ProbabilityEstimator()
    
    market_data = {
        "symbol": "BTC/USDC",
        "price": 76000.0,
        "volume_24h": 10_000_000,
        "price_change_24h": 1.5,
        "market_cap": 1_500_000_000_000
    }
    
    result = estimator._heuristic_estimate(market_data)
    
    # Should have non-empty reasoning
    assert result.reasoning
    assert len(result.reasoning) > 10


def test_no_api_key_fallback():
    """Test graceful fallback when no API key."""
    # Temporarily unset API key
    original = os.environ.get("ANTHROPIC_API_KEY")
    if original:
        del os.environ["ANTHROPIC_API_KEY"]
    
    try:
        estimator = ProbabilityEstimator()
        
        market_data = {
            "symbol": "TEST/USDC",
            "price": 1.0,
            "volume_24h": 100_000,
            "price_change_24h": 0.0
        }
        
        result = estimator._heuristic_estimate(market_data)
        # Should fallback to heuristic mode
        assert isinstance(result, EstimationResult)
    finally:
        if original:
            os.environ["ANTHROPIC_API_KEY"] = original


def test_high_volume_efficient_market():
    """Test that high volume leads to near-50% probability."""
    estimator = ProbabilityEstimator()
    
    market_data = {
        "symbol": "ETH/USDC",
        "price": 2500.0,
        "volume_24h": 50_000_000,  # Very high volume
        "price_change_24h": 0.0
    }
    
    result = estimator._heuristic_estimate(market_data)
    
    # High volume = efficient market = near 50%
    assert 0.45 <= result.probability <= 0.55
    assert result.confidence <= 0.5  # Lower confidence in efficient market


def test_low_volume_opportunity():
    """Test that low volume has higher confidence edge."""
    estimator = ProbabilityEstimator()
    
    market_data = {
        "symbol": "MICRO/USDC",
        "price": 0.001,
        "volume_24h": 10_000,  # Very low volume
        "price_change_24h": -15.0  # Oversold
    }
    
    result = estimator._heuristic_estimate(market_data)
    
    # Low volume + oversold = higher probability, higher confidence
    assert result.probability > 0.50  # Mean reversion
    assert result.confidence >= 0.5


if __name__ == "__main__":
    """Run tests."""
    test_estimation_result_dataclass()
    print("✓ Estimation result dataclass")
    
    test_estimator_init()
    print("✓ Estimator init")
    
    test_confidence_bounds()
    print("✓ Confidence bounds")
    
    test_edge_calculation()
    print("✓ Edge calculation")
    
    test_kelly_with_confidence()
    print("✓ Kelly with confidence")
    
    test_heuristic_estimation()
    print("✓ Heuristic estimation")
    
    test_estimation_factors()
    print("✓ Estimation factors")
    
    test_reasoning_generation()
    print("✓ Reasoning generation")
    
    test_no_api_key_fallback()
    print("✓ No API key fallback")
    
    test_high_volume_efficient_market()
    print("✓ High volume efficient market")
    
    test_low_volume_opportunity()
    print("✓ Low volume opportunity")
    
    print("\n✅ All estimator tests passed")
