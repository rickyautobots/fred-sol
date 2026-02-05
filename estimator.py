#!/usr/bin/env python3
"""
FRED Probability Estimator

LLM-based probability estimation with confidence scoring.
Uses Claude API for market analysis.
"""

import os
import json
from dataclasses import dataclass
from typing import Optional

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


@dataclass
class Estimate:
    probability: float
    confidence: float
    reasoning: str
    raw_response: Optional[str] = None
    factors: Optional[dict] = None


# Alias for backward compatibility with tests
EstimationResult = Estimate


class ProbabilityEstimator:
    """LLM-based probability estimation for trading decisions."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = None
        
        if HAS_ANTHROPIC and self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
    
    def _heuristic_estimate(self, market_data: dict) -> Estimate:
        """Fallback heuristic when LLM unavailable."""
        volume = market_data.get("volume_24h", 0)
        price_change = market_data.get("price_change_24h", 0)
        
        # Simple momentum + mean reversion
        if volume > 1_000_000:
            base_prob = 0.50  # Efficient market
            confidence = 0.3
        elif volume > 100_000:
            base_prob = 0.52
            confidence = 0.5
        else:
            base_prob = 0.55
            confidence = 0.6
        
        # Adjust for momentum
        if price_change > 10:
            base_prob -= 0.03  # Mean reversion
        elif price_change < -10:
            base_prob += 0.03  # Oversold bounce
        
        return Estimate(
            probability=max(0.3, min(0.7, base_prob)),
            confidence=confidence,
            reasoning=f"Heuristic: vol=${volume:,.0f}, change={price_change:.1f}%"
        )
    
    async def estimate(self, market_data: dict) -> Estimate:
        """Estimate probability using LLM or fallback to heuristics."""
        
        if not self.client:
            return self._heuristic_estimate(market_data)
        
        prompt = f"""Analyze this market for short-term trading opportunity:

Market: {market_data.get('symbol', 'Unknown')}
Current Price: ${market_data.get('price', 0):.4f}
24h Volume: ${market_data.get('volume_24h', 0):,.0f}
24h Change: {market_data.get('price_change_24h', 0):.2f}%
Market Cap: ${market_data.get('market_cap', 0):,.0f}

Task: Estimate the probability that this asset will be higher in 4 hours.

Respond in JSON format:
{{
    "probability": 0.XX,  // 0.0 to 1.0
    "confidence": 0.XX,   // 0.0 to 1.0 (how confident in estimate)
    "reasoning": "Brief explanation"
}}

Consider:
- Volume trends (higher = more efficient pricing)
- Recent momentum (mean reversion vs trend following)
- Market cap (smaller = more volatile)
- Time of day effects

Be calibrated - if uncertain, probability should be near 0.5 with low confidence."""

        try:
            response = self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            text = response.content[0].text
            
            # Parse JSON from response
            import re
            json_match = re.search(r'\{[^}]+\}', text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return Estimate(
                    probability=float(data.get("probability", 0.5)),
                    confidence=float(data.get("confidence", 0.5)),
                    reasoning=data.get("reasoning", "LLM analysis"),
                    raw_response=text
                )
        except Exception as e:
            print(f"LLM estimation failed: {e}")
        
        return self._heuristic_estimate(market_data)
    
    def batch_estimate(self, markets: list) -> list:
        """Estimate probabilities for multiple markets."""
        import asyncio
        
        async def run_batch():
            return [await self.estimate(m) for m in markets]
        
        return asyncio.run(run_batch())


# Convenience function
async def estimate_probability(market_data: dict, api_key: Optional[str] = None) -> Estimate:
    """Quick estimation for a single market."""
    estimator = ProbabilityEstimator(api_key)
    return await estimator.estimate(market_data)


if __name__ == "__main__":
    # Test
    import asyncio
    
    test_market = {
        "symbol": "SOL/USDC",
        "price": 96.42,
        "volume_24h": 500_000,
        "price_change_24h": -2.1,
        "market_cap": 45_000_000_000
    }
    
    async def test():
        estimator = ProbabilityEstimator()
        result = await estimator.estimate(test_market)
        print(f"Probability: {result.probability:.2%}")
        print(f"Confidence: {result.confidence:.2%}")
        print(f"Reasoning: {result.reasoning}")
    
    asyncio.run(test())
