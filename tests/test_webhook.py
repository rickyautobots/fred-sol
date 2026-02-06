#!/usr/bin/env python3
"""
Tests for webhook alert system
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import sys
sys.path.insert(0, '..')

from webhook_alerts import (
    AlertLevel, TradeAlert, SystemAlert,
    WebhookProvider, DiscordWebhook, TelegramWebhook, SlackWebhook,
    AlertManager
)


class TestAlertLevel:
    """Test AlertLevel enum"""
    
    def test_all_levels(self):
        assert AlertLevel.INFO
        assert AlertLevel.WARNING
        assert AlertLevel.SUCCESS
        assert AlertLevel.ERROR
        assert AlertLevel.CRITICAL


class TestTradeAlert:
    """Test TradeAlert dataclass"""
    
    def test_trade_alert_creation(self):
        alert = TradeAlert(
            timestamp=datetime.now(timezone.utc).isoformat(),
            market="SOL/USDC",
            side="BUY",
            amount=100.0,
            price=98.50,
            pnl=12.50,
            r_multiple=1.25
        )
        
        assert alert.market == "SOL/USDC"
        assert alert.pnl == 12.50
    
    def test_trade_alert_to_dict(self):
        alert = TradeAlert(
            timestamp="2026-02-06T12:00:00Z",
            market="SOL/USDC",
            side="BUY",
            amount=100.0,
            price=98.50
        )
        
        d = alert.to_dict()
        
        assert d["market"] == "SOL/USDC"
        assert d["side"] == "BUY"
        assert d["amount"] == 100.0


class TestSystemAlert:
    """Test SystemAlert dataclass"""
    
    def test_system_alert_creation(self):
        alert = SystemAlert(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level="success",
            title="Agent Online",
            message="FRED is now active"
        )
        
        assert alert.level == "success"
        assert alert.title == "Agent Online"
    
    def test_system_alert_with_metadata(self):
        alert = SystemAlert(
            timestamp="now",
            level="info",
            title="Test",
            message="Test message",
            metadata={"version": "1.0"}
        )
        
        assert alert.metadata["version"] == "1.0"


class TestWebhookProvider:
    """Test base WebhookProvider"""
    
    @pytest.mark.asyncio
    async def test_send_success(self):
        provider = WebhookProvider("https://example.com/webhook")
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch.object(provider.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            result = await provider.send({"test": "data"})
            
            assert result == True
    
    @pytest.mark.asyncio
    async def test_send_failure(self):
        provider = WebhookProvider("https://example.com/webhook")
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        
        with patch.object(provider.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            result = await provider.send({"test": "data"})
            
            assert result == False
    
    @pytest.mark.asyncio
    async def test_send_exception(self):
        provider = WebhookProvider("https://example.com/webhook")
        
        with patch.object(provider.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("Connection error")
            
            result = await provider.send({"test": "data"})
            
            assert result == False


class TestDiscordWebhook:
    """Test Discord webhook formatting"""
    
    @pytest.fixture
    def discord(self):
        return DiscordWebhook("https://discord.com/api/webhooks/123/abc")
    
    def test_format_trade_buy(self, discord):
        alert = TradeAlert(
            timestamp="2026-02-06T12:00:00Z",
            market="SOL/USDC",
            side="BUY",
            amount=100.0,
            price=98.50,
            pnl=15.0,
            r_multiple=1.5
        )
        
        payload = discord.format_trade(alert)
        
        assert "embeds" in payload
        assert len(payload["embeds"]) == 1
        assert "BUY" in payload["embeds"][0]["title"]
    
    def test_format_trade_sell(self, discord):
        alert = TradeAlert(
            timestamp="2026-02-06T12:00:00Z",
            market="SOL/USDC",
            side="SELL",
            amount=100.0,
            price=98.50
        )
        
        payload = discord.format_trade(alert)
        
        assert "SELL" in payload["embeds"][0]["title"]
    
    def test_format_system(self, discord):
        alert = SystemAlert(
            timestamp="2026-02-06T12:00:00Z",
            level="success",
            title="Agent Online",
            message="FRED is active"
        )
        
        payload = discord.format_system(alert)
        
        assert "embeds" in payload
        assert "Agent Online" in payload["embeds"][0]["title"]


class TestTelegramWebhook:
    """Test Telegram webhook formatting"""
    
    @pytest.fixture
    def telegram(self):
        return TelegramWebhook("123:ABC", "456")
    
    def test_format_trade(self, telegram):
        alert = TradeAlert(
            timestamp="2026-02-06T12:00:00Z",
            market="SOL/USDC",
            side="BUY",
            amount=100.0,
            price=98.50,
            pnl=15.0
        )
        
        payload = telegram.format_trade(alert)
        
        assert payload["chat_id"] == "456"
        assert payload["parse_mode"] == "Markdown"
        assert "SOL/USDC" in payload["text"]
    
    def test_format_system(self, telegram):
        alert = SystemAlert(
            timestamp="2026-02-06T12:00:00Z",
            level="warning",
            title="Low Balance",
            message="SOL balance is low"
        )
        
        payload = telegram.format_system(alert)
        
        assert "Low Balance" in payload["text"]
        assert "⚠️" in payload["text"]


class TestSlackWebhook:
    """Test Slack webhook formatting"""
    
    @pytest.fixture
    def slack(self):
        return SlackWebhook("https://hooks.slack.com/services/T/B/X")
    
    def test_format_trade(self, slack):
        alert = TradeAlert(
            timestamp="2026-02-06T12:00:00Z",
            market="SOL/USDC",
            side="BUY",
            amount=100.0,
            price=98.50
        )
        
        payload = slack.format_trade(alert)
        
        assert "attachments" in payload
        assert len(payload["attachments"]) == 1
        assert payload["attachments"][0]["color"] == "good"


class TestAlertManager:
    """Test AlertManager"""
    
    @pytest.fixture
    def manager(self):
        return AlertManager()
    
    def test_add_discord(self, manager):
        manager.add_discord("https://discord.com/api/webhooks/123/abc")
        
        assert len(manager.providers) == 1
        assert isinstance(manager.providers[0], DiscordWebhook)
    
    def test_add_telegram(self, manager):
        manager.add_telegram("123:ABC", "456")
        
        assert len(manager.providers) == 1
        assert isinstance(manager.providers[0], TelegramWebhook)
    
    def test_add_slack(self, manager):
        manager.add_slack("https://hooks.slack.com/services/T/B/X")
        
        assert len(manager.providers) == 1
        assert isinstance(manager.providers[0], SlackWebhook)
    
    def test_chaining(self, manager):
        manager.add_discord("d").add_telegram("t", "c").add_slack("s")
        
        assert len(manager.providers) == 3
    
    @pytest.mark.asyncio
    async def test_send_trade_alert(self, manager):
        mock_provider = MagicMock()
        mock_provider.name = "mock"
        mock_provider.send_trade = AsyncMock(return_value=True)
        
        manager.providers.append(mock_provider)
        
        alert = TradeAlert(
            timestamp="now",
            market="SOL/USDC",
            side="BUY",
            amount=100.0,
            price=98.50
        )
        
        results = await manager.send_trade_alert(alert)
        
        assert results["mock"] == True
    
    @pytest.mark.asyncio
    async def test_send_system_alert(self, manager):
        mock_provider = MagicMock()
        mock_provider.name = "mock"
        mock_provider.send_system = AsyncMock(return_value=True)
        
        manager.providers.append(mock_provider)
        
        alert = SystemAlert(
            timestamp="now",
            level="info",
            title="Test",
            message="Test message"
        )
        
        results = await manager.send_system_alert(alert)
        
        assert results["mock"] == True
    
    def test_history_tracking(self, manager):
        # History should be empty initially
        assert len(manager.history) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
