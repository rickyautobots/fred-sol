#!/usr/bin/env python3
"""
FRED-SOL: LLM Probability Estimator

Uses Claude to estimate market probabilities.
"""

import os
import json
from dataclasses import dataclass
from typing import Optional
import httpx


@dataclass
class Estimate:
    probability: float  # 0-1
    confidence: float   # 0-1
    direction: str      # 'long', 'short', 'neutral'
    reasoning: str
    edge: float         # vs market price


class ProbabilityEstimator:
    """LLM-based market analysis."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    
    async def estimate(
        self,
        symbol: str,
        current_price: float,
        volume_24h: float,
        context: str = ""
    ) -> Estimate:
        """Get probability estimate from Claude."""
        
        prompt = f"""Analyze this Solana token for short-term trading:

Symbol: {symbol}
Current Price: ${current_price:.6f}
24h Volume: ${volume_24h:,.0f}
{f'Context: {context}' if context else ''}

Provide trading analysis:
1. Probability of 5%+ upside in next 24h (0.0-1.0)
2. Your confidence in this estimate (0.0-1.0)  
3. Recommended direction: long, short, or neutral
4. Brief reasoning (1-2 sentences)

Respond ONLY with valid JSON:
{{"probability": 0.XX, "confidence": 0.XX, "direction": "long|short|neutral", "reasoning": "..."}}
"""
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": "claude-3-haiku-20240307",
                        "max_tokens": 200,
                        "messages": [{"role": "user", "content": prompt}]
                    }
                )
                
                if resp.status_code == 200:
                    content = resp.json()["content"][0]["text"]
                    # Extract JSON
                    start = content.find("{")
                    end = content.rfind("}") + 1
                    if start >= 0 and end > start:
                        data = json.loads(content[start:end])
                        
                        # Calculate edge vs neutral assumption
                        prob = data.get("probability", 0.5)
                        edge = prob - 0.5  # Edge vs random
                        
                        return Estimate(
                            probability=prob,
                            confidence=data.get("confidence", 0.5),
                            direction=data.get("direction", "neutral"),
                            reasoning=data.get("reasoning", ""),
                            edge=edge
                        )
        except Exception as e:
            print(f"Estimation error: {e}")
        
        # Fallback
        return Estimate(
            probability=0.5,
            confidence=0.3,
            direction="neutral",
            reasoning="Unable to analyze - using neutral stance",
            edge=0.0
        )


class PositionSizer:
    """Kelly criterion position sizing."""
    
    @staticmethod
    def calculate(
        probability: float,
        confidence: float,
        bankroll: float,
        max_position_pct: float = 0.20
    ) -> float:
        """
        Calculate position size using fractional Kelly.
        
        Returns position size in USD.
        """
        if probability <= 0.5 or confidence < 0.4:
            return 0.0
        
        # Assume 2:1 odds for simplicity (can profit 100% or lose 100%)
        odds = 2.0
        
        # Kelly formula
        b = odds - 1  # Net odds
        p = probability
        q = 1 - p
        
        kelly = (b * p - q) / b
        
        # Apply confidence as fractional Kelly
        # Also use half-Kelly for safety
        fraction = kelly * confidence * 0.5
        
        # Cap at max position
        fraction = max(0, min(fraction, max_position_pct))
        
        return bankroll * fraction


async def demo():
    print("🧠 FRED-SOL Estimator Demo")
    print("=" * 40)
    
    estimator = ProbabilityEstimator()
    sizer = PositionSizer()
    
    # Demo analysis
    tokens = [
        ("SOL", 95.50, 1_500_000_000),
        ("BONK", 0.00001234, 50_000_000),
        ("JTO", 2.85, 30_000_000),
    ]
    
    bankroll = 1000.0  # $1000 USDC
    
    for symbol, price, volume in tokens:
        print(f"\n📊 Analyzing {symbol}...")
        
        estimate = await estimator.estimate(symbol, price, volume)
        
        print(f"   Probability: {estimate.probability:.1%}")
        print(f"   Confidence: {estimate.confidence:.1%}")
        print(f"   Direction: {estimate.direction}")
        print(f"   Edge: {estimate.edge:+.1%}")
        print(f"   Reasoning: {estimate.reasoning}")
        
        if estimate.direction == "long" and estimate.edge > 0.05:
            position = sizer.calculate(
                estimate.probability,
                estimate.confidence,
                bankroll
            )
            if position > 0:
                print(f"   💰 Position: ${position:.2f} ({position/bankroll:.1%} of bankroll)")


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())
