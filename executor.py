#!/usr/bin/env python3
"""
FRED-SOL: Trade Executor

Executes swaps via Jupiter aggregator.
"""

import asyncio
from dataclasses import dataclass
from typing import Optional
import httpx


@dataclass
class SwapQuote:
    input_mint: str
    output_mint: str
    in_amount: int
    out_amount: int
    price_impact: float
    route: dict


@dataclass 
class SwapResult:
    success: bool
    tx_signature: Optional[str]
    error: Optional[str]


class JupiterExecutor:
    """Execute swaps via Jupiter."""
    
    JUPITER_API = "https://quote-api.jup.ag/v6"
    
    # Common token mints
    SOL = "So11111111111111111111111111111111111111112"
    USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    
    def __init__(self, wallet_address: str):
        self.wallet = wallet_address
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,  # in smallest units
        slippage_bps: int = 50  # 0.5%
    ) -> Optional[SwapQuote]:
        """Get swap quote from Jupiter."""
        try:
            resp = await self.client.get(
                f"{self.JUPITER_API}/quote",
                params={
                    "inputMint": input_mint,
                    "outputMint": output_mint,
                    "amount": str(amount),
                    "slippageBps": slippage_bps,
                }
            )
            
            if resp.status_code != 200:
                print(f"Quote error: {resp.text}")
                return None
            
            data = resp.json()
            return SwapQuote(
                input_mint=input_mint,
                output_mint=output_mint,
                in_amount=int(data.get("inAmount", 0)),
                out_amount=int(data.get("outAmount", 0)),
                price_impact=float(data.get("priceImpactPct", 0)),
                route=data
            )
        except Exception as e:
            print(f"Quote error: {e}")
            return None
    
    async def get_swap_transaction(self, quote: SwapQuote) -> Optional[bytes]:
        """Get serialized swap transaction."""
        try:
            resp = await self.client.post(
                f"{self.JUPITER_API}/swap",
                json={
                    "quoteResponse": quote.route,
                    "userPublicKey": self.wallet,
                    "wrapAndUnwrapSol": True,
                }
            )
            
            if resp.status_code != 200:
                print(f"Swap tx error: {resp.text}")
                return None
            
            data = resp.json()
            import base64
            return base64.b64decode(data.get("swapTransaction", ""))
        except Exception as e:
            print(f"Swap tx error: {e}")
            return None
    
    async def execute_swap(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        sign_callback
    ) -> SwapResult:
        """Full swap execution."""
        # Get quote
        quote = await self.get_quote(input_mint, output_mint, amount)
        if not quote:
            return SwapResult(False, None, "Failed to get quote")
        
        print(f"Quote: {quote.in_amount} -> {quote.out_amount} (impact: {quote.price_impact:.2%})")
        
        # Get transaction
        tx_bytes = await self.get_swap_transaction(quote)
        if not tx_bytes:
            return SwapResult(False, None, "Failed to get transaction")
        
        # Sign transaction
        try:
            signature = sign_callback(tx_bytes)
            # Would send to RPC here
            return SwapResult(True, "simulated_tx_sig", None)
        except Exception as e:
            return SwapResult(False, None, str(e))
    
    async def close(self):
        await self.client.aclose()


async def demo():
    print("🔄 Jupiter Swap Demo")
    
    # Demo wallet (don't use real funds)
    demo_wallet = "4b5f4pmpSXtJrecmvZtyGyGXfwGCANA6UY1VYMjcjs44"
    
    executor = JupiterExecutor(demo_wallet)
    
    try:
        # Get quote for 0.1 SOL -> USDC
        quote = await executor.get_quote(
            input_mint=executor.SOL,
            output_mint=executor.USDC,
            amount=100_000_000  # 0.1 SOL in lamports
        )
        
        if quote:
            usdc_out = quote.out_amount / 1e6
            print(f"0.1 SOL -> {usdc_out:.2f} USDC")
            print(f"Price impact: {quote.price_impact:.4%}")
    finally:
        await executor.close()


if __name__ == "__main__":
    asyncio.run(demo())
