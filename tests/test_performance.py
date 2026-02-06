#!/usr/bin/env python3
"""Tests for performance_tracker module."""

import pytest
import tempfile
import shutil
from pathlib import Path

from performance_tracker import Trade, DailyStats, PerformanceTracker


class TestTrade:
    """Tests for Trade dataclass."""
    
    def test_trade_creation(self):
        trade = Trade(
            timestamp="2026-02-05T10:00:00",
            symbol="SOL/USDC",
            side="BUY",
            size_usd=100.0,
            entry_price=95.0
        )
        assert trade.symbol == "SOL/USDC"
        assert trade.status == "OPEN"
    
    def test_r_multiple_calculation(self):
        trade = Trade(
            timestamp="2026-02-05T10:00:00",
            symbol="SOL/USDC",
            side="BUY",
            size_usd=100.0,
            entry_price=95.0,
            exit_price=97.0,
            pnl=2.10  # ~2% gain
        )
        # Risk is 2% of size = $2
        # R = 2.10 / 2 = 1.05
        assert trade.r_multiple is not None
        assert 1.0 <= trade.r_multiple <= 1.1
    
    def test_r_multiple_none_when_open(self):
        trade = Trade(
            timestamp="2026-02-05T10:00:00",
            symbol="SOL/USDC",
            side="BUY",
            size_usd=100.0,
            entry_price=95.0
        )
        assert trade.r_multiple is None


class TestDailyStats:
    """Tests for DailyStats dataclass."""
    
    def test_expectancy_calculation(self):
        stats = DailyStats(
            date="2026-02-05",
            trades=10,
            total_pnl=50.0
        )
        assert stats.expectancy == 5.0
    
    def test_avg_r_calculation(self):
        stats = DailyStats(
            date="2026-02-05",
            r_multiples=[1.0, 2.0, -0.5, 1.5]
        )
        assert stats.avg_r == 1.0
    
    def test_zero_trades_expectancy(self):
        stats = DailyStats(date="2026-02-05")
        assert stats.expectancy == 0.0


class TestPerformanceTracker:
    """Tests for PerformanceTracker class."""
    
    @pytest.fixture
    def tracker(self):
        """Create tracker with temp directory."""
        temp_dir = tempfile.mkdtemp()
        tracker = PerformanceTracker(data_dir=temp_dir)
        yield tracker
        shutil.rmtree(temp_dir)
    
    def test_record_trade(self, tracker):
        trade = tracker.record_trade(
            symbol="SOL/USDC",
            side="BUY",
            size_usd=100.0,
            price=95.0
        )
        assert trade.symbol == "SOL/USDC"
        assert len(tracker.trades) == 1
    
    def test_close_trade_calculates_pnl(self, tracker):
        trade = tracker.record_trade("SOL/USDC", "BUY", 100.0, 95.0)
        tracker.close_trade(trade, exit_price=97.0)
        
        assert trade.status == "CLOSED"
        assert trade.pnl is not None
        assert trade.pnl > 0  # Should be a win
    
    def test_close_trade_sell_side(self, tracker):
        trade = tracker.record_trade("SOL/USDC", "SELL", 100.0, 100.0)
        tracker.close_trade(trade, exit_price=95.0)  # Price dropped = win for short
        
        assert trade.pnl > 0
    
    def test_daily_stats_updated(self, tracker):
        trade = tracker.record_trade("SOL/USDC", "BUY", 100.0, 95.0)
        tracker.close_trade(trade, exit_price=97.0)
        
        date = trade.timestamp[:10]
        assert date in tracker.daily_stats
        assert tracker.daily_stats[date].trades == 1
        assert tracker.daily_stats[date].wins == 1
    
    def test_get_open_trades(self, tracker):
        t1 = tracker.record_trade("SOL/USDC", "BUY", 100.0, 95.0)
        t2 = tracker.record_trade("JUP/USDC", "BUY", 50.0, 0.85)
        tracker.close_trade(t1, exit_price=97.0)
        
        open_trades = tracker.get_open_trades()
        assert len(open_trades) == 1
        assert open_trades[0].symbol == "JUP/USDC"
    
    def test_daily_report_generation(self, tracker):
        trade = tracker.record_trade("SOL/USDC", "BUY", 100.0, 95.0)
        tracker.close_trade(trade, exit_price=97.0)
        
        report = tracker.get_daily_report()
        assert "FRED Daily Report" in report
        assert "Trades: 1" in report
    
    def test_persistence(self, tracker):
        """Test that data persists across instances."""
        trade = tracker.record_trade("SOL/USDC", "BUY", 100.0, 95.0)
        tracker.close_trade(trade, exit_price=97.0)
        
        # Create new tracker with same directory
        new_tracker = PerformanceTracker(data_dir=tracker.data_dir)
        assert len(new_tracker.trades) == 1
        assert new_tracker.trades[0].symbol == "SOL/USDC"


class TestExpectancyAnalysis:
    """Tests for expectancy analysis."""
    
    @pytest.fixture
    def tracker_with_trades(self):
        temp_dir = tempfile.mkdtemp()
        tracker = PerformanceTracker(data_dir=temp_dir)
        
        # High confidence trades
        t1 = tracker.record_trade("SOL", "BUY", 100, 95, confidence=0.8, edge_estimate=0.05)
        tracker.close_trade(t1, 97)
        
        t2 = tracker.record_trade("JUP", "BUY", 100, 0.85, confidence=0.75, edge_estimate=0.04)
        tracker.close_trade(t2, 0.90)
        
        # Low confidence trade
        t3 = tracker.record_trade("RAY", "BUY", 50, 4.0, confidence=0.4, edge_estimate=0.02)
        tracker.close_trade(t3, 3.9)  # Loss
        
        yield tracker
        shutil.rmtree(temp_dir)
    
    def test_confidence_buckets(self, tracker_with_trades):
        analysis = tracker_with_trades.get_expectancy_analysis()
        
        assert "high" in analysis
        assert "low" in analysis
        assert analysis["high"]["trades"] == 2
        assert analysis["low"]["trades"] == 1
    
    def test_edge_accuracy(self, tracker_with_trades):
        analysis = tracker_with_trades.get_expectancy_analysis()
        
        # 2 trades had positive edge and won, 1 had positive edge and lost
        assert "edge_accuracy" in analysis
        assert 0 <= analysis["edge_accuracy"] <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
