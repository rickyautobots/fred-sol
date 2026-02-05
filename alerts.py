#!/usr/bin/env python3
"""
FRED Alerts

Notification system for trades, errors, and status updates.
Supports Telegram and console output.
"""

import os
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


@dataclass
class Alert:
    level: str  # INFO, TRADE, WARNING, ERROR
    title: str
    message: str
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def format_telegram(self) -> str:
        emoji = {"INFO": "ℹ️", "TRADE": "💰", "WARNING": "⚠️", "ERROR": "🚨"}.get(self.level, "📢")
        return f"{emoji} *{self.title}*\n\n{self.message}\n\n_{self.timestamp}_"
    
    def format_console(self) -> str:
        return f"[{self.level}] {self.title}: {self.message}"


class AlertManager:
    """Manages notifications across channels."""
    
    def __init__(
        self, 
        telegram_token: Optional[str] = None, 
        telegram_chat_id: Optional[str] = None,
        webhook_url: Optional[str] = None,
        discord_webhook: Optional[str] = None
    ):
        self.telegram_token = telegram_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = telegram_chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.webhook_url = webhook_url or os.getenv("ALERT_WEBHOOK_URL")
        self.discord_webhook = discord_webhook or os.getenv("DISCORD_WEBHOOK_URL")
        self.telegram_enabled = bool(self.telegram_token and self.telegram_chat_id and HAS_HTTPX)
        self.webhook_enabled = bool(self.webhook_url and HAS_HTTPX)
        self.discord_enabled = bool(self.discord_webhook and HAS_HTTPX)
        self.enabled = self.telegram_enabled or self.webhook_enabled or self.discord_enabled
    
    def _send_telegram(self, text: str):
        """Send message to Telegram."""
        if not self.telegram_enabled:
            return
        
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                "chat_id": self.telegram_chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            with httpx.Client() as client:
                client.post(url, json=data, timeout=10)
        except Exception as e:
            print(f"Telegram alert failed: {e}")
    
    def _send_webhook(self, alert: Alert):
        """Send alert to generic webhook (JSON payload)."""
        if not self.webhook_enabled:
            return
        
        try:
            payload = {
                "level": alert.level,
                "title": alert.title,
                "message": alert.message,
                "timestamp": alert.timestamp,
                "agent": "FRED-SOL"
            }
            with httpx.Client() as client:
                client.post(self.webhook_url, json=payload, timeout=10)
        except Exception as e:
            print(f"Webhook alert failed: {e}")
    
    def _send_discord(self, alert: Alert):
        """Send alert to Discord webhook."""
        if not self.discord_enabled:
            return
        
        try:
            colors = {"INFO": 0x00ff88, "TRADE": 0x00ff88, "WARNING": 0xffaa00, "ERROR": 0xff4444}
            emoji = {"INFO": "ℹ️", "TRADE": "💰", "WARNING": "⚠️", "ERROR": "🚨"}.get(alert.level, "📢")
            
            payload = {
                "embeds": [{
                    "title": f"{emoji} {alert.title}",
                    "description": alert.message,
                    "color": colors.get(alert.level, 0x888888),
                    "footer": {"text": f"FRED-SOL • {alert.timestamp}"}
                }]
            }
            with httpx.Client() as client:
                client.post(self.discord_webhook, json=payload, timeout=10)
        except Exception as e:
            print(f"Discord alert failed: {e}")
    
    def send(self, alert: Alert):
        """Send alert to all configured channels."""
        print(alert.format_console())
        
        if self.telegram_enabled:
            self._send_telegram(alert.format_telegram())
        
        if self.webhook_enabled:
            self._send_webhook(alert)
        
        if self.discord_enabled:
            self._send_discord(alert)
    
    def trade_executed(self, symbol: str, side: str, size: float, price: float, pnl: Optional[float] = None):
        """Alert for executed trade."""
        pnl_str = f"\nP&L: ${pnl:.2f}" if pnl is not None else ""
        self.send(Alert(
            level="TRADE",
            title=f"{side} {symbol}",
            message=f"Size: ${size:.2f}\nPrice: ${price:.4f}{pnl_str}"
        ))
    
    def opportunity_found(self, symbol: str, edge: float, size: float):
        """Alert for trading opportunity."""
        self.send(Alert(
            level="INFO",
            title=f"Opportunity: {symbol}",
            message=f"Edge: {edge:.1%}\nSuggested size: ${size:.2f}"
        ))
    
    def risk_warning(self, message: str):
        """Alert for risk limit approached."""
        self.send(Alert(
            level="WARNING",
            title="Risk Warning",
            message=message
        ))
    
    def error(self, message: str, details: str = ""):
        """Alert for errors."""
        self.send(Alert(
            level="ERROR",
            title="Error",
            message=f"{message}\n{details}" if details else message
        ))
    
    def status_update(self, capital: float, pnl: float, positions: int):
        """Daily/hourly status update."""
        self.send(Alert(
            level="INFO",
            title="Status Update",
            message=f"Capital: ${capital:.2f}\nP&L: ${pnl:+.2f}\nOpen positions: {positions}"
        ))


# Global instance
_alerts: Optional[AlertManager] = None

def get_alerts() -> AlertManager:
    global _alerts
    if _alerts is None:
        _alerts = AlertManager()
    return _alerts


if __name__ == "__main__":
    # Test (console only unless env vars set)
    alerts = AlertManager()
    
    alerts.trade_executed("SOL/USDC", "BUY", 100, 96.42)
    alerts.opportunity_found("JUP/USDC", 0.08, 50)
    alerts.risk_warning("Approaching daily loss limit")
    alerts.status_update(1050, 50, 2)
