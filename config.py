#!/usr/bin/env python3
"""
FRED-SOL: Configuration Management
Environment-based config with validation

Built: 2026-02-06 07:10 CST by Ricky
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from enum import Enum


class Network(Enum):
    MAINNET = "mainnet"
    DEVNET = "devnet"
    TESTNET = "testnet"


class TradingMode(Enum):
    DRY_RUN = "dry_run"
    PAPER = "paper"
    LIVE = "live"


@dataclass
class WalletConfig:
    """Wallet configuration"""
    address: str
    private_key_path: Optional[str] = None
    
    def has_signing_capability(self) -> bool:
        return self.private_key_path is not None


@dataclass
class RiskConfig:
    """Risk management parameters"""
    max_position_pct: float = 0.05  # 5% max per trade
    max_daily_loss_pct: float = 0.10  # 10% max daily loss
    min_edge: float = 0.05  # 5% minimum edge
    min_r_multiple: float = 1.5  # 1.5R minimum
    max_open_positions: int = 5
    
    def validate(self):
        assert 0 < self.max_position_pct <= 0.25, "Max position must be 0-25%"
        assert 0 < self.max_daily_loss_pct <= 0.50, "Max daily loss must be 0-50%"
        assert 0 <= self.min_edge <= 0.50, "Min edge must be 0-50%"
        assert self.min_r_multiple > 0, "Min R-multiple must be positive"


@dataclass  
class RPCConfig:
    """Solana RPC configuration"""
    mainnet_url: str = "https://api.mainnet-beta.solana.com"
    devnet_url: str = "https://api.devnet.solana.com"
    testnet_url: str = "https://api.testnet.solana.com"
    commitment: str = "confirmed"
    timeout: int = 30
    
    def get_url(self, network: Network) -> str:
        urls = {
            Network.MAINNET: self.mainnet_url,
            Network.DEVNET: self.devnet_url,
            Network.TESTNET: self.testnet_url
        }
        return urls[network]


@dataclass
class AlertConfig:
    """Alert/notification configuration"""
    discord_webhook: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    slack_webhook: Optional[str] = None
    
    def has_any_provider(self) -> bool:
        return any([
            self.discord_webhook,
            self.telegram_bot_token and self.telegram_chat_id,
            self.slack_webhook
        ])


@dataclass
class LLMConfig:
    """LLM inference configuration"""
    provider: str = "anthropic"
    model: str = "claude-3-sonnet"
    api_key: Optional[str] = None
    x402_endpoint: Optional[str] = None
    max_tokens: int = 1024
    temperature: float = 0.3
    
    def get_api_key(self) -> str:
        if self.api_key:
            return self.api_key
        return os.environ.get(f"{self.provider.upper()}_API_KEY", "")


@dataclass
class FREDConfig:
    """
    Main FRED configuration container
    
    Loads from environment variables and optional config file.
    All sensitive values should come from environment.
    """
    # Core settings
    network: Network = Network.MAINNET
    mode: TradingMode = TradingMode.DRY_RUN
    
    # Sub-configs
    wallet: WalletConfig = field(default_factory=lambda: WalletConfig(
        address=os.environ.get("SOLANA_WALLET", "")
    ))
    risk: RiskConfig = field(default_factory=RiskConfig)
    rpc: RPCConfig = field(default_factory=RPCConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    
    # Agent identity
    agent_id: Optional[int] = None  # ERC-8004 ID
    agent_name: str = "FRED"
    
    @classmethod
    def from_env(cls) -> "FREDConfig":
        """Load config from environment variables"""
        config = cls()
        
        # Network
        network_str = os.environ.get("SOLANA_NETWORK", "mainnet").lower()
        config.network = Network(network_str)
        
        # Trading mode
        mode_str = os.environ.get("TRADING_MODE", "dry_run").lower()
        config.mode = TradingMode(mode_str)
        
        # Wallet
        config.wallet = WalletConfig(
            address=os.environ.get("SOLANA_WALLET", ""),
            private_key_path=os.environ.get("SOLANA_KEY_PATH")
        )
        
        # RPC (allow custom endpoints)
        if rpc_url := os.environ.get("SOLANA_RPC_URL"):
            config.rpc.mainnet_url = rpc_url
        
        # Alerts
        config.alerts = AlertConfig(
            discord_webhook=os.environ.get("DISCORD_WEBHOOK"),
            telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=os.environ.get("TELEGRAM_CHAT_ID"),
            slack_webhook=os.environ.get("SLACK_WEBHOOK")
        )
        
        # LLM
        config.llm = LLMConfig(
            provider=os.environ.get("LLM_PROVIDER", "anthropic"),
            model=os.environ.get("LLM_MODEL", "claude-3-sonnet"),
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
            x402_endpoint=os.environ.get("X402_ENDPOINT")
        )
        
        # Agent identity
        if agent_id := os.environ.get("ERC8004_AGENT_ID"):
            config.agent_id = int(agent_id)
        
        return config
    
    @classmethod
    def from_file(cls, path: str) -> "FREDConfig":
        """Load config from JSON file"""
        with open(path) as f:
            data = json.load(f)
        
        config = cls()
        
        if "network" in data:
            config.network = Network(data["network"])
        if "mode" in data:
            config.mode = TradingMode(data["mode"])
        
        if "wallet" in data:
            config.wallet = WalletConfig(**data["wallet"])
        if "risk" in data:
            config.risk = RiskConfig(**data["risk"])
        if "llm" in data:
            config.llm = LLMConfig(**data["llm"])
        
        if "agent_id" in data:
            config.agent_id = data["agent_id"]
        if "agent_name" in data:
            config.agent_name = data["agent_name"]
        
        return config
    
    def validate(self):
        """Validate all config values"""
        assert self.wallet.address, "Wallet address required"
        self.risk.validate()
        
        if self.mode == TradingMode.LIVE:
            assert self.wallet.has_signing_capability(), "Live mode requires signing key"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (safe for logging)"""
        return {
            "network": self.network.value,
            "mode": self.mode.value,
            "wallet_address": self.wallet.address[:12] + "..." if self.wallet.address else None,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "risk": asdict(self.risk),
            "alerts_configured": self.alerts.has_any_provider(),
            "llm_provider": self.llm.provider
        }
    
    def save(self, path: str):
        """Save config to file (without secrets)"""
        data = {
            "network": self.network.value,
            "mode": self.mode.value,
            "wallet": {"address": self.wallet.address},
            "risk": asdict(self.risk),
            "agent_id": self.agent_id,
            "agent_name": self.agent_name
        }
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)


def get_config() -> FREDConfig:
    """
    Get FRED configuration
    
    Priority:
    1. Environment variables
    2. Config file (if FRED_CONFIG_PATH set)
    3. Defaults
    """
    config = FREDConfig.from_env()
    
    # Override with file if specified
    config_path = os.environ.get("FRED_CONFIG_PATH")
    if config_path and Path(config_path).exists():
        file_config = FREDConfig.from_file(config_path)
        # Merge (file takes precedence for non-secret values)
        if file_config.agent_id:
            config.agent_id = file_config.agent_id
        if file_config.agent_name != "FRED":
            config.agent_name = file_config.agent_name
        config.risk = file_config.risk
    
    return config


# Example config file template
EXAMPLE_CONFIG = """
{
  "network": "mainnet",
  "mode": "dry_run",
  "wallet": {
    "address": "YOUR_WALLET_ADDRESS"
  },
  "risk": {
    "max_position_pct": 0.05,
    "max_daily_loss_pct": 0.10,
    "min_edge": 0.05,
    "min_r_multiple": 1.5,
    "max_open_positions": 5
  },
  "agent_id": 1147,
  "agent_name": "FRED"
}
"""


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="FRED Config Manager")
    parser.add_argument("--show", action="store_true", help="Show current config")
    parser.add_argument("--validate", action="store_true", help="Validate config")
    parser.add_argument("--template", action="store_true", help="Print config template")
    args = parser.parse_args()
    
    if args.template:
        print(EXAMPLE_CONFIG)
    elif args.show or args.validate:
        config = get_config()
        
        if args.validate:
            try:
                config.validate()
                print("✅ Config valid")
            except AssertionError as e:
                print(f"❌ Config invalid: {e}")
        
        if args.show:
            print(json.dumps(config.to_dict(), indent=2))
    else:
        parser.print_help()
