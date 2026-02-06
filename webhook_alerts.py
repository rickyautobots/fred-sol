#!/usr/bin/env python3
"""
FRED-SOL: Webhook Alert System
Send trade notifications to Discord/Telegram/Slack

Built: 2026-02-06 07:05 CST by Ricky
"""

import asyncio
import json
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from enum import Enum

import httpx


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    SUCCESS = "success"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class TradeAlert:
    """Trade notification payload"""
    timestamp: str
    market: str
    side: str
    amount: float
    price: float
    pnl: Optional[float] = None
    r_multiple: Optional[float] = None
    reasoning: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SystemAlert:
    """System status notification"""
    timestamp: str
    level: str
    title: str
    message: str
    metadata: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


class WebhookProvider:
    """Base webhook provider"""
    
    def __init__(self, webhook_url: str, name: str = "webhook"):
        self.url = webhook_url
        self.name = name
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def send(self, payload: Dict) -> bool:
        """Send payload to webhook"""
        try:
            resp = await self.client.post(self.url, json=payload)
            return resp.status_code < 400
        except Exception as e:
            print(f"[{self.name}] Webhook error: {e}")
            return False
    
    async def close(self):
        await self.client.aclose()


class DiscordWebhook(WebhookProvider):
    """Discord webhook formatter"""
    
    def __init__(self, webhook_url: str):
        super().__init__(webhook_url, "discord")
    
    def format_trade(self, alert: TradeAlert) -> Dict:
        """Format trade alert for Discord embed"""
        color = 0x00FF00 if alert.side == "BUY" else 0xFF0000
        
        fields = [
            {"name": "Market", "value": alert.market, "inline": True},
            {"name": "Side", "value": alert.side, "inline": True},
            {"name": "Amount", "value": f"${alert.amount:,.2f}", "inline": True},
        ]
        
        if alert.pnl is not None:
            pnl_emoji = "📈" if alert.pnl >= 0 else "📉"
            fields.append({
                "name": "P&L", 
                "value": f"{pnl_emoji} ${alert.pnl:+,.2f}", 
                "inline": True
            })
        
        if alert.r_multiple is not None:
            fields.append({
                "name": "R-Multiple",
                "value": f"{alert.r_multiple:+.2f}R",
                "inline": True
            })
        
        return {
            "embeds": [{
                "title": f"🤖 FRED Trade: {alert.side} {alert.market}",
                "color": color,
                "fields": fields,
                "footer": {"text": f"FRED-SOL | {alert.timestamp}"},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }]
        }
    
    def format_system(self, alert: SystemAlert) -> Dict:
        """Format system alert for Discord"""
        level_colors = {
            "info": 0x3498DB,
            "warning": 0xF39C12,
            "success": 0x2ECC71,
            "error": 0xE74C3C,
            "critical": 0x9B59B6
        }
        level_emojis = {
            "info": "ℹ️",
            "warning": "⚠️",
            "success": "✅",
            "error": "❌",
            "critical": "🚨"
        }
        
        return {
            "embeds": [{
                "title": f"{level_emojis.get(alert.level, '📢')} {alert.title}",
                "description": alert.message,
                "color": level_colors.get(alert.level, 0x95A5A6),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }]
        }
    
    async def send_trade(self, alert: TradeAlert) -> bool:
        return await self.send(self.format_trade(alert))
    
    async def send_system(self, alert: SystemAlert) -> bool:
        return await self.send(self.format_system(alert))


class TelegramWebhook(WebhookProvider):
    """Telegram bot webhook"""
    
    def __init__(self, bot_token: str, chat_id: str):
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        super().__init__(url, "telegram")
        self.chat_id = chat_id
    
    def format_trade(self, alert: TradeAlert) -> Dict:
        """Format trade for Telegram"""
        emoji = "🟢" if alert.side == "BUY" else "🔴"
        pnl_line = ""
        if alert.pnl is not None:
            pnl_emoji = "📈" if alert.pnl >= 0 else "📉"
            pnl_line = f"\n{pnl_emoji} P&L: ${alert.pnl:+,.2f}"
        
        text = f"""
{emoji} *FRED Trade*
Market: `{alert.market}`
Side: {alert.side}
Amount: ${alert.amount:,.2f}{pnl_line}
        """.strip()
        
        return {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
    
    def format_system(self, alert: SystemAlert) -> Dict:
        """Format system alert for Telegram"""
        level_emojis = {
            "info": "ℹ️",
            "warning": "⚠️",
            "success": "✅",
            "error": "❌",
            "critical": "🚨"
        }
        
        text = f"""
{level_emojis.get(alert.level, '📢')} *{alert.title}*
{alert.message}
        """.strip()
        
        return {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
    
    async def send_trade(self, alert: TradeAlert) -> bool:
        return await self.send(self.format_trade(alert))
    
    async def send_system(self, alert: SystemAlert) -> bool:
        return await self.send(self.format_system(alert))


class SlackWebhook(WebhookProvider):
    """Slack incoming webhook"""
    
    def __init__(self, webhook_url: str):
        super().__init__(webhook_url, "slack")
    
    def format_trade(self, alert: TradeAlert) -> Dict:
        """Format trade for Slack blocks"""
        color = "good" if alert.side == "BUY" else "danger"
        
        fields = [
            {"title": "Market", "value": alert.market, "short": True},
            {"title": "Side", "value": alert.side, "short": True},
            {"title": "Amount", "value": f"${alert.amount:,.2f}", "short": True},
        ]
        
        if alert.pnl is not None:
            fields.append({
                "title": "P&L",
                "value": f"${alert.pnl:+,.2f}",
                "short": True
            })
        
        return {
            "attachments": [{
                "color": color,
                "title": f"🤖 FRED Trade: {alert.side} {alert.market}",
                "fields": fields,
                "footer": "FRED-SOL Trading Agent",
                "ts": int(datetime.now().timestamp())
            }]
        }
    
    async def send_trade(self, alert: TradeAlert) -> bool:
        return await self.send(self.format_trade(alert))


class AlertManager:
    """
    Manage multiple webhook providers for FRED alerts
    """
    
    def __init__(self):
        self.providers: List[WebhookProvider] = []
        self.history: List[Dict] = []
        self.max_history = 100
    
    def add_discord(self, webhook_url: str) -> "AlertManager":
        self.providers.append(DiscordWebhook(webhook_url))
        return self
    
    def add_telegram(self, bot_token: str, chat_id: str) -> "AlertManager":
        self.providers.append(TelegramWebhook(bot_token, chat_id))
        return self
    
    def add_slack(self, webhook_url: str) -> "AlertManager":
        self.providers.append(SlackWebhook(webhook_url))
        return self
    
    async def send_trade_alert(self, alert: TradeAlert) -> Dict[str, bool]:
        """Send trade alert to all providers"""
        results = {}
        
        for provider in self.providers:
            if hasattr(provider, 'send_trade'):
                results[provider.name] = await provider.send_trade(alert)
        
        self._add_history("trade", alert.to_dict(), results)
        return results
    
    async def send_system_alert(self, alert: SystemAlert) -> Dict[str, bool]:
        """Send system alert to all providers"""
        results = {}
        
        for provider in self.providers:
            if hasattr(provider, 'send_system'):
                results[provider.name] = await provider.send_system(alert)
        
        self._add_history("system", alert.to_dict(), results)
        return results
    
    def _add_history(self, alert_type: str, data: Dict, results: Dict):
        """Track alert history"""
        self.history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": alert_type,
            "data": data,
            "results": results
        })
        
        # Trim history
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    async def close(self):
        """Close all provider connections"""
        for provider in self.providers:
            await provider.close()


async def main():
    """Demo webhook alerts"""
    import argparse
    
    parser = argparse.ArgumentParser(description="FRED Webhook Alert Demo")
    parser.add_argument("--discord", help="Discord webhook URL")
    parser.add_argument("--telegram-token", help="Telegram bot token")
    parser.add_argument("--telegram-chat", help="Telegram chat ID")
    args = parser.parse_args()
    
    manager = AlertManager()
    
    if args.discord:
        manager.add_discord(args.discord)
    
    if args.telegram_token and args.telegram_chat:
        manager.add_telegram(args.telegram_token, args.telegram_chat)
    
    if not manager.providers:
        print("No webhook providers configured.")
        print("Usage: python webhook_alerts.py --discord <url>")
        return
    
    # Send demo alerts
    print("Sending demo trade alert...")
    trade = TradeAlert(
        timestamp=datetime.now(timezone.utc).isoformat(),
        market="SOL/USDC",
        side="BUY",
        amount=100.00,
        price=98.50,
        pnl=12.50,
        r_multiple=1.25
    )
    results = await manager.send_trade_alert(trade)
    print(f"Results: {results}")
    
    print("\nSending demo system alert...")
    system = SystemAlert(
        timestamp=datetime.now(timezone.utc).isoformat(),
        level="success",
        title="Agent Online",
        message="FRED-SOL trading agent is now active and monitoring markets."
    )
    results = await manager.send_system_alert(system)
    print(f"Results: {results}")
    
    await manager.close()


if __name__ == "__main__":
    asyncio.run(main())
