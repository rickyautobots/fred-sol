#!/usr/bin/env python3
"""
Tests for Solana integration module
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import sys
sys.path.insert(0, '..')

from solana_integration import (
    SolanaClient,
    JupiterSwap,
    FREDSolanaTrader,
    TokenBalance,
    TOKENS,
    LAMPORTS_PER_SOL
)


class TestSolanaClient:
    """Test SolanaClient RPC methods"""
    
    @pytest.fixture
    def client(self):
        return SolanaClient(rpc_url="https://api.devnet.solana.com")
    
    @pytest.mark.asyncio
    async def test_get_balance(self, client):
        """Test balance query returns float"""
        with patch.object(client, '_rpc', new_callable=AsyncMock) as mock_rpc:
            mock_rpc.return_value = {"value": 1_500_000_000}  # 1.5 SOL
            
            balance = await client.get_balance("TestPubkey123")
            
            assert balance == 1.5
            mock_rpc.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_balance_zero(self, client):
        """Test zero balance handling"""
        with patch.object(client, '_rpc', new_callable=AsyncMock) as mock_rpc:
            mock_rpc.return_value = {"value": 0}
            
            balance = await client.get_balance("EmptyWallet")
            
            assert balance == 0.0
    
    @pytest.mark.asyncio
    async def test_get_slot(self, client):
        """Test slot query"""
        with patch.object(client, '_rpc', new_callable=AsyncMock) as mock_rpc:
            mock_rpc.return_value = 250_000_000
            
            slot = await client.get_slot()
            
            assert slot == 250_000_000
    
    @pytest.mark.asyncio
    async def test_get_recent_blockhash(self, client):
        """Test blockhash retrieval"""
        with patch.object(client, '_rpc', new_callable=AsyncMock) as mock_rpc:
            mock_rpc.return_value = {
                "value": {"blockhash": "ABC123blockhash"}
            }
            
            blockhash = await client.get_recent_blockhash()
            
            assert blockhash == "ABC123blockhash"
    
    @pytest.mark.asyncio
    async def test_get_token_accounts(self, client):
        """Test SPL token account parsing"""
        with patch.object(client, '_rpc', new_callable=AsyncMock) as mock_rpc:
            mock_rpc.return_value = {
                "value": [{
                    "account": {
                        "data": {
                            "parsed": {
                                "info": {
                                    "mint": TOKENS["USDC"],
                                    "tokenAmount": {
                                        "uiAmount": 100.5,
                                        "decimals": 6
                                    }
                                }
                            }
                        }
                    }
                }]
            }
            
            balances = await client.get_token_accounts("TestOwner")
            
            assert len(balances) == 1
            assert balances[0].symbol == "USDC"
            assert balances[0].balance == 100.5
            assert balances[0].decimals == 6


class TestJupiterSwap:
    """Test Jupiter aggregator integration"""
    
    @pytest.fixture
    def jupiter(self):
        return JupiterSwap()
    
    @pytest.mark.asyncio
    async def test_get_quote(self, jupiter):
        """Test swap quote retrieval"""
        with patch.object(jupiter.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "outAmount": "98500000",  # 98.5 USDC
                "priceImpactPct": "0.01",
                "routePlan": [{"swapInfo": {"label": "Raydium"}}]
            }
            mock_get.return_value = mock_response
            
            quote = await jupiter.get_quote(
                TOKENS["SOL"],
                TOKENS["USDC"],
                1_000_000_000  # 1 SOL
            )
            
            assert quote["outAmount"] == "98500000"
            assert "routePlan" in quote


class TestFREDSolanaTrader:
    """Test FRED trading agent"""
    
    @pytest.fixture
    def trader(self):
        return FREDSolanaTrader(
            wallet_pubkey="EamKq5ZhE2eZP6Z2LgAps9RUeNTem8K2udSeYNWuCPKF"
        )
    
    @pytest.mark.asyncio
    async def test_get_portfolio(self, trader):
        """Test portfolio snapshot"""
        with patch.object(trader.solana, 'get_balance', new_callable=AsyncMock) as mock_bal, \
             patch.object(trader.solana, 'get_token_accounts', new_callable=AsyncMock) as mock_tokens, \
             patch.object(trader.solana, 'get_slot', new_callable=AsyncMock) as mock_slot:
            
            mock_bal.return_value = 5.5
            mock_tokens.return_value = [
                TokenBalance(mint=TOKENS["USDC"], symbol="USDC", balance=250.0, decimals=6)
            ]
            mock_slot.return_value = 250_000_000
            
            portfolio = await trader.get_portfolio()
            
            assert portfolio["sol"] == 5.5
            assert len(portfolio["tokens"]) == 1
            assert portfolio["tokens"][0]["symbol"] == "USDC"
    
    @pytest.mark.asyncio
    async def test_quote_swap(self, trader):
        """Test swap quote generation"""
        with patch.object(trader.jupiter, 'get_quote', new_callable=AsyncMock) as mock_quote:
            mock_quote.return_value = {
                "outAmount": "98500000",
                "priceImpactPct": "0.01",
                "routePlan": []
            }
            
            quote = await trader.quote_swap("SOL", "USDC", 1.0)
            
            assert quote["input"] == "SOL"
            assert quote["output"] == "USDC"
            assert quote["input_amount"] == 1.0
    
    @pytest.mark.asyncio
    async def test_execute_swap_dry_run(self, trader):
        """Test dry run swap execution"""
        with patch.object(trader.jupiter, 'get_quote', new_callable=AsyncMock) as mock_quote:
            mock_quote.return_value = {
                "outAmount": "98500000",
                "priceImpactPct": "0.01"
            }
            
            result = await trader.execute_swap("SOL", "USDC", 1.0, dry_run=True)
            
            assert result["status"] == "simulated"
            assert "quote" in result


class TestTokenConstants:
    """Test token configuration"""
    
    def test_common_tokens_defined(self):
        """Verify common tokens are configured"""
        required = ["SOL", "USDC", "USDT", "BONK", "JUP"]
        for token in required:
            assert token in TOKENS
            assert len(TOKENS[token]) == 44  # Solana pubkey length
    
    def test_lamports_constant(self):
        """Verify lamports conversion"""
        assert LAMPORTS_PER_SOL == 1_000_000_000


# Run with: pytest tests/test_solana_integration.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
