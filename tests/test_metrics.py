#!/usr/bin/env python3
"""
Tests for trading metrics
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import sys
sys.path.insert(0, '..')

from metrics import (
    Trade, DailyStats, PerformanceMetrics, MetricsTracker
)


class TestTrade:
    """Test Trade class"""
    
    def test_trade_creation(self):
        trade = Trade(
            id="t1",
            timestamp=datetime.now(timezone.utc),
            market="SOL/USDC",
            side="BUY",
            entry_price=100.0,
            amount=10.0
        )
        
        assert trade.status == "OPEN"
        assert trade.pnl == 0.0
    
    def test_r_multiple_calculation_long(self):
        trade = Trade(
            id="t1",
            timestamp=datetime.now(timezone.utc),
            market="SOL/USDC",
            side="BUY",
            entry_price=100.0,
            exit_price=115.0,
            stop_loss=95.0,
            amount=10.0,
            status="CLOSED"
        )
        
        r = trade.calculate_r_multiple()
        # Risk: 100-95 = 5, Reward: 115-100 = 15
        # R = 15/5 = 3.0
        assert r == 3.0
    
    def test_r_multiple_calculation_short(self):
        trade = Trade(
            id="t1",
            timestamp=datetime.now(timezone.utc),
            market="SOL/USDC",
            side="SELL",
            entry_price=100.0,
            exit_price=85.0,
            stop_loss=105.0,
            amount=10.0,
            status="CLOSED"
        )
        
        r = trade.calculate_r_multiple()
        # Risk: 105-100 = 5, Reward: 100-85 = 15
        # R = 15/5 = 3.0
        assert r == 3.0
    
    def test_r_multiple_open_trade(self):
        trade = Trade(
            id="t1",
            timestamp=datetime.now(timezone.utc),
            market="SOL/USDC",
            side="BUY",
            entry_price=100.0,
            status="OPEN"
        )
        
        assert trade.calculate_r_multiple() == 0.0
    
    def test_r_multiple_no_stop_loss(self):
        trade = Trade(
            id="t1",
            timestamp=datetime.now(timezone.utc),
            market="SOL/USDC",
            side="BUY",
            entry_price=100.0,
            exit_price=110.0,
            status="CLOSED"
        )
        
        assert trade.calculate_r_multiple() == 0.0


class TestDailyStats:
    """Test DailyStats class"""
    
    def test_daily_stats_defaults(self):
        stats = DailyStats(date="2026-02-06")
        
        assert stats.trades == 0
        assert stats.wins == 0
        assert stats.losses == 0
        assert stats.win_rate == 0.0


class TestMetricsTracker:
    """Test MetricsTracker class"""
    
    @pytest.fixture
    def tracker(self):
        t = MetricsTracker()
        
        # Add sample trades
        trades = [
            Trade("t1", datetime.now(timezone.utc) - timedelta(days=5),
                  "SOL/USDC", "BUY", 100.0, 110.0, 10, 95.0, 120.0,
                  100.0, 2.0, "CLOSED"),
            Trade("t2", datetime.now(timezone.utc) - timedelta(days=4),
                  "JUP/USDC", "BUY", 0.80, 0.72, 100, 0.75, 0.90,
                  -8.0, -1.6, "CLOSED"),
            Trade("t3", datetime.now(timezone.utc) - timedelta(days=3),
                  "BONK/USDC", "BUY", 0.00002, 0.00003, 1000000, 0.000015, 0.00004,
                  10.0, 2.0, "CLOSED"),
        ]
        
        for trade in trades:
            t.add_trade(trade)
        
        return t
    
    def test_add_trade(self, tracker):
        assert len(tracker.trades) == 3
    
    def test_close_trade(self):
        t = MetricsTracker()
        
        trade = Trade(
            id="t1",
            timestamp=datetime.now(timezone.utc),
            market="SOL/USDC",
            side="BUY",
            entry_price=100.0,
            amount=10.0,
            stop_loss=95.0
        )
        t.add_trade(trade)
        
        closed = t.close_trade("t1", exit_price=115.0)
        
        assert closed.status == "CLOSED"
        assert closed.pnl == 150.0  # (115-100) * 10
    
    def test_get_metrics_basic(self, tracker):
        metrics = tracker.get_metrics()
        
        assert metrics.total_trades == 3
        assert metrics.winning_trades == 2
        assert metrics.losing_trades == 1
    
    def test_win_rate(self, tracker):
        metrics = tracker.get_metrics()
        
        # 2 wins / 3 total = 66.67%
        assert 66 < metrics.win_rate < 67
    
    def test_total_pnl(self, tracker):
        metrics = tracker.get_metrics()
        
        # 100 - 8 + 10 = 102
        assert metrics.total_pnl == 102.0
    
    def test_total_r(self, tracker):
        metrics = tracker.get_metrics()
        
        # Sum of R-multiples from trades
        assert metrics.total_r != 0  # Has some R value
    
    def test_profit_factor(self, tracker):
        metrics = tracker.get_metrics()
        
        # Gross profit: 100 + 10 = 110
        # Gross loss: 8
        # PF = 110/8 = 13.75
        assert 13.7 < metrics.profit_factor < 13.8
    
    def test_daily_stats_updated(self, tracker):
        assert len(tracker.daily_stats) > 0
    
    def test_get_summary(self, tracker):
        summary = tracker.get_summary()
        
        assert "FRED-SOL" in summary
        assert "Win Rate" in summary
        assert "Total P&L" in summary
    
    def test_empty_tracker_metrics(self):
        t = MetricsTracker()
        metrics = t.get_metrics()
        
        assert metrics.total_trades == 0
        assert metrics.win_rate == 0.0


class TestStreakCalculation:
    """Test win/lose streak tracking"""
    
    def test_max_win_streak(self):
        t = MetricsTracker()
        
        for i, pnl in enumerate([10, 20, 30, -5, 15, 25]):
            trade = Trade(
                id=f"t{i}",
                timestamp=datetime.now(timezone.utc) - timedelta(hours=6-i),
                market="SOL/USDC",
                side="BUY",
                entry_price=100.0,
                exit_price=100.0,
                amount=10.0,
                pnl=pnl,
                status="CLOSED"
            )
            t.add_trade(trade)
        
        metrics = t.get_metrics()
        
        assert metrics.max_win_streak == 3
        assert metrics.max_lose_streak == 1


class TestDrawdown:
    """Test max drawdown calculation"""
    
    def test_max_drawdown(self):
        t = MetricsTracker()
        
        # Sequence: +100, +50, -80, -50, +200
        # Equity: 0, 100, 150, 70, 20, 220
        # Peak at 150, trough at 20, DD = (150-20)/150 = 86.7%
        
        pnls = [100, 50, -80, -50, 200]
        for i, pnl in enumerate(pnls):
            trade = Trade(
                id=f"t{i}",
                timestamp=datetime.now(timezone.utc) - timedelta(hours=5-i),
                market="SOL/USDC",
                side="BUY",
                entry_price=100.0,
                exit_price=100.0,
                amount=10.0,
                pnl=pnl,
                status="CLOSED"
            )
            t.add_trade(trade)
        
        metrics = t.get_metrics()
        
        assert metrics.max_drawdown > 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
