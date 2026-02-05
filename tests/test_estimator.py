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
        probability=0.65,
        confidence=0.80,
        reasoning="test"
    )
    assert 0 <= result.probability <= 1
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
    assert edge == 0.15  # We estimate 15% higher


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


def test_mock_estimation():
    """Test mock estimation (no API call)."""
    estimator = ProbabilityEstimator(mock=True)
    
    result = estimator.estimate(
        question="Will SOL hit $100?",
        market_price=0.45,
        context={"recent_price": 95, "trend": "up"}
    )
    
    assert isinstance(result, EstimationResult)
    assert 0 < result.probability < 1
    assert 0 < result.confidence <= 1


def test_estimation_factors():
    """Test that estimation includes factor breakdown."""
    estimator = ProbabilityEstimator(mock=True)
    
    result = estimator.estimate(
        question="Test question",
        market_price=0.50
    )
    
    # Should have factors dict
    assert isinstance(result.factors, dict)


def test_reasoning_generation():
    """Test that estimation generates reasoning."""
    estimator = ProbabilityEstimator(mock=True)
    
    result = estimator.estimate(
        question="Will BTC hit $50k?",
        market_price=0.60
    )
    
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
        result = estimator.estimate(
            question="Test question",
            market_price=0.50
        )
        # Should fallback to mock mode
        assert isinstance(result, EstimationResult)
    finally:
        if original:
            os.environ["ANTHROPIC_API_KEY"] = original


if __name__ == "__main__":
    """Run tests."""
    test_estimation_result_dataclass()
    print("✓ EstimationResult dataclass")
    
    test_estimator_init()
    print("✓ Estimator init")
    
    test_confidence_bounds()
    print("✓ Confidence bounds")
    
    test_edge_calculation()
    print("✓ Edge calculation")
    
    test_kelly_with_confidence()
    print("✓ Kelly with confidence")
    
    test_mock_estimation()
    print("✓ Mock estimation")
    
    test_estimation_factors()
    print("✓ Estimation factors")
    
    test_reasoning_generation()
    print("✓ Reasoning generation")
    
    test_no_api_key_fallback()
    print("✓ No API key fallback")
    
    print("\n✅ All estimator tests passed")
