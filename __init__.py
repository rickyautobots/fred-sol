"""
FRED-SOL: Autonomous Solana Trading Agent

Built for Solana AI Agent Hackathon 2026 (Feb 2-12)
Prize Pool: $100,000

Features:
- LLM-based probability estimation
- Kelly criterion position sizing
- Native Solana integration (Jupiter swaps)
- Multi-provider alerts (Discord/Telegram/Slack)
- Real-time health monitoring
- Pluggable strategy framework

Usage:
    from fred_sol import FREDAgent, get_config
    
    config = get_config()
    agent = FREDAgent(config)
    await agent.run()

CLI:
    python -m fred_sol.cli portfolio
    python -m fred_sol.cli scan
    python -m fred_sol.cli run --dry-run

Stats (as of 2026-02-06):
- 11,000+ lines of Python
- 200+ test cases
- 25 modules

GitHub: github.com/rickyautobots/fred-sol
Agent ID: #603 (Colosseum)
Project ID: #294 (Colosseum)
ERC-8004 ID: 1147 (Base)
"""

__version__ = "0.1.0"
__author__ = "Ricky (AI Agent)"
__hackathon__ = "Solana AI Agent Hackathon 2026"

# Core exports
from .config import FREDConfig, get_config, Network, TradingMode
from .agent import FREDAgent
from .strategy import (
    Strategy, Signal, TradeSignal, MarketData,
    MomentumStrategy, MeanReversionStrategy, BreakoutStrategy,
    CompositeStrategy, get_strategy, STRATEGIES
)
from .portfolio import Portfolio, Position, Allocation
from .metrics import MetricsTracker, Trade, PerformanceMetrics
from .health import HealthChecker, HealthStatus, CheckResult
from .scheduler import Scheduler, ScheduledTask, TaskPriority
from .webhook_alerts import AlertManager, TradeAlert, SystemAlert
from .solana_integration import SolanaClient, JupiterSwap, FREDSolanaTrader

__all__ = [
    # Config
    "FREDConfig", "get_config", "Network", "TradingMode",
    
    # Core
    "FREDAgent",
    
    # Strategy
    "Strategy", "Signal", "TradeSignal", "MarketData",
    "MomentumStrategy", "MeanReversionStrategy", "BreakoutStrategy",
    "CompositeStrategy", "get_strategy", "STRATEGIES",
    
    # Portfolio
    "Portfolio", "Position", "Allocation",
    
    # Metrics
    "MetricsTracker", "Trade", "PerformanceMetrics",
    
    # Health
    "HealthChecker", "HealthStatus", "CheckResult",
    
    # Scheduler
    "Scheduler", "ScheduledTask", "TaskPriority",
    
    # Alerts
    "AlertManager", "TradeAlert", "SystemAlert",
    
    # Solana
    "SolanaClient", "JupiterSwap", "FREDSolanaTrader",
]
