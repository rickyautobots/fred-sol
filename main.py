#!/usr/bin/env python3
"""
FRED-SOL: Main Entry Point

Run the full autonomous trading loop.
"""

import asyncio
import os
import sys
from datetime import datetime

from scanner import SolanaScanner, Market
from wallet import SolanaWallet
from executor import JupiterExecutor


class FredSol:
    """Autonomous Solana trading agent."""
    
    def __init__(self):
        self.scanner = SolanaScanner()
        self.wallet = SolanaWallet()
        self.executor = None
        self.min_edge = 0.05  # 5% minimum edge to trade
        self.max_position_pct = 0.10  # 10% max position
        
    async def initialize(self):
        """Initialize components."""
        if not self.wallet.address:
            print("❌ No wallet configured")
            return False
        
        self.executor = JupiterExecutor(self.wallet.address)
        
        # Check balances
        info = await self.wallet.get_balance()
        print(f"💰 Wallet: {self.wallet.address[:8]}...")
        print(f"   SOL:  {info.balance_sol:.4f}")
        print(f"   USDC: {info.balance_usdc:.2f}")
        
        if info.balance_usdc < 1:
            print("⚠️  Low USDC balance")
        
        return True
    
    async def estimate_probability(self, market: Market) -> dict:
        """LLM probability estimation (simplified for demo)."""
        # In production, this calls Claude API
        # For now, use simple heuristics
        
        volume = market.volume_24h
        
        # Higher volume = more efficient market = closer to 0.5
        if volume > 1_000_000:
            base_prob = 0.50
            confidence = 0.3
        elif volume > 100_000:
            base_prob = 0.52
            confidence = 0.5
        else:
            base_prob = 0.55
            confidence = 0.6
        
        return {
            "probability": base_prob,
            "confidence": confidence,
            "reasoning": f"Volume-based heuristic (${volume:,.0f} 24h)"
        }
    
    def kelly_size(self, prob: float, odds: float, confidence: float) -> float:
        """Kelly criterion position sizing."""
        if odds <= 1 or prob <= 0 or prob >= 1:
            return 0
        
        b = odds - 1
        f = (b * prob - (1 - prob)) / b
        
        # Half-Kelly with confidence adjustment
        adjusted = f * confidence * 0.5
        
        return max(0, min(adjusted, self.max_position_pct))
    
    async def scan_and_trade(self):
        """Single trading cycle."""
        print(f"\n{'='*50}")
        print(f"🔍 Scanning markets... {datetime.now().strftime('%H:%M:%S')}")
        
        markets = await self.scanner.scan_all(limit=10)
        print(f"   Found {len(markets)} markets")
        
        opportunities = []
        
        for market in markets:
            estimate = await self.estimate_probability(market)
            
            # Calculate edge (simplified)
            market_prob = 0.5  # Assume 50/50 for spot markets
            our_prob = estimate["probability"]
            edge = abs(our_prob - market_prob)
            
            if edge >= self.min_edge and estimate["confidence"] > 0.4:
                size = self.kelly_size(our_prob, 2.0, estimate["confidence"])
                if size > 0.01:
                    opportunities.append({
                        "market": market,
                        "edge": edge,
                        "size": size,
                        "estimate": estimate
                    })
        
        if not opportunities:
            print("   No opportunities this cycle")
            return
        
        print(f"\n📊 {len(opportunities)} opportunities found:")
        
        for opp in opportunities[:3]:  # Top 3
            m = opp["market"]
            print(f"\n   [{m.source}] {m.question}")
            print(f"   Edge: {opp['edge']:.1%} | Size: {opp['size']:.1%}")
            print(f"   Reason: {opp['estimate']['reasoning']}")
    
    async def run_loop(self, interval_seconds: int = 60):
        """Continuous trading loop."""
        print("🤖 FRED-SOL Starting...")
        
        if not await self.initialize():
            return
        
        print(f"\n⏰ Running every {interval_seconds}s (Ctrl+C to stop)\n")
        
        try:
            while True:
                await self.scan_and_trade()
                await asyncio.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down...")
        finally:
            await self.cleanup()
    
    async def run_once(self):
        """Single scan cycle."""
        print("🤖 FRED-SOL Single Run")
        
        if not await self.initialize():
            return
        
        await self.scan_and_trade()
        await self.cleanup()
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.scanner.close()
        if self.executor:
            await self.executor.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="FRED-SOL: Autonomous Solana Trading Agent")
    parser.add_argument("--backtest", action="store_true", help="Run backtesting engine")
    parser.add_argument("--loop", action="store_true", help="Run continuous trading loop")
    parser.add_argument("--interval", type=int, default=60, help="Loop interval in seconds")
    args = parser.parse_args()
    
    if args.backtest:
        from backtest import main as backtest_main
        backtest_main()
    elif args.loop:
        agent = FredSol()
        asyncio.run(agent.run_loop(args.interval))
    else:
        agent = FredSol()
        asyncio.run(agent.run_once())


if __name__ == "__main__":
    main()
