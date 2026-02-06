#!/usr/bin/env python3
"""
FRED-SOL: Live Trade Monitor
Real-time display of trading activity and P&L for demo/monitoring

Built: 2026-02-06 06:40 CST by Ricky
For: Solana AI Agent Hackathon ($100K prize pool)
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from pathlib import Path

try:
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


@dataclass
class Trade:
    """Single trade record"""
    id: str
    timestamp: datetime
    market: str
    side: str  # BUY or SELL
    outcome: str
    amount: float
    price: float
    status: str  # PENDING, FILLED, CANCELLED
    pnl: float = 0.0
    r_multiple: float = 0.0


@dataclass
class PortfolioState:
    """Current portfolio snapshot"""
    wallet_address: str
    balance_sol: float = 0.0
    balance_usdc: float = 0.0
    open_positions: int = 0
    total_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    total_r: float = 0.0
    last_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class LiveMonitor:
    """
    Real-time trading monitor with terminal UI
    
    Features:
    - Live trade feed
    - Portfolio P&L tracking
    - R-multiple analysis
    - Position sizing display
    """
    
    def __init__(
        self,
        wallet_address: str,
        data_dir: str = "./data",
        refresh_interval: float = 2.0
    ):
        self.wallet = wallet_address
        self.data_dir = Path(data_dir)
        self.refresh_interval = refresh_interval
        self.trades: List[Trade] = []
        self.portfolio = PortfolioState(wallet_address=wallet_address)
        self.running = False
        
        if RICH_AVAILABLE:
            self.console = Console()
        
    def load_trades(self, filepath: str = "demo_trades.json") -> List[Trade]:
        """Load trades from JSON file"""
        trade_file = self.data_dir / filepath
        if not trade_file.exists():
            return []
        
        with open(trade_file) as f:
            data = json.load(f)
        
        trades = []
        for t in data.get("trades", []):
            trades.append(Trade(
                id=t.get("id", ""),
                timestamp=datetime.fromisoformat(t.get("timestamp", datetime.now().isoformat())),
                market=t.get("market", ""),
                side=t.get("side", "BUY"),
                outcome=t.get("outcome", ""),
                amount=t.get("amount", 0),
                price=t.get("price", 0),
                status=t.get("status", "FILLED"),
                pnl=t.get("pnl", 0),
                r_multiple=t.get("r_multiple", 0)
            ))
        return trades
    
    def calculate_stats(self) -> Dict:
        """Calculate portfolio statistics"""
        if not self.trades:
            return {
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "total_r": 0,
                "avg_r": 0,
                "best_trade": 0,
                "worst_trade": 0
            }
        
        closed = [t for t in self.trades if t.status == "FILLED" and t.pnl != 0]
        wins = [t for t in closed if t.pnl > 0]
        losses = [t for t in closed if t.pnl < 0]
        
        total_pnl = sum(t.pnl for t in closed)
        total_r = sum(t.r_multiple for t in closed)
        
        return {
            "total_trades": len(self.trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": len(wins) / len(closed) * 100 if closed else 0,
            "total_pnl": total_pnl,
            "total_r": total_r,
            "avg_r": total_r / len(closed) if closed else 0,
            "best_trade": max((t.pnl for t in closed), default=0),
            "worst_trade": min((t.pnl for t in closed), default=0)
        }
    
    def render_header(self) -> Panel:
        """Render header panel"""
        header_text = Text()
        header_text.append("FRED-SOL ", style="bold cyan")
        header_text.append("Live Trade Monitor\n", style="white")
        header_text.append(f"Wallet: {self.wallet[:8]}...{self.wallet[-6:]}", style="dim")
        return Panel(header_text, title="🤖 AI Trading Agent", border_style="cyan")
    
    def render_stats(self) -> Panel:
        """Render statistics panel"""
        stats = self.calculate_stats()
        
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Metric", style="dim")
        table.add_column("Value", style="bold")
        
        pnl_style = "green" if stats["total_pnl"] >= 0 else "red"
        r_style = "green" if stats["total_r"] >= 0 else "red"
        
        table.add_row("Total Trades", str(stats["total_trades"]))
        table.add_row("Win Rate", f"{stats['win_rate']:.1f}%")
        table.add_row("Total P&L", Text(f"${stats['total_pnl']:,.2f}", style=pnl_style))
        table.add_row("Total R", Text(f"{stats['total_r']:+.2f}R", style=r_style))
        table.add_row("Avg R/Trade", f"{stats['avg_r']:+.2f}R")
        table.add_row("Best Trade", f"${stats['best_trade']:,.2f}")
        table.add_row("Worst Trade", f"${stats['worst_trade']:,.2f}")
        
        return Panel(table, title="📊 Statistics", border_style="green")
    
    def render_trades(self, limit: int = 10) -> Panel:
        """Render recent trades table"""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Time", style="dim", width=8)
        table.add_column("Market", width=20)
        table.add_column("Side", width=6)
        table.add_column("Amount", justify="right", width=10)
        table.add_column("P&L", justify="right", width=12)
        table.add_column("R", justify="right", width=8)
        
        recent = sorted(self.trades, key=lambda t: t.timestamp, reverse=True)[:limit]
        
        for trade in recent:
            side_style = "green" if trade.side == "BUY" else "red"
            pnl_style = "green" if trade.pnl >= 0 else "red"
            
            table.add_row(
                trade.timestamp.strftime("%H:%M:%S"),
                trade.market[:20],
                Text(trade.side, style=side_style),
                f"${trade.amount:,.2f}",
                Text(f"${trade.pnl:+,.2f}", style=pnl_style),
                f"{trade.r_multiple:+.2f}R"
            )
        
        return Panel(table, title="📈 Recent Trades", border_style="blue")
    
    def render_layout(self) -> Layout:
        """Build full terminal layout"""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=5),
            Layout(name="body")
        )
        
        layout["body"].split_row(
            Layout(name="stats", ratio=1),
            Layout(name="trades", ratio=2)
        )
        
        layout["header"].update(self.render_header())
        layout["stats"].update(self.render_stats())
        layout["trades"].update(self.render_trades())
        
        return layout
    
    async def run(self, duration: Optional[int] = None):
        """
        Run live monitor
        
        Args:
            duration: Run for N seconds, or indefinitely if None
        """
        if not RICH_AVAILABLE:
            print("Rich library not installed. Install with: pip install rich")
            return self._run_basic()
        
        self.running = True
        self.trades = self.load_trades()
        
        start_time = datetime.now()
        
        with Live(self.render_layout(), console=self.console, refresh_per_second=1) as live:
            try:
                while self.running:
                    # Reload trades (simulates real-time updates)
                    self.trades = self.load_trades()
                    live.update(self.render_layout())
                    
                    # Check duration limit
                    if duration and (datetime.now() - start_time).seconds >= duration:
                        break
                    
                    await asyncio.sleep(self.refresh_interval)
            except KeyboardInterrupt:
                self.running = False
    
    def _run_basic(self):
        """Basic text-only output when Rich not available"""
        self.trades = self.load_trades()
        stats = self.calculate_stats()
        
        print("\n" + "=" * 60)
        print("FRED-SOL Live Monitor")
        print("=" * 60)
        print(f"Wallet: {self.wallet}")
        print(f"Total Trades: {stats['total_trades']}")
        print(f"Win Rate: {stats['win_rate']:.1f}%")
        print(f"Total P&L: ${stats['total_pnl']:,.2f}")
        print(f"Total R: {stats['total_r']:+.2f}R")
        print("=" * 60)
        
        print("\nRecent Trades:")
        for trade in sorted(self.trades, key=lambda t: t.timestamp, reverse=True)[:5]:
            print(f"  {trade.timestamp.strftime('%H:%M')} | {trade.market[:15]} | "
                  f"{trade.side} | ${trade.pnl:+.2f}")


async def main():
    """Demo the live monitor"""
    import argparse
    
    parser = argparse.ArgumentParser(description="FRED-SOL Live Trade Monitor")
    parser.add_argument("--wallet", default="EamKq5ZhE2eZP6Z2LgAps9RUeNTem8K2udSeYNWuCPKF")
    parser.add_argument("--duration", type=int, help="Run for N seconds")
    parser.add_argument("--refresh", type=float, default=2.0, help="Refresh interval")
    args = parser.parse_args()
    
    monitor = LiveMonitor(
        wallet_address=args.wallet,
        refresh_interval=args.refresh
    )
    
    await monitor.run(duration=args.duration)


if __name__ == "__main__":
    asyncio.run(main())
