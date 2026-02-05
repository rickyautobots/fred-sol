#!/usr/bin/env python3
"""
Tests for executor.py - Jupiter swap execution

Tests cover:
- SwapQuote dataclass
- SwapResult dataclass
- JupiterExecutor initialization
- Quote fetching (mock)
- Swap transaction building (mock)
- Full swap execution (mock)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import base64

from executor import SwapQuote, SwapResult, JupiterExecutor


class TestSwapQuote:
    """Tests for SwapQuote dataclass."""
    
    def test_swap_quote_creation(self):
        """Test SwapQuote dataclass fields."""
        quote = SwapQuote(
            input_mint="So11111111111111111111111111111111111111112",
            output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            in_amount=100_000_000,  # 0.1 SOL
            out_amount=15_000_000,  # 15 USDC
            price_impact=0.001,
            route={"routePlan": []}
        )
        assert quote.input_mint == "So11111111111111111111111111111111111111112"
        assert quote.output_mint == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        assert quote.in_amount == 100_000_000
        assert quote.out_amount == 15_000_000
        assert quote.price_impact == 0.001
    
    def test_swap_quote_zero_impact(self):
        """Test SwapQuote with zero price impact."""
        quote = SwapQuote(
            input_mint="test_input",
            output_mint="test_output",
            in_amount=1000,
            out_amount=1000,
            price_impact=0.0,
            route={}
        )
        assert quote.price_impact == 0.0


class TestSwapResult:
    """Tests for SwapResult dataclass."""
    
    def test_swap_result_success(self):
        """Test successful SwapResult."""
        result = SwapResult(
            success=True,
            tx_signature="5wHu1qwD7q4...",
            error=None
        )
        assert result.success is True
        assert result.tx_signature == "5wHu1qwD7q4..."
        assert result.error is None
    
    def test_swap_result_failure(self):
        """Test failed SwapResult."""
        result = SwapResult(
            success=False,
            tx_signature=None,
            error="Insufficient balance"
        )
        assert result.success is False
        assert result.tx_signature is None
        assert result.error == "Insufficient balance"


class TestJupiterExecutor:
    """Tests for JupiterExecutor class."""
    
    def test_executor_init(self):
        """Test executor initialization."""
        executor = JupiterExecutor("test_wallet_address")
        assert executor.wallet == "test_wallet_address"
    
    def test_executor_constants(self):
        """Test executor has correct token constants."""
        assert JupiterExecutor.SOL == "So11111111111111111111111111111111111111112"
        assert JupiterExecutor.USDC == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    
    def test_jupiter_api_url(self):
        """Test Jupiter API URL is correct."""
        assert "jup.ag" in JupiterExecutor.JUPITER_API
    
    @pytest.mark.asyncio
    async def test_get_quote_success(self):
        """Test successful quote fetching."""
        executor = JupiterExecutor("test_wallet")
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "inAmount": "100000000",
            "outAmount": "15000000",
            "priceImpactPct": "0.001",
            "routePlan": []
        }
        
        executor.client = MagicMock()
        executor.client.get = AsyncMock(return_value=mock_response)
        
        quote = await executor.get_quote(
            input_mint=executor.SOL,
            output_mint=executor.USDC,
            amount=100_000_000
        )
        
        assert quote is not None
        assert quote.in_amount == 100_000_000
        assert quote.out_amount == 15_000_000
        assert quote.price_impact == 0.001
    
    @pytest.mark.asyncio
    async def test_get_quote_failure(self):
        """Test quote fetching handles errors."""
        executor = JupiterExecutor("test_wallet")
        
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        
        executor.client = MagicMock()
        executor.client.get = AsyncMock(return_value=mock_response)
        
        quote = await executor.get_quote(
            input_mint="invalid",
            output_mint="invalid",
            amount=100
        )
        
        assert quote is None
    
    @pytest.mark.asyncio
    async def test_get_quote_exception(self):
        """Test quote fetching handles exceptions."""
        executor = JupiterExecutor("test_wallet")
        
        executor.client = MagicMock()
        executor.client.get = AsyncMock(side_effect=Exception("Network error"))
        
        quote = await executor.get_quote(
            input_mint=executor.SOL,
            output_mint=executor.USDC,
            amount=100_000_000
        )
        
        assert quote is None
    
    @pytest.mark.asyncio
    async def test_get_swap_transaction_success(self):
        """Test successful swap transaction building."""
        executor = JupiterExecutor("test_wallet")
        
        # Create a mock quote
        quote = SwapQuote(
            input_mint=executor.SOL,
            output_mint=executor.USDC,
            in_amount=100_000_000,
            out_amount=15_000_000,
            price_impact=0.001,
            route={"quoteResponse": "data"}
        )
        
        # Mock response with base64 encoded transaction
        mock_tx = base64.b64encode(b"mock_transaction_bytes").decode()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "swapTransaction": mock_tx
        }
        
        executor.client = MagicMock()
        executor.client.post = AsyncMock(return_value=mock_response)
        
        tx_bytes = await executor.get_swap_transaction(quote)
        
        assert tx_bytes is not None
        assert tx_bytes == b"mock_transaction_bytes"
    
    @pytest.mark.asyncio
    async def test_get_swap_transaction_failure(self):
        """Test swap transaction handles errors."""
        executor = JupiterExecutor("test_wallet")
        
        quote = SwapQuote(
            input_mint="test",
            output_mint="test",
            in_amount=100,
            out_amount=100,
            price_impact=0.0,
            route={}
        )
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Server error"
        
        executor.client = MagicMock()
        executor.client.post = AsyncMock(return_value=mock_response)
        
        tx_bytes = await executor.get_swap_transaction(quote)
        
        assert tx_bytes is None
    
    @pytest.mark.asyncio
    async def test_execute_swap_full_flow(self):
        """Test complete swap execution flow."""
        executor = JupiterExecutor("test_wallet")
        
        # Mock get_quote
        mock_quote = SwapQuote(
            input_mint=executor.SOL,
            output_mint=executor.USDC,
            in_amount=100_000_000,
            out_amount=15_000_000,
            price_impact=0.001,
            route={}
        )
        
        # Mock get_swap_transaction
        mock_tx = b"mock_tx"
        
        with patch.object(executor, 'get_quote', new_callable=AsyncMock) as mock_get_quote:
            with patch.object(executor, 'get_swap_transaction', new_callable=AsyncMock) as mock_get_tx:
                mock_get_quote.return_value = mock_quote
                mock_get_tx.return_value = mock_tx
                
                # Mock sign callback
                sign_callback = MagicMock(return_value=b"signature")
                
                result = await executor.execute_swap(
                    input_mint=executor.SOL,
                    output_mint=executor.USDC,
                    amount=100_000_000,
                    sign_callback=sign_callback
                )
                
                assert result.success is True
                assert result.error is None
    
    @pytest.mark.asyncio
    async def test_execute_swap_quote_failure(self):
        """Test swap execution handles quote failure."""
        executor = JupiterExecutor("test_wallet")
        
        with patch.object(executor, 'get_quote', new_callable=AsyncMock) as mock_get_quote:
            mock_get_quote.return_value = None
            
            result = await executor.execute_swap(
                input_mint=executor.SOL,
                output_mint=executor.USDC,
                amount=100_000_000,
                sign_callback=lambda x: x
            )
            
            assert result.success is False
            assert "quote" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_execute_swap_transaction_failure(self):
        """Test swap execution handles transaction failure."""
        executor = JupiterExecutor("test_wallet")
        
        mock_quote = SwapQuote(
            input_mint=executor.SOL,
            output_mint=executor.USDC,
            in_amount=100_000_000,
            out_amount=15_000_000,
            price_impact=0.001,
            route={}
        )
        
        with patch.object(executor, 'get_quote', new_callable=AsyncMock) as mock_get_quote:
            with patch.object(executor, 'get_swap_transaction', new_callable=AsyncMock) as mock_get_tx:
                mock_get_quote.return_value = mock_quote
                mock_get_tx.return_value = None
                
                result = await executor.execute_swap(
                    input_mint=executor.SOL,
                    output_mint=executor.USDC,
                    amount=100_000_000,
                    sign_callback=lambda x: x
                )
                
                assert result.success is False
                assert "transaction" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_executor_close(self):
        """Test executor cleanup."""
        executor = JupiterExecutor("test_wallet")
        executor.client = MagicMock()
        executor.client.aclose = AsyncMock()
        
        await executor.close()
        
        executor.client.aclose.assert_called_once()


class TestSlippageHandling:
    """Tests for slippage parameters."""
    
    @pytest.mark.asyncio
    async def test_default_slippage(self):
        """Test default slippage is reasonable."""
        executor = JupiterExecutor("test_wallet")
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "inAmount": "100",
            "outAmount": "100",
            "priceImpactPct": "0"
        }
        
        executor.client = MagicMock()
        executor.client.get = AsyncMock(return_value=mock_response)
        
        await executor.get_quote("input", "output", 100)
        
        # Check the call included slippage
        call_kwargs = executor.client.get.call_args
        assert call_kwargs is not None
        params = call_kwargs.kwargs.get('params', {})
        assert 'slippageBps' in params
        assert params['slippageBps'] == 50  # 0.5% default
    
    @pytest.mark.asyncio
    async def test_custom_slippage(self):
        """Test custom slippage is passed correctly."""
        executor = JupiterExecutor("test_wallet")
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "inAmount": "100",
            "outAmount": "100",
            "priceImpactPct": "0"
        }
        
        executor.client = MagicMock()
        executor.client.get = AsyncMock(return_value=mock_response)
        
        await executor.get_quote("input", "output", 100, slippage_bps=100)  # 1%
        
        call_kwargs = executor.client.get.call_args
        params = call_kwargs.kwargs.get('params', {})
        assert params['slippageBps'] == 100
