#!/usr/bin/env python3
"""
Tests for health monitoring system
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import sys
sys.path.insert(0, '..')

from health import (
    HealthStatus, CheckResult, HealthChecker
)


class TestHealthStatus:
    """Test HealthStatus enum"""
    
    def test_all_statuses_exist(self):
        assert HealthStatus.HEALTHY
        assert HealthStatus.DEGRADED
        assert HealthStatus.UNHEALTHY
        assert HealthStatus.UNKNOWN


class TestCheckResult:
    """Test CheckResult dataclass"""
    
    def test_check_result_creation(self):
        result = CheckResult(
            name="test_check",
            status=HealthStatus.HEALTHY,
            latency_ms=50.0,
            message="All good"
        )
        
        assert result.name == "test_check"
        assert result.status == HealthStatus.HEALTHY
        assert result.latency_ms == 50.0
    
    def test_check_result_with_metadata(self):
        result = CheckResult(
            name="balance",
            status=HealthStatus.HEALTHY,
            metadata={"balance_sol": 5.5}
        )
        
        assert result.metadata["balance_sol"] == 5.5


class TestHealthChecker:
    """Test HealthChecker class"""
    
    @pytest.fixture
    def checker(self):
        config = {
            "rpc_url": "https://api.mainnet-beta.solana.com",
            "wallet_address": "EamKq5ZhE2eZP6Z2LgAps9RUeNTem8K2udSeYNWuCPKF",
            "min_sol_balance": 0.01
        }
        return HealthChecker(config)
    
    @pytest.mark.asyncio
    async def test_check_solana_rpc_healthy(self, checker):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "ok"}
        
        with patch.object(checker.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            result = await checker.check_solana_rpc()
            
            assert result.status == HealthStatus.HEALTHY
            assert result.latency_ms is not None
    
    @pytest.mark.asyncio
    async def test_check_solana_rpc_degraded(self, checker):
        mock_response = MagicMock()
        mock_response.status_code = 500
        
        with patch.object(checker.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            result = await checker.check_solana_rpc()
            
            assert result.status == HealthStatus.DEGRADED
    
    @pytest.mark.asyncio
    async def test_check_solana_rpc_unhealthy(self, checker):
        with patch.object(checker.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("Connection failed")
            
            result = await checker.check_solana_rpc()
            
            assert result.status == HealthStatus.UNHEALTHY
            assert "error" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_check_jupiter_healthy(self, checker):
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch.object(checker.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            result = await checker.check_jupiter()
            
            assert result.status == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_check_wallet_balance_healthy(self, checker):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {"value": 1_000_000_000}  # 1 SOL
        }
        
        with patch.object(checker.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            result = await checker.check_wallet_balance()
            
            assert result.status == HealthStatus.HEALTHY
            assert result.metadata["balance_sol"] == 1.0
    
    @pytest.mark.asyncio
    async def test_check_wallet_balance_degraded(self, checker):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {"value": 5_000_000}  # 0.005 SOL, below threshold
        }
        
        with patch.object(checker.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            result = await checker.check_wallet_balance()
            
            assert result.status == HealthStatus.DEGRADED
            assert "low" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_check_wallet_balance_no_wallet(self):
        checker = HealthChecker({})  # No wallet configured
        
        result = await checker.check_wallet_balance()
        
        assert result.status == HealthStatus.UNKNOWN
        assert "no wallet" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_check_llm_api_no_key(self):
        checker = HealthChecker({})
        
        result = await checker.check_llm_api()
        
        assert result.status == HealthStatus.UNKNOWN
    
    @pytest.mark.asyncio
    async def test_check_all_returns_summary(self, checker):
        # Mock all individual checks
        async def mock_healthy():
            return CheckResult("test", HealthStatus.HEALTHY)
        
        with patch.object(checker, 'check_solana_rpc', mock_healthy), \
             patch.object(checker, 'check_jupiter', mock_healthy), \
             patch.object(checker, 'check_wallet_balance', mock_healthy), \
             patch.object(checker, 'check_llm_api', mock_healthy):
            
            result = await checker.check_all()
            
            assert result["status"] == "healthy"
            assert len(result["checks"]) == 4
            assert result["timestamp"] is not None
    
    @pytest.mark.asyncio
    async def test_check_all_degraded_if_any_degraded(self, checker):
        async def mock_healthy():
            return CheckResult("test", HealthStatus.HEALTHY)
        
        async def mock_degraded():
            return CheckResult("test", HealthStatus.DEGRADED)
        
        with patch.object(checker, 'check_solana_rpc', mock_healthy), \
             patch.object(checker, 'check_jupiter', mock_degraded), \
             patch.object(checker, 'check_wallet_balance', mock_healthy), \
             patch.object(checker, 'check_llm_api', mock_healthy):
            
            result = await checker.check_all()
            
            assert result["status"] == "degraded"
    
    @pytest.mark.asyncio
    async def test_check_all_unhealthy_if_any_unhealthy(self, checker):
        async def mock_healthy():
            return CheckResult("test", HealthStatus.HEALTHY)
        
        async def mock_unhealthy():
            return CheckResult("test", HealthStatus.UNHEALTHY)
        
        with patch.object(checker, 'check_solana_rpc', mock_unhealthy), \
             patch.object(checker, 'check_jupiter', mock_healthy), \
             patch.object(checker, 'check_wallet_balance', mock_healthy), \
             patch.object(checker, 'check_llm_api', mock_healthy):
            
            result = await checker.check_all()
            
            assert result["status"] == "unhealthy"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
