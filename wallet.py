#!/usr/bin/env python3
"""
FRED-SOL: Solana Wallet Operations

Handles keypair management and transaction signing.
"""

import os
import json
import base58
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class WalletInfo:
    address: str
    balance_sol: float
    balance_usdc: float


class SolanaWallet:
    """Manages Solana wallet operations."""
    
    USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    
    def __init__(self, keypair_path: Optional[str] = None):
        self.keypair_path = keypair_path or os.path.expanduser(
            "~/.config/solana/ricky-wallet.json"
        )
        self._keypair = None
        self._address = None
    
    def load_keypair(self) -> bool:
        """Load keypair from file."""
        try:
            with open(self.keypair_path) as f:
                data = json.load(f)
            
            if isinstance(data, list):
                # Standard Solana CLI format [u8; 64]
                secret = bytes(data[:32])
                self._keypair = data
                # Derive public key (first 32 bytes of ed25519 keypair are private)
                from hashlib import sha512
                import nacl.signing
                signing_key = nacl.signing.SigningKey(secret)
                self._address = base58.b58encode(
                    bytes(signing_key.verify_key)
                ).decode()
                return True
        except Exception as e:
            print(f"Keypair load error: {e}")
        return False
    
    @property
    def address(self) -> Optional[str]:
        if not self._address:
            self.load_keypair()
        return self._address
    
    async def get_balance(self, rpc_url: str = "https://api.mainnet-beta.solana.com") -> WalletInfo:
        """Fetch wallet balances."""
        import httpx
        
        async with httpx.AsyncClient() as client:
            # Get SOL balance
            sol_resp = await client.post(rpc_url, json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": [self.address]
            })
            sol_data = sol_resp.json()
            sol_balance = sol_data.get("result", {}).get("value", 0) / 1e9
            
            # Get USDC balance (SPL token)
            usdc_resp = await client.post(rpc_url, json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenAccountsByOwner",
                "params": [
                    self.address,
                    {"mint": self.USDC_MINT},
                    {"encoding": "jsonParsed"}
                ]
            })
            usdc_data = usdc_resp.json()
            usdc_balance = 0
            
            accounts = usdc_data.get("result", {}).get("value", [])
            for acc in accounts:
                info = acc.get("account", {}).get("data", {}).get("parsed", {}).get("info", {})
                amount = info.get("tokenAmount", {}).get("uiAmount", 0)
                usdc_balance += amount or 0
            
            return WalletInfo(
                address=self.address,
                balance_sol=sol_balance,
                balance_usdc=usdc_balance
            )
    
    def sign_transaction(self, tx_bytes: bytes) -> bytes:
        """Sign a transaction."""
        if not self._keypair:
            self.load_keypair()
        
        import nacl.signing
        secret = bytes(self._keypair[:32])
        signing_key = nacl.signing.SigningKey(secret)
        signed = signing_key.sign(tx_bytes)
        return signed.signature


async def main():
    print("🔐 FRED-SOL Wallet")
    
    wallet = SolanaWallet()
    
    if wallet.address:
        print(f"Address: {wallet.address}")
        
        info = await wallet.get_balance()
        print(f"SOL: {info.balance_sol:.4f}")
        print(f"USDC: {info.balance_usdc:.2f}")
    else:
        print("No wallet found. Create one with:")
        print("  solana-keygen new -o ~/.config/solana/ricky-wallet.json")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
