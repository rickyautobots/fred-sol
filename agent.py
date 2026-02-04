#!/usr/bin/env python3
"""
FRED-SOL: Autonomous Solana Trading Agent

Main agent loop that:
1. Scans markets
2. Estimates probabilities via LLM
3. Calculates position sizes (Kelly criterion)
4. Executes trades
"""

import asyncio
import os
from dataclasses import dataclass
from typing import Optional
import httpx

from scanner import SolanaScanner, Market


@dataclass
class TradeSignal:
    """Trading decision output."""
    market: Market
    direction: str  # 'long' or 'short'
    confidence: float  # 0-1
    edge: float  # estimated edge over market
    position_pct: float  # % of bankroll to risk
    reasoning: str


class ProbabilityEstimator:
    """LLM-based probability estimation."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def estimate(self, market: Market) -> dict:
        """Estimate probability using Claude."""
        prompt = f"""Analyze this trading opportunity:

Market: {market.question}
Current outcomes: {market.outcomes}
24h Volume: ${market.volume_24h:,.2f}
Liquidity: ${market.liquidity:,.2f}
Source: {market.source}

Provide:
1. Your probability estimate (0-1) for the primary outcome
2. Confidence level (0-1)
3. Brief reasoning (1-2 sentences)

Respond in JSON format:
{{"probability": 0.XX, "confidence": 0.XX, "reasoning": "..."}}
"""
        
        try:
            resp = await self.client.post(
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
                # Parse JSON from response
                import json
                start = content.find("{")
                end = content.rfind("}") + 1
                return json.loads(content[start:end])
        except Exception as e:
            print(f"Estimation error: {e}")
        
        return {"probability": 0.5, "confidence": 0.3, "reasoning": "Fallback estimate"}
    
    async def close(self):
        await self.client.aclose()


class PositionSizer:
    """Kelly criterion position sizing."""
    
    @staticmethod
    def kelly(probability: float, odds: float, confidence: float = 1.0) -> float:
        """
        Calculate Kelly fraction.
        
        Args:
            probability: Estimated win probability
            odds: Payout odds (e.g., 2.0 for even money)
            confidence: Confidence multiplier (fractional Kelly)
        
        Returns:
            Fraction of bankroll to bet
        """
        if odds <= 1 or probability <= 0 or probability >= 1:
            return 0.0
        
        # Kelly formula: f* = (bp - q) / b
        # where b = odds - 1, p = win prob, q = lose prob
        b = odds - 1
        p = probability
        q = 1 - p
        
        kelly_fraction = (b * p - q) / b
        
        # Apply confidence as fractional Kelly
        adjusted = kelly_fraction * confidence * 0.5  # Half-Kelly for safety
        
        # Cap at 20% of bankroll
        return max(0, min(adjusted, 0.20))


class FredSolAgent:
    """Main trading agent."""
    
    def __init__(self, bankroll_usdc: float = 100.0):
        self.bankroll = bankroll_usdc
        self.scanner = SolanaScanner()
        self.estimator = ProbabilityEstimator()
        self.sizer = PositionSizer()
        self.positions = []
    
    async def scan_opportunities(self, limit: int = 5) -> list[TradeSignal]:
        """Scan markets and generate trade signals."""
        markets = await self.scanner.scan_all(limit=limit)
        signals = []
        
        for market in markets:
            # Get LLM estimate
            estimate = await self.estimator.estimate(market)
            
            # Calculate edge
            market_prob = market.outcomes[0].get("price", 0.5) if market.outcomes else 0.5
            our_prob = estimate["probability"]
            edge = our_prob - market_prob
            
            # Only signal if positive edge and sufficient confidence
            if edge > 0.05 and estimate["confidence"] > 0.5:
                # Calculate position size
                odds = 1 / market_prob if market_prob > 0 else 2.0
                position_pct = self.sizer.kelly(our_prob, odds, estimate["confidence"])
                
                if position_pct > 0.01:  # Minimum 1% position
                    signals.append(TradeSignal(
                        market=market,
                        direction="long",
                        confidence=estimate["confidence"],
                        edge=edge,
                        position_pct=position_pct,
                        reasoning=estimate["reasoning"]
                    ))
        
        return signals
    
    async def run_once(self):
        """Single agent iteration."""
        print("\n🤖 FRED-SOL Agent Cycle")
        print("=" * 50)
        
        signals = await self.scan_opportunities(limit=5)
        
        if not signals:
            print("No opportunities found this cycle.")
            return
        
        print(f"\n📊 Found {len(signals)} opportunities:\n")
        
        for i, sig in enumerate(signals, 1):
            position_usdc = self.bankroll * sig.position_pct
            print(f"{i}. {sig.market.question}")
            print(f"   Direction: {sig.direction.upper()}")
            print(f"   Edge: {sig.edge:.1%}")
            print(f"   Confidence: {sig.confidence:.1%}")
            print(f"   Position: ${position_usdc:.2f} ({sig.position_pct:.1%} of bankroll)")
            print(f"   Reasoning: {sig.reasoning}")
            print()
    
    async def close(self):
        await self.scanner.close()
        await self.estimator.close()


async def main():
    """Run agent demo."""
    agent = FredSolAgent(bankroll_usdc=100.0)
    
    try:
        await agent.run_once()
    finally:
        await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
