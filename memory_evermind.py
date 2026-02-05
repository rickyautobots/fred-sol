#!/usr/bin/env python3
"""
FRED + EverMemOS Integration

Persistent memory for trading decisions.
Tracks trades, outcomes, and learns patterns.

For EverMind Memory Genesis Competition 2026.
"""

import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


@dataclass
class TradeMemory:
    """A memory of a trade decision."""
    symbol: str
    action: str  # BUY, SELL, SKIP
    reasoning: str
    probability: float
    confidence: float
    size_usd: float
    price: float
    outcome: Optional[str] = None  # WIN, LOSS, PENDING
    pnl: Optional[float] = None
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_content(self) -> str:
        """Convert to natural language for memory storage."""
        outcome_str = ""
        if self.outcome:
            outcome_str = f" Outcome: {self.outcome} with PnL ${self.pnl:.2f}." if self.pnl else f" Outcome: {self.outcome}."
        
        return (
            f"Trade decision on {self.symbol}: {self.action}. "
            f"Reasoning: {self.reasoning}. "
            f"Estimated probability: {self.probability:.1%}, confidence: {self.confidence:.1%}. "
            f"Position size: ${self.size_usd:.2f} at price ${self.price:.4f}.{outcome_str}"
        )


class EverMindMemory:
    """Interface to EverMemOS for persistent trading memory."""
    
    def __init__(self, api_url: Optional[str] = None, user_id: str = "fred_agent"):
        self.api_url = api_url or os.getenv("EVERMEMOS_URL", "http://localhost:8001/api/v1")
        self.user_id = user_id
        self.enabled = HAS_HTTPX
        self._client = None
    
    @property
    def client(self):
        if self._client is None and self.enabled:
            self._client = httpx.Client(timeout=30)
        return self._client
    
    def store_trade(self, trade: TradeMemory) -> bool:
        """Store a trade decision in memory."""
        if not self.enabled:
            print("[Memory] EverMind disabled (no httpx)")
            return False
        
        try:
            response = self.client.post(
                f"{self.api_url}/memories",
                json={
                    "message_id": f"trade_{trade.timestamp}_{trade.symbol}".replace(":", "").replace("-", ""),
                    "create_time": trade.timestamp,
                    "sender": self.user_id,
                    "content": trade.to_content(),
                    "role": "assistant",
                    "metadata": {
                        "type": "trade_decision",
                        "symbol": trade.symbol,
                        "action": trade.action,
                        "probability": trade.probability,
                        "confidence": trade.confidence,
                        "outcome": trade.outcome,
                        "pnl": trade.pnl
                    }
                }
            )
            return response.status_code == 200
        except Exception as e:
            print(f"[Memory] Store failed: {e}")
            return False
    
    def update_outcome(self, symbol: str, outcome: str, pnl: float) -> bool:
        """Update a trade with its outcome."""
        # Store as new memory (outcome update)
        memory = TradeMemory(
            symbol=symbol,
            action="OUTCOME",
            reasoning=f"Trade closed with {outcome}",
            probability=0,
            confidence=1.0,
            size_usd=0,
            price=0,
            outcome=outcome,
            pnl=pnl
        )
        return self.store_trade(memory)
    
    def recall_similar(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Recall similar trading situations from memory."""
        if not self.enabled:
            return []
        
        try:
            response = self.client.get(
                f"{self.api_url}/memories/search",
                json={
                    "query": query,
                    "user_id": self.user_id,
                    "memory_types": ["episodic_memory"],
                    "retrieve_method": "hybrid",
                    "limit": limit
                }
            )
            if response.status_code == 200:
                result = response.json().get("result", {})
                return result.get("memories", [])
        except Exception as e:
            print(f"[Memory] Recall failed: {e}")
        
        return []
    
    def get_trading_patterns(self, symbol: str) -> Dict[str, Any]:
        """Analyze past trades for a symbol."""
        memories = self.recall_similar(
            f"Past trades on {symbol} and their outcomes",
            limit=20
        )
        
        wins = 0
        losses = 0
        _total_pnl = 0.0
        
        for mem in memories:
            content = str(mem)
            if "WIN" in content:
                wins += 1
            elif "LOSS" in content:
                losses += 1
            # Could parse PnL from content
        
        return {
            "symbol": symbol,
            "trades_recalled": len(memories),
            "wins": wins,
            "losses": losses,
            "win_rate": wins / (wins + losses) if (wins + losses) > 0 else 0,
            "memories": memories[:3]  # Sample
        }
    
    def should_trade(self, symbol: str, current_probability: float) -> Dict[str, Any]:
        """Use memory to adjust trading decision."""
        patterns = self.get_trading_patterns(symbol)
        
        # Simple adjustment based on historical performance
        adjustment = 0.0
        confidence_boost = 0.0
        
        if patterns["trades_recalled"] > 5:
            if patterns["win_rate"] > 0.6:
                adjustment = 0.02  # Slightly more bullish
                confidence_boost = 0.1
            elif patterns["win_rate"] < 0.4:
                adjustment = -0.02  # More cautious
                confidence_boost = -0.1
        
        return {
            "original_probability": current_probability,
            "adjusted_probability": current_probability + adjustment,
            "confidence_adjustment": confidence_boost,
            "reasoning": f"Based on {patterns['trades_recalled']} past trades with {patterns['win_rate']:.0%} win rate",
            "patterns": patterns
        }
    
    def close(self):
        """Cleanup."""
        if self._client:
            self._client.close()


# Convenience functions
_memory: Optional[EverMindMemory] = None

def get_memory() -> EverMindMemory:
    global _memory
    if _memory is None:
        _memory = EverMindMemory()
    return _memory


async def remember_trade(trade: TradeMemory) -> bool:
    """Store a trade in memory."""
    return get_memory().store_trade(trade)


async def recall_for_decision(symbol: str, probability: float) -> Dict[str, Any]:
    """Use memory to inform trading decision."""
    return get_memory().should_trade(symbol, probability)


if __name__ == "__main__":
    # Test
    memory = EverMindMemory()
    
    # Store a trade
    trade = TradeMemory(
        symbol="SOL/USDC",
        action="BUY",
        reasoning="High volume, positive momentum",
        probability=0.58,
        confidence=0.65,
        size_usd=100,
        price=96.42
    )
    
    print(f"Storing trade: {trade.to_content()}")
    result = memory.store_trade(trade)
    print(f"Stored: {result}")
    
    # Query patterns
    patterns = memory.get_trading_patterns("SOL/USDC")
    print(f"Patterns: {patterns}")
    
    # Get trading recommendation
    recommendation = memory.should_trade("SOL/USDC", 0.55)
    print(f"Recommendation: {recommendation}")
