#!/usr/bin/env python3
"""
FRED-SOL: Trading Metrics & Analytics
Performance tracking with R-multiple analysis

Built: 2026-02-06 07:20 CST by Ricky
"""

import json
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import statistics


@dataclass
class Trade:
    """Individual trade record"""
    id: str
    timestamp: datetime
    market: str
    side: str  # BUY or SELL
    entry_price: float
    exit_price: Optional[float] = None
    amount: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    pnl: float = 0.0
    r_multiple: float = 0.0
    status: str = "OPEN"  # OPEN, CLOSED, STOPPED
    notes: str = ""
    
    def calculate_r_multiple(self) -> float:
        """Calculate R-multiple for closed trade"""
        if self.status == "OPEN" or self.exit_price is None:
            return 0.0
        
        if self.stop_loss is None or self.stop_loss == self.entry_price:
            return 0.0
        
        risk = abs(self.entry_price - self.stop_loss)
        reward = self.exit_price - self.entry_price
        
        if self.side == "SELL":
            reward = -reward
        
        return reward / risk if risk > 0 else 0.0


@dataclass
class DailyStats:
    """Daily trading statistics"""
    date: str
    trades: int = 0
    wins: int = 0
    losses: int = 0
    total_pnl: float = 0.0
    total_r: float = 0.0
    max_win: float = 0.0
    max_loss: float = 0.0
    win_rate: float = 0.0
    avg_r: float = 0.0


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics"""
    # Basic stats
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # P&L
    total_pnl: float = 0.0
    average_pnl: float = 0.0
    max_win: float = 0.0
    max_loss: float = 0.0
    
    # R-multiples
    total_r: float = 0.0
    average_r: float = 0.0
    expectancy: float = 0.0  # Expected R per trade
    
    # Streaks
    current_streak: int = 0
    max_win_streak: int = 0
    max_lose_streak: int = 0
    
    # Risk metrics
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    profit_factor: float = 0.0
    
    # Time-based
    best_day: Optional[str] = None
    worst_day: Optional[str] = None
    avg_trade_duration: Optional[float] = None  # hours


class MetricsTracker:
    """
    Track and analyze trading performance
    
    Features:
    - Real-time metrics updates
    - R-multiple tracking
    - Streak analysis
    - Risk-adjusted returns
    - Daily/weekly/monthly rollups
    """
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.trades: List[Trade] = []
        self.daily_stats: Dict[str, DailyStats] = {}
    
    def add_trade(self, trade: Trade):
        """Add a trade to tracking"""
        self.trades.append(trade)
        
        if trade.status == "CLOSED":
            trade.r_multiple = trade.calculate_r_multiple()
            self._update_daily_stats(trade)
    
    def close_trade(
        self,
        trade_id: str,
        exit_price: float,
        status: str = "CLOSED"
    ) -> Optional[Trade]:
        """Close an open trade"""
        for trade in self.trades:
            if trade.id == trade_id and trade.status == "OPEN":
                trade.exit_price = exit_price
                trade.status = status
                
                # Calculate P&L
                if trade.side == "BUY":
                    trade.pnl = (exit_price - trade.entry_price) * trade.amount
                else:
                    trade.pnl = (trade.entry_price - exit_price) * trade.amount
                
                trade.r_multiple = trade.calculate_r_multiple()
                self._update_daily_stats(trade)
                return trade
        
        return None
    
    def _update_daily_stats(self, trade: Trade):
        """Update daily statistics"""
        date_str = trade.timestamp.strftime("%Y-%m-%d")
        
        if date_str not in self.daily_stats:
            self.daily_stats[date_str] = DailyStats(date=date_str)
        
        stats = self.daily_stats[date_str]
        stats.trades += 1
        stats.total_pnl += trade.pnl
        stats.total_r += trade.r_multiple
        
        if trade.pnl > 0:
            stats.wins += 1
            stats.max_win = max(stats.max_win, trade.pnl)
        elif trade.pnl < 0:
            stats.losses += 1
            stats.max_loss = min(stats.max_loss, trade.pnl)
        
        # Update derived metrics
        stats.win_rate = stats.wins / stats.trades * 100 if stats.trades > 0 else 0
        stats.avg_r = stats.total_r / stats.trades if stats.trades > 0 else 0
    
    def get_metrics(self) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        closed = [t for t in self.trades if t.status in ["CLOSED", "STOPPED"]]
        
        if not closed:
            return PerformanceMetrics()
        
        wins = [t for t in closed if t.pnl > 0]
        losses = [t for t in closed if t.pnl < 0]
        
        metrics = PerformanceMetrics(
            total_trades=len(closed),
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate=len(wins) / len(closed) * 100 if closed else 0,
            total_pnl=sum(t.pnl for t in closed),
            average_pnl=sum(t.pnl for t in closed) / len(closed),
            max_win=max((t.pnl for t in closed), default=0),
            max_loss=min((t.pnl for t in closed), default=0),
            total_r=sum(t.r_multiple for t in closed),
            average_r=sum(t.r_multiple for t in closed) / len(closed)
        )
        
        # Expectancy: (win_rate * avg_win) - (loss_rate * avg_loss) in R
        if wins and losses:
            avg_win_r = sum(t.r_multiple for t in wins) / len(wins)
            avg_loss_r = abs(sum(t.r_multiple for t in losses) / len(losses))
            win_rate = len(wins) / len(closed)
            metrics.expectancy = (win_rate * avg_win_r) - ((1 - win_rate) * avg_loss_r)
        
        # Profit factor
        gross_profit = sum(t.pnl for t in wins) if wins else 0
        gross_loss = abs(sum(t.pnl for t in losses)) if losses else 1
        metrics.profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Streaks
        metrics.max_win_streak, metrics.max_lose_streak = self._calculate_streaks(closed)
        
        # Best/worst day
        if self.daily_stats:
            best = max(self.daily_stats.values(), key=lambda d: d.total_pnl)
            worst = min(self.daily_stats.values(), key=lambda d: d.total_pnl)
            metrics.best_day = f"{best.date}: ${best.total_pnl:+,.2f}"
            metrics.worst_day = f"{worst.date}: ${worst.total_pnl:+,.2f}"
        
        # Max drawdown
        metrics.max_drawdown = self._calculate_max_drawdown(closed)
        
        # Sharpe ratio (simplified)
        if len(closed) > 1:
            returns = [t.pnl for t in closed]
            avg_return = statistics.mean(returns)
            std_return = statistics.stdev(returns)
            if std_return > 0:
                metrics.sharpe_ratio = avg_return / std_return
        
        return metrics
    
    def _calculate_streaks(self, trades: List[Trade]) -> Tuple[int, int]:
        """Calculate max win and lose streaks"""
        max_win = max_lose = 0
        current_win = current_lose = 0
        
        for trade in sorted(trades, key=lambda t: t.timestamp):
            if trade.pnl > 0:
                current_win += 1
                current_lose = 0
                max_win = max(max_win, current_win)
            elif trade.pnl < 0:
                current_lose += 1
                current_win = 0
                max_lose = max(max_lose, current_lose)
        
        return max_win, max_lose
    
    def _calculate_max_drawdown(self, trades: List[Trade]) -> float:
        """Calculate maximum drawdown"""
        if not trades:
            return 0.0
        
        equity = [0.0]
        for trade in sorted(trades, key=lambda t: t.timestamp):
            equity.append(equity[-1] + trade.pnl)
        
        peak = equity[0]
        max_dd = 0.0
        
        for value in equity:
            if value > peak:
                peak = value
            dd = (peak - value) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        
        return max_dd
    
    def get_summary(self) -> str:
        """Get formatted summary string"""
        m = self.get_metrics()
        
        return f"""
╔══════════════════════════════════════╗
║     FRED-SOL Performance Summary     ║
╠══════════════════════════════════════╣
║ Trades: {m.total_trades:>4} │ Win Rate: {m.win_rate:>5.1f}% ║
║ Wins:   {m.winning_trades:>4} │ Losses:   {m.losing_trades:>5}   ║
╠══════════════════════════════════════╣
║ Total P&L:    ${m.total_pnl:>10,.2f}       ║
║ Average P&L:  ${m.average_pnl:>10,.2f}       ║
║ Max Win:      ${m.max_win:>10,.2f}       ║
║ Max Loss:     ${m.max_loss:>10,.2f}       ║
╠══════════════════════════════════════╣
║ Total R:      {m.total_r:>10.2f}R       ║
║ Average R:    {m.average_r:>10.2f}R       ║
║ Expectancy:   {m.expectancy:>10.2f}R       ║
╠══════════════════════════════════════╣
║ Profit Factor:  {m.profit_factor:>8.2f}         ║
║ Max Drawdown:   {m.max_drawdown:>8.1%}         ║
║ Sharpe Ratio:   {m.sharpe_ratio:>8.2f}         ║
╠══════════════════════════════════════╣
║ Best Day:  {m.best_day or 'N/A':>24} ║
║ Worst Day: {m.worst_day or 'N/A':>24} ║
╚══════════════════════════════════════╝
        """.strip()
    
    def save(self, filename: str = "metrics.json"):
        """Save metrics to file"""
        data = {
            "generated": datetime.now(timezone.utc).isoformat(),
            "metrics": asdict(self.get_metrics()),
            "daily_stats": {k: asdict(v) for k, v in self.daily_stats.items()},
            "trades": [asdict(t) for t in self.trades[-100:]]  # Last 100
        }
        
        with open(self.data_dir / filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def load(self, filename: str = "metrics.json"):
        """Load metrics from file"""
        filepath = self.data_dir / filename
        if not filepath.exists():
            return
        
        with open(filepath) as f:
            data = json.load(f)
        
        # Reconstruct trades
        for t in data.get("trades", []):
            t["timestamp"] = datetime.fromisoformat(t["timestamp"])
            self.trades.append(Trade(**t))
        
        # Reconstruct daily stats
        for date, stats in data.get("daily_stats", {}).items():
            self.daily_stats[date] = DailyStats(**stats)


if __name__ == "__main__":
    # Demo
    tracker = MetricsTracker()
    
    # Add sample trades
    trades = [
        Trade("t1", datetime.now() - timedelta(days=5), "SOL/USDC", "BUY", 
              98.0, 105.0, 10, 95.0, 110.0, 70.0, 2.33, "CLOSED"),
        Trade("t2", datetime.now() - timedelta(days=4), "JUP/USDC", "BUY",
              0.80, 0.72, 100, 0.75, 0.90, -8.0, -1.6, "CLOSED"),
        Trade("t3", datetime.now() - timedelta(days=3), "BONK/USDC", "BUY",
              0.000018, 0.000025, 1000000, 0.000015, 0.000030, 7.0, 2.33, "CLOSED"),
        Trade("t4", datetime.now() - timedelta(days=2), "WIF/USDC", "SELL",
              2.50, 2.20, 50, 2.70, 2.00, 15.0, 1.5, "CLOSED"),
        Trade("t5", datetime.now() - timedelta(days=1), "PYTH/USDC", "BUY",
              0.42, 0.48, 200, 0.38, 0.55, 12.0, 1.5, "CLOSED"),
    ]
    
    for t in trades:
        tracker.add_trade(t)
    
    print(tracker.get_summary())
