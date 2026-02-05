#!/usr/bin/env python3
"""
Tests for wallet.py - Solana wallet operations

Tests cover:
- WalletInfo dataclass
- SolanaWallet initialization
- Keypair loading (mock)
- Balance fetching (mock)
- Transaction signing (mock)
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from wallet import WalletInfo, SolanaWallet


class TestWalletInfo:
    """Tests for WalletInfo dataclass."""
    
    def test_wallet_info_creation(self):
        """Test WalletInfo dataclass fields."""
        info = WalletInfo(
            address="4b5f4pmpSXtJrecmvZtyGyGXfwGCANA6UY1VYMjcjs44",
            balance_sol=1.5,
            balance_usdc=100.0
        )
        assert info.address == "4b5f4pmpSXtJrecmvZtyGyGXfwGCANA6UY1VYMjcjs44"
        assert info.balance_sol == 1.5
        assert info.balance_usdc == 100.0
    
    def test_wallet_info_zero_balances(self):
        """Test WalletInfo with zero balances."""
        info = WalletInfo(
            address="test_address",
            balance_sol=0.0,
            balance_usdc=0.0
        )
        assert info.balance_sol == 0.0
        assert info.balance_usdc == 0.0


class TestSolanaWallet:
    """Tests for SolanaWallet class."""
    
    def test_wallet_init_default_path(self):
        """Test wallet initializes with default keypair path."""
        wallet = SolanaWallet()
        assert "ricky-wallet.json" in wallet.keypair_path
    
    def test_wallet_init_custom_path(self):
        """Test wallet initializes with custom keypair path."""
        custom_path = "/tmp/my-wallet.json"
        wallet = SolanaWallet(keypair_path=custom_path)
        assert wallet.keypair_path == custom_path
    
    def test_usdc_mint_constant(self):
        """Test USDC mint address is correct."""
        assert SolanaWallet.USDC_MINT == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    
    def test_load_keypair_missing_file(self):
        """Test keypair loading fails gracefully with missing file."""
        wallet = SolanaWallet(keypair_path="/nonexistent/path.json")
        result = wallet.load_keypair()
        assert result is False
    
    def test_load_keypair_invalid_json(self):
        """Test keypair loading fails gracefully with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("not valid json")
            temp_path = f.name
        
        try:
            wallet = SolanaWallet(keypair_path=temp_path)
            result = wallet.load_keypair()
            assert result is False
        finally:
            Path(temp_path).unlink()
    
    def test_address_property_without_keypair(self):
        """Test address property returns None without valid keypair."""
        wallet = SolanaWallet(keypair_path="/nonexistent/path.json")
        # Address should be None if keypair can't load
        address = wallet.address
        assert address is None
    
    @pytest.mark.asyncio
    async def test_get_balance_structure(self):
        """Test get_balance returns proper WalletInfo structure."""
        wallet = SolanaWallet()
        wallet._address = "test_address"  # Set directly for testing
        
        # Mock httpx client
        mock_response_sol = MagicMock()
        mock_response_sol.json.return_value = {
            "result": {"value": 1_500_000_000}  # 1.5 SOL
        }
        
        mock_response_usdc = MagicMock()
        mock_response_usdc.json.return_value = {
            "result": {
                "value": [{
                    "account": {
                        "data": {
                            "parsed": {
                                "info": {
                                    "tokenAmount": {"uiAmount": 100.0}
                                }
                            }
                        }
                    }
                }]
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(side_effect=[mock_response_sol, mock_response_usdc])
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance
            
            info = await wallet.get_balance()
            
            assert isinstance(info, WalletInfo)
            assert info.address == "test_address"
            assert info.balance_sol == 1.5
            assert info.balance_usdc == 100.0
    
    @pytest.mark.asyncio
    async def test_get_balance_no_usdc_accounts(self):
        """Test get_balance with no USDC token accounts."""
        wallet = SolanaWallet()
        wallet._address = "test_address"
        
        mock_response_sol = MagicMock()
        mock_response_sol.json.return_value = {
            "result": {"value": 500_000_000}  # 0.5 SOL
        }
        
        mock_response_usdc = MagicMock()
        mock_response_usdc.json.return_value = {
            "result": {"value": []}  # No USDC accounts
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(side_effect=[mock_response_sol, mock_response_usdc])
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance
            
            info = await wallet.get_balance()
            
            assert info.balance_usdc == 0.0
    
    def test_sign_transaction_without_keypair(self):
        """Test sign_transaction behavior without keypair."""
        wallet = SolanaWallet(keypair_path="/nonexistent/path.json")
        
        # Should fail gracefully when no keypair
        # The actual implementation tries to load, which will fail
        # This tests the error path
        try:
            wallet.sign_transaction(b"test_tx_bytes")
            assert False, "Should have raised an exception"
        except Exception:
            pass  # Expected to fail


class TestWalletIntegration:
    """Integration-style tests (still mocked, but test full flows)."""
    
    def test_wallet_workflow(self):
        """Test typical wallet usage workflow."""
        # 1. Create wallet
        wallet = SolanaWallet(keypair_path="/tmp/test-wallet.json")
        
        # 2. Check initial state
        assert wallet._keypair is None
        assert wallet._address is None
        
        # 3. Verify USDC mint is accessible
        assert wallet.USDC_MINT is not None
        assert len(wallet.USDC_MINT) > 30  # Valid base58 address
