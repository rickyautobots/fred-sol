#!/usr/bin/env python3
"""
FRED-SOL: Solana Market Scanner
"""

import asyncio
from dataclasses import dataclass
from typing import List, Optional
import httpx


@dataclass
class Market:
    id: str
    question: str
    outcomes: List[dict]
    volume_24h: float
    liquidity: float
    source: str


class SolanaScanner:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def fetch_jupiter_prices(self) -> List[Market]:
        """Fetch token prices from Jupiter."""
        tokens = {
            "So11111111111111111111111111111111111111112": "SOL",
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
            "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263": "BONK",
        }
        
        try:
            resp = await self.client.get(
                "https://api.jup.ag/price/v2",
                params={"ids": ",".join(tokens.keys())}
            )
            data = resp.json()
            
            markets = []
            for mint, info in data.get("data", {}).items():
                symbol = tokens.get(mint, mint[:8])
                markets.append(Market(
                    id=f"jup_{symbol}",
                    question=f"{symbol}/USD",
                    outcomes=[{"name": "price", "value": info.get("price", 0)}],
                    volume_24h=0,
                    liquidity=0,
                    source="jupiter"
                ))
            return markets
        except Exception as e:
            print(f"Jupiter error: {e}")
            return []
    
    async def fetch_birdeye_markets(self) -> List[Market]:
        """Fetch trending tokens from Birdeye."""
        try:
            resp = await self.client.get(
                "https://public-api.birdeye.so/defi/tokenlist",
                params={"sort_by": "v24hUSD", "sort_type": "desc", "limit": 10},
                headers={"x-chain": "solana"}
            )
            data = resp.json()
            
            markets = []
            for token in data.get("data", {}).get("tokens", [])[:10]:
                markets.append(Market(
                    id=f"bird_{token.get('symbol', 'UNK')}",
                    question=f"{token.get('symbol', 'UNK')}/USD",
                    outcomes=[{"name": "price", "value": token.get("price", 0)}],
                    volume_24h=token.get("v24hUSD", 0),
                    liquidity=token.get("liquidity", 0),
                    source="birdeye"
                ))
            return markets
        except Exception as e:
            print(f"Birdeye error: {e}")
            return []
    
    async def scan_all(self, limit: int = 20) -> List[Market]:
        results = await asyncio.gather(
            self.fetch_jupiter_prices(),
            self.fetch_birdeye_markets(),
            return_exceptions=True
        )
        
        markets = []
        for r in results:
            if isinstance(r, list):
                markets.extend(r)
        
        markets.sort(key=lambda m: m.volume_24h, reverse=True)
        return markets[:limit]
    
    async def close(self):
        await self.client.aclose()


async def main():
    print("🔍 FRED-SOL Scanner")
    scanner = SolanaScanner()
    
    try:
        markets = await scanner.scan_all()
        print(f"\nFound {len(markets)} markets:\n")
        for m in markets:
            price = m.outcomes[0].get("value", 0) if m.outcomes else 0
            print(f"[{m.source}] {m.question}: ${price:.6f} (vol: ${m.volume_24h:,.0f})")
    finally:
        await scanner.close()


if __name__ == "__main__":
    asyncio.run(main())
