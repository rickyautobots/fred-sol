#!/usr/bin/env python3
"""
Tests for configuration management
"""

import pytest
import os
import tempfile
import json

import sys
sys.path.insert(0, '..')

from config import (
    Network, TradingMode,
    WalletConfig, RiskConfig, RPCConfig, AlertConfig, LLMConfig,
    FREDConfig, get_config
)


class TestNetworkEnum:
    """Test Network enum"""
    
    def test_all_networks(self):
        assert Network.MAINNET.value == "mainnet"
        assert Network.DEVNET.value == "devnet"
        assert Network.TESTNET.value == "testnet"


class TestTradingModeEnum:
    """Test TradingMode enum"""
    
    def test_all_modes(self):
        assert TradingMode.DRY_RUN.value == "dry_run"
        assert TradingMode.PAPER.value == "paper"
        assert TradingMode.LIVE.value == "live"


class TestWalletConfig:
    """Test WalletConfig"""
    
    def test_wallet_creation(self):
        wallet = WalletConfig(
            address="EamKq5ZhE2eZP6Z2LgAps9RUeNTem8K2udSeYNWuCPKF"
        )
        
        assert wallet.address
        assert wallet.private_key_path is None
    
    def test_has_signing_capability_false(self):
        wallet = WalletConfig(address="test")
        assert wallet.has_signing_capability() == False
    
    def test_has_signing_capability_true(self):
        wallet = WalletConfig(
            address="test",
            private_key_path="/path/to/key.json"
        )
        assert wallet.has_signing_capability() == True


class TestRiskConfig:
    """Test RiskConfig"""
    
    def test_risk_defaults(self):
        risk = RiskConfig()
        
        assert risk.max_position_pct == 0.05
        assert risk.max_daily_loss_pct == 0.10
        assert risk.min_edge == 0.05
        assert risk.min_r_multiple == 1.5
        assert risk.max_open_positions == 5
    
    def test_risk_validate_success(self):
        risk = RiskConfig()
        risk.validate()  # Should not raise
    
    def test_risk_validate_max_position_too_high(self):
        risk = RiskConfig(max_position_pct=0.50)
        
        with pytest.raises(AssertionError):
            risk.validate()
    
    def test_risk_validate_max_position_zero(self):
        risk = RiskConfig(max_position_pct=0)
        
        with pytest.raises(AssertionError):
            risk.validate()
    
    def test_risk_validate_daily_loss_too_high(self):
        risk = RiskConfig(max_daily_loss_pct=0.75)
        
        with pytest.raises(AssertionError):
            risk.validate()


class TestRPCConfig:
    """Test RPCConfig"""
    
    def test_rpc_defaults(self):
        rpc = RPCConfig()
        
        assert "mainnet-beta.solana.com" in rpc.mainnet_url
        assert "devnet.solana.com" in rpc.devnet_url
        assert rpc.commitment == "confirmed"
    
    def test_get_url_mainnet(self):
        rpc = RPCConfig()
        url = rpc.get_url(Network.MAINNET)
        
        assert "mainnet" in url
    
    def test_get_url_devnet(self):
        rpc = RPCConfig()
        url = rpc.get_url(Network.DEVNET)
        
        assert "devnet" in url


class TestAlertConfig:
    """Test AlertConfig"""
    
    def test_alert_no_providers(self):
        alerts = AlertConfig()
        assert alerts.has_any_provider() == False
    
    def test_alert_with_discord(self):
        alerts = AlertConfig(discord_webhook="https://discord.com/api/webhooks/123/abc")
        assert alerts.has_any_provider() == True
    
    def test_alert_with_telegram(self):
        alerts = AlertConfig(
            telegram_bot_token="123:ABC",
            telegram_chat_id="456"
        )
        assert alerts.has_any_provider() == True
    
    def test_alert_telegram_incomplete(self):
        # Need both token and chat_id
        alerts = AlertConfig(telegram_bot_token="123:ABC")
        assert alerts.has_any_provider() == False


class TestLLMConfig:
    """Test LLMConfig"""
    
    def test_llm_defaults(self):
        llm = LLMConfig()
        
        assert llm.provider == "anthropic"
        assert llm.model == "claude-3-sonnet"
        assert llm.temperature == 0.3
    
    def test_get_api_key_from_config(self):
        llm = LLMConfig(api_key="test_key")
        assert llm.get_api_key() == "test_key"
    
    def test_get_api_key_from_env(self):
        os.environ["ANTHROPIC_API_KEY"] = "env_key"
        
        llm = LLMConfig()
        key = llm.get_api_key()
        
        del os.environ["ANTHROPIC_API_KEY"]
        
        assert key == "env_key"


class TestFREDConfig:
    """Test FREDConfig"""
    
    def test_fred_config_defaults(self):
        config = FREDConfig()
        
        assert config.network == Network.MAINNET
        assert config.mode == TradingMode.DRY_RUN
        assert config.agent_name == "FRED"
    
    def test_from_env(self):
        os.environ["SOLANA_NETWORK"] = "devnet"
        os.environ["TRADING_MODE"] = "paper"
        os.environ["SOLANA_WALLET"] = "test_wallet"
        
        config = FREDConfig.from_env()
        
        del os.environ["SOLANA_NETWORK"]
        del os.environ["TRADING_MODE"]
        del os.environ["SOLANA_WALLET"]
        
        assert config.network == Network.DEVNET
        assert config.mode == TradingMode.PAPER
        assert config.wallet.address == "test_wallet"
    
    def test_from_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "network": "devnet",
                "mode": "paper",
                "wallet": {"address": "file_wallet"},
                "agent_id": 1234,
                "agent_name": "TestAgent"
            }, f)
            f.flush()
            
            config = FREDConfig.from_file(f.name)
            
            os.unlink(f.name)
        
        assert config.network == Network.DEVNET
        assert config.mode == TradingMode.PAPER
        assert config.wallet.address == "file_wallet"
        assert config.agent_id == 1234
        assert config.agent_name == "TestAgent"
    
    def test_validate_success(self):
        config = FREDConfig()
        config.wallet = WalletConfig(address="test_wallet")
        
        config.validate()  # Should not raise
    
    def test_validate_no_wallet(self):
        config = FREDConfig()
        config.wallet = WalletConfig(address="")
        
        with pytest.raises(AssertionError):
            config.validate()
    
    def test_validate_live_no_signing(self):
        config = FREDConfig()
        config.wallet = WalletConfig(address="test")
        config.mode = TradingMode.LIVE
        
        with pytest.raises(AssertionError):
            config.validate()
    
    def test_to_dict(self):
        config = FREDConfig()
        config.wallet = WalletConfig(address="test_wallet_address")
        
        d = config.to_dict()
        
        assert d["network"] == "mainnet"
        assert d["mode"] == "dry_run"
        assert "test_wallet" in d["wallet_address"]
    
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "config.json")
            
            config = FREDConfig()
            config.wallet = WalletConfig(address="save_test")
            config.agent_id = 9999
            config.save(filepath)
            
            # Verify file exists and is valid JSON
            with open(filepath) as f:
                data = json.load(f)
            
            assert data["agent_id"] == 9999
            assert data["wallet"]["address"] == "save_test"


class TestGetConfig:
    """Test get_config function"""
    
    def test_get_config_returns_config(self):
        config = get_config()
        
        assert isinstance(config, FREDConfig)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
