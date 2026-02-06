#!/usr/bin/env python3
"""
FRED Performance Tracker

Tracks trading performance, generates reports, and calculates key metrics.
Designed for autonomous agents to self-evaluate and improve.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
import math


@dataclass
class Trade:
    """Individual trade record."""
    timestamp: str
    symbol: str
    side: str  # BUY or SELL
    size_usd: float
    entry_price: float
    exit_price: Optional[float] = None
    exit_timestamp: Optional[str] = None
    pnl: Optional[float] = None
    edge_estimate: float = 0.0
    confidence: float = 0.0
    status: str = "OPEN"  # OPEN, CLOSED, CANCELLED
    
    @property
    def r_multiple(self) -> Optional[float]:
        """R-multiple: PnL / initial risk."""
        if self.pnl is None:
            return None
        risk = self.size_usd * 0.02  # Assume 2% stop loss
        if risk == 0:
            return 0
        return self.pnl / risk


@dataclass
class DailyStats:
    """Daily performance statistics."""
    date: str
    trades: int = 0
    wins: int = 0
    losses: int = 0
    total_pnl: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_estimate: float = 0.0
    r_multiples: List[float] = field(default_factory=list)
    
    @property
    def expectancy(self) -> float:
        """Expected value per trade."""
        if self.trades == 0:
            return 0.0
        return self.total_pnl / self.trades
    
    @property
    def avg_r(self) -> float:
        """Average R-multiple."""
        if not self.r_multiples:
            return 0.0
        return sum(self.r_multiples) / len(self.r_multiples)


class PerformanceTracker:
    """Tracks and analyzes trading performance."""
    
    def __init__(self, data_dir: str = "data/performance"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.trades_file = self.data_dir / "trades.json"
        self.stats_file = self.data_dir / "daily_stats.json"
        self.trades: List[Trade] = []
        self.daily_stats: Dict[str, DailyStats] = {}
        self._load()
    
    def _load(self):
        """Load existing data."""
        if self.trades_file.exists():
            try:
                with open(self.trades_file) as f:
                    data = json.load(f)
                    self.trades = [Trade(**t) for t in data]
            except Exception as e:
                print(f"Failed to load trades: {e}")
        
        if self.stats_file.exists():
            try:
                with open(self.stats_file) as f:
                    data = json.load(f)
                    self.daily_stats = {k: DailyStats(**v) for k, v in data.items()}
            except Exception as e:
                print(f"Failed to load stats: {e}")
    
    def _save(self):
        """Persist data to disk."""
        with open(self.trades_file, "w") as f:
            json.dump([asdict(t) for t in self.trades], f, indent=2)
        
        with open(self.stats_file, "w") as f:
            json.dump({k: asdict(v) for k, v in self.daily_stats.items()}, f, indent=2)
    
    def record_trade(
        self,
        symbol: str,
        side: str,
        size_usd: float,
        price: float,
        edge_estimate: float = 0.0,
        confidence: float = 0.0
    ) -> Trade:
        """Record a new trade."""
        trade = Trade(
            timestamp=datetime.now().isoformat(),
            symbol=symbol,
            side=side,
            size_usd=size_usd,
            entry_price=price,
            edge_estimate=edge_estimate,
            confidence=confidence
        )
        self.trades.append(trade)
        self._save()
        return trade
    
    def close_trade(
        self,
        trade: Trade,
        exit_price: float,
        pnl: Optional[float] = None
    ):
        """Close an open trade."""
        trade.exit_price = exit_price
        trade.exit_timestamp = datetime.now().isoformat()
        trade.status = "CLOSED"
        
        # Calculate PnL if not provided
        if pnl is not None:
            trade.pnl = pnl
        else:
            if trade.side == "BUY":
                trade.pnl = (exit_price - trade.entry_price) / trade.entry_price * trade.size_usd
            else:
                trade.pnl = (trade.entry_price - exit_price) / trade.entry_price * trade.size_usd
        
        self._save()
        self._update_daily_stats(trade)
    
    def _update_daily_stats(self, trade: Trade):
        """Update daily stats with closed trade."""
        date = trade.timestamp[:10]  # YYYY-MM-DD
        
        if date not in self.daily_stats:
            self.daily_stats[date] = DailyStats(date=date)
        
        stats = self.daily_stats[date]
        stats.trades += 1
        
        if trade.pnl is not None:
            stats.total_pnl += trade.pnl
            
            if trade.pnl > 0:
                stats.wins += 1
                stats.gross_profit += trade.pnl
                if trade.pnl > stats.largest_win:
                    stats.largest_win = trade.pnl
            else:
                stats.losses += 1
                stats.gross_loss += abs(trade.pnl)
                if abs(trade.pnl) > stats.largest_loss:
                    stats.largest_loss = abs(trade.pnl)
            
            if trade.r_multiple is not None:
                stats.r_multiples.append(trade.r_multiple)
        
        # Recalculate derived metrics
        if stats.wins > 0:
            stats.avg_win = stats.gross_profit / stats.wins
        if stats.losses > 0:
            stats.avg_loss = stats.gross_loss / stats.losses
        if stats.trades > 0:
            stats.win_rate = stats.wins / stats.trades
        if stats.gross_loss > 0:
            stats.profit_factor = stats.gross_profit / stats.gross_loss
        
        self._save()
    
    def get_open_trades(self) -> List[Trade]:
        """Get all open trades."""
        return [t for t in self.trades if t.status == "OPEN"]
    
    def get_daily_report(self, date: Optional[str] = None) -> str:
        """Generate daily performance report."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        if date not in self.daily_stats:
            return f"No trades on {date}"
        
        stats = self.daily_stats[date]
        
        report = f"""
📊 FRED Daily Report — {date}
{'='*40}

📈 Performance
   Trades: {stats.trades}
   Win Rate: {stats.win_rate:.1%}
   P&L: ${stats.total_pnl:+.2f}
   
💰 Winners/Losers
   Wins: {stats.wins} | Losses: {stats.losses}
   Avg Win: ${stats.avg_win:.2f}
   Avg Loss: ${stats.avg_loss:.2f}
   Largest Win: ${stats.largest_win:.2f}
   Largest Loss: ${stats.largest_loss:.2f}

📐 Risk Metrics
   Profit Factor: {stats.profit_factor:.2f}
   Expectancy: ${stats.expectancy:.2f}/trade
   Avg R: {stats.avg_r:.2f}R

{'='*40}
"""
        return report.strip()
    
    def get_weekly_summary(self) -> str:
        """Generate weekly summary."""
        today = datetime.now()
        week_ago = today - timedelta(days=7)
        
        total_trades = 0
        total_pnl = 0.0
        total_wins = 0
        total_losses = 0
        
        for date_str, stats in self.daily_stats.items():
            date = datetime.fromisoformat(date_str)
            if date >= week_ago:
                total_trades += stats.trades
                total_pnl += stats.total_pnl
                total_wins += stats.wins
                total_losses += stats.losses
        
        win_rate = total_wins / total_trades if total_trades > 0 else 0
        
        return f"""
📈 FRED Weekly Summary
{'='*40}
Period: {week_ago.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}

Trades: {total_trades}
P&L: ${total_pnl:+.2f}
Win Rate: {win_rate:.1%}
Wins/Losses: {total_wins}/{total_losses}
{'='*40}
"""
    
    def get_expectancy_analysis(self) -> Dict[str, Any]:
        """Analyze trade expectancy for strategy tuning."""
        closed_trades = [t for t in self.trades if t.status == "CLOSED" and t.pnl is not None]
        
        if not closed_trades:
            return {"error": "No closed trades"}
        
        # Group by confidence levels
        confidence_buckets = {
            "low": [t for t in closed_trades if t.confidence < 0.5],
            "medium": [t for t in closed_trades if 0.5 <= t.confidence < 0.7],
            "high": [t for t in closed_trades if t.confidence >= 0.7]
        }
        
        analysis = {}
        for bucket, trades in confidence_buckets.items():
            if trades:
                wins = sum(1 for t in trades if t.pnl > 0)
                total_pnl = sum(t.pnl for t in trades)
                analysis[bucket] = {
                    "trades": len(trades),
                    "win_rate": wins / len(trades),
                    "avg_pnl": total_pnl / len(trades),
                    "total_pnl": total_pnl
                }
        
        # Edge accuracy
        edge_hits = sum(
            1 for t in closed_trades 
            if (t.edge_estimate > 0 and t.pnl > 0) or (t.edge_estimate < 0 and t.pnl < 0)
        )
        
        analysis["edge_accuracy"] = edge_hits / len(closed_trades) if closed_trades else 0
        
        return analysis


# Singleton instance
_tracker: Optional[PerformanceTracker] = None

def get_tracker() -> PerformanceTracker:
    global _tracker
    if _tracker is None:
        _tracker = PerformanceTracker()
    return _tracker


if __name__ == "__main__":
    # Demo
    tracker = PerformanceTracker(data_dir="/tmp/fred_perf_demo")
    
    # Simulate some trades
    t1 = tracker.record_trade("SOL/USDC", "BUY", 100, 95.0, edge_estimate=0.05, confidence=0.7)
    tracker.close_trade(t1, 97.0)  # Win
    
    t2 = tracker.record_trade("JUP/USDC", "BUY", 50, 0.85, edge_estimate=0.03, confidence=0.6)
    tracker.close_trade(t2, 0.82)  # Loss
    
    t3 = tracker.record_trade("RAY/USDC", "BUY", 75, 4.20, edge_estimate=0.08, confidence=0.8)
    tracker.close_trade(t3, 4.50)  # Win
    
    print(tracker.get_daily_report())
    print(tracker.get_expectancy_analysis())
