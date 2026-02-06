#!/usr/bin/env python3
"""
FRED-SOL: Native Solana Integration
Direct on-chain trading via Solana RPC

Built: 2026-02-06 06:50 CST by Ricky
"""

import asyncio
import json
import base64
import struct
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from pathlib import Path

import httpx

# Solana constants
LAMPORTS_PER_SOL = 1_000_000_000
MAINNET_RPC = "https://api.mainnet-beta.solana.com"
DEVNET_RPC = "https://api.devnet.solana.com"

# Token program IDs
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
ASSOCIATED_TOKEN_PROGRAM = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"

# Common token mints
TOKENS = {
    "SOL": "So11111111111111111111111111111111111111112",
    "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
    "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "JUP": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
    "WIF": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
}


@dataclass
class TokenBalance:
    """Token balance with metadata"""
    mint: str
    symbol: str
    balance: float
    decimals: int
    usd_value: Optional[float] = None


@dataclass
class Transaction:
    """Solana transaction result"""
    signature: str
    slot: int
    success: bool
    fee: int
    error: Optional[str] = None


class SolanaClient:
    """
    Async Solana RPC client for FRED trading operations
    """
    
    def __init__(self, rpc_url: str = MAINNET_RPC, commitment: str = "confirmed"):
        self.rpc_url = rpc_url
        self.commitment = commitment
        self.client = httpx.AsyncClient(timeout=30.0)
        self._request_id = 0
    
    async def _rpc(self, method: str, params: List = None) -> Dict:
        """Make JSON-RPC call"""
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or []
        }
        
        resp = await self.client.post(self.rpc_url, json=payload)
        data = resp.json()
        
        if "error" in data:
            raise Exception(f"RPC error: {data['error']}")
        
        return data.get("result")
    
    async def get_balance(self, pubkey: str) -> float:
        """Get SOL balance for address"""
        result = await self._rpc("getBalance", [pubkey, {"commitment": self.commitment}])
        lamports = result.get("value", 0)
        return lamports / LAMPORTS_PER_SOL
    
    async def get_token_accounts(self, owner: str) -> List[TokenBalance]:
        """Get all SPL token balances for owner"""
        result = await self._rpc("getTokenAccountsByOwner", [
            owner,
            {"programId": TOKEN_PROGRAM},
            {"encoding": "jsonParsed", "commitment": self.commitment}
        ])
        
        balances = []
        for account in result.get("value", []):
            info = account["account"]["data"]["parsed"]["info"]
            mint = info["mint"]
            token_amount = info["tokenAmount"]
            
            # Find symbol
            symbol = next((s for s, m in TOKENS.items() if m == mint), mint[:8])
            
            balances.append(TokenBalance(
                mint=mint,
                symbol=symbol,
                balance=float(token_amount["uiAmount"] or 0),
                decimals=token_amount["decimals"]
            ))
        
        return balances
    
    async def get_slot(self) -> int:
        """Get current slot"""
        return await self._rpc("getSlot", [{"commitment": self.commitment}])
    
    async def get_recent_blockhash(self) -> str:
        """Get recent blockhash for transaction"""
        result = await self._rpc("getLatestBlockhash", [{"commitment": self.commitment}])
        return result["value"]["blockhash"]
    
    async def get_transaction(self, signature: str) -> Optional[Dict]:
        """Get transaction details"""
        return await self._rpc("getTransaction", [
            signature,
            {"encoding": "jsonParsed", "commitment": self.commitment}
        ])
    
    async def simulate_transaction(self, tx_base64: str) -> Dict:
        """Simulate transaction before sending"""
        return await self._rpc("simulateTransaction", [
            tx_base64,
            {"encoding": "base64", "commitment": self.commitment}
        ])
    
    async def send_transaction(self, tx_base64: str) -> str:
        """Send signed transaction"""
        return await self._rpc("sendTransaction", [
            tx_base64,
            {"encoding": "base64", "preflightCommitment": self.commitment}
        ])
    
    async def close(self):
        await self.client.aclose()


class JupiterSwap:
    """
    Jupiter aggregator integration for best-price swaps
    """
    
    BASE_URL = "https://quote-api.jup.ag/v6"
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 50
    ) -> Dict:
        """Get swap quote from Jupiter"""
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount),
            "slippageBps": slippage_bps
        }
        
        resp = await self.client.get(f"{self.BASE_URL}/quote", params=params)
        return resp.json()
    
    async def get_swap_transaction(
        self,
        quote: Dict,
        user_pubkey: str,
        wrap_unwrap_sol: bool = True
    ) -> Dict:
        """Get swap transaction from quote"""
        payload = {
            "quoteResponse": quote,
            "userPublicKey": user_pubkey,
            "wrapAndUnwrapSol": wrap_unwrap_sol
        }
        
        resp = await self.client.post(f"{self.BASE_URL}/swap", json=payload)
        return resp.json()
    
    async def close(self):
        await self.client.aclose()


class FREDSolanaTrader:
    """
    FRED trading agent with native Solana integration
    
    Features:
    - Direct RPC balance queries
    - Jupiter swap execution
    - Transaction simulation before send
    - Multi-token portfolio tracking
    """
    
    def __init__(
        self,
        wallet_pubkey: str,
        private_key_path: Optional[str] = None,
        rpc_url: str = MAINNET_RPC
    ):
        self.wallet = wallet_pubkey
        self.private_key_path = private_key_path
        self.solana = SolanaClient(rpc_url)
        self.jupiter = JupiterSwap()
        
    async def get_portfolio(self) -> Dict[str, Any]:
        """Get full portfolio snapshot"""
        sol_balance = await self.solana.get_balance(self.wallet)
        token_balances = await self.solana.get_token_accounts(self.wallet)
        
        return {
            "wallet": self.wallet,
            "sol": sol_balance,
            "tokens": [
                {
                    "symbol": t.symbol,
                    "balance": t.balance,
                    "mint": t.mint
                }
                for t in token_balances if t.balance > 0
            ],
            "slot": await self.solana.get_slot()
        }
    
    async def quote_swap(
        self,
        from_token: str,
        to_token: str,
        amount: float
    ) -> Dict:
        """Get swap quote"""
        from_mint = TOKENS.get(from_token, from_token)
        to_mint = TOKENS.get(to_token, to_token)
        
        # Get decimals (default 9 for SOL, 6 for USDC)
        decimals = 6 if from_token in ["USDC", "USDT"] else 9
        amount_raw = int(amount * (10 ** decimals))
        
        quote = await self.jupiter.get_quote(from_mint, to_mint, amount_raw)
        
        return {
            "input": from_token,
            "output": to_token,
            "input_amount": amount,
            "output_amount": int(quote.get("outAmount", 0)) / (10 ** decimals),
            "price_impact": quote.get("priceImpactPct", 0),
            "route": quote.get("routePlan", [])
        }
    
    async def execute_swap(
        self,
        from_token: str,
        to_token: str,
        amount: float,
        dry_run: bool = True
    ) -> Dict:
        """Execute swap via Jupiter"""
        from_mint = TOKENS.get(from_token, from_token)
        to_mint = TOKENS.get(to_token, to_token)
        decimals = 6 if from_token in ["USDC", "USDT"] else 9
        amount_raw = int(amount * (10 ** decimals))
        
        # Get quote
        quote = await self.jupiter.get_quote(from_mint, to_mint, amount_raw)
        
        if dry_run:
            return {
                "status": "simulated",
                "quote": quote,
                "message": "Dry run - transaction not sent"
            }
        
        # Get swap transaction
        swap_tx = await self.jupiter.get_swap_transaction(quote, self.wallet)
        
        if "error" in swap_tx:
            return {"status": "error", "error": swap_tx["error"]}
        
        # In production: sign and send transaction
        # For now, return the unsigned transaction
        return {
            "status": "ready",
            "transaction": swap_tx.get("swapTransaction"),
            "message": "Transaction ready for signing"
        }
    
    async def close(self):
        await self.solana.close()
        await self.jupiter.close()


async def main():
    """Demo the Solana integration"""
    import argparse
    
    parser = argparse.ArgumentParser(description="FRED Solana Integration")
    parser.add_argument("--wallet", default="EamKq5ZhE2eZP6Z2LgAps9RUeNTem8K2udSeYNWuCPKF")
    parser.add_argument("--rpc", default=MAINNET_RPC)
    args = parser.parse_args()
    
    print("=" * 60)
    print("FRED-SOL: Solana Integration Demo")
    print("=" * 60)
    
    trader = FREDSolanaTrader(args.wallet, rpc_url=args.rpc)
    
    try:
        # Get portfolio
        print(f"\nWallet: {args.wallet[:12]}...")
        portfolio = await trader.get_portfolio()
        
        print(f"SOL Balance: {portfolio['sol']:.4f} SOL")
        print(f"Current Slot: {portfolio['slot']}")
        
        if portfolio['tokens']:
            print("\nToken Balances:")
            for token in portfolio['tokens']:
                print(f"  {token['symbol']}: {token['balance']:.4f}")
        
        # Demo swap quote
        print("\n--- Swap Quote Demo ---")
        quote = await trader.quote_swap("SOL", "USDC", 1.0)
        print(f"1 SOL → {quote['output_amount']:.2f} USDC")
        print(f"Price Impact: {float(quote['price_impact']):.4f}%")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await trader.close()
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
