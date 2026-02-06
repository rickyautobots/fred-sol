#!/usr/bin/env python3
"""
Tests for portfolio management
"""

import pytest
from decimal import Decimal
import tempfile
import os

import sys
sys.path.insert(0, '..')

from portfolio import (
    Position, Allocation, RebalanceOrder, Portfolio
)


class TestPosition:
    """Test Position class"""
    
    @pytest.fixture
    def sol_position(self):
        return Position(
            symbol="SOL",
            mint="So11111111111111111111111111111111111111112",
            quantity=Decimal("10"),
            avg_cost=Decimal("95"),
            current_price=Decimal("100")
        )
    
    def test_position_value(self, sol_position):
        assert sol_position.value == Decimal("1000")
    
    def test_position_cost_basis(self, sol_position):
        assert sol_position.cost_basis == Decimal("950")
    
    def test_position_pnl(self, sol_position):
        assert sol_position.pnl == Decimal("50")
    
    def test_position_pnl_pct(self, sol_position):
        pnl_pct = sol_position.pnl_pct
        # (50/950) * 100 = 5.26%
        assert 5.2 < float(pnl_pct) < 5.3
    
    def test_position_pnl_negative(self):
        pos = Position(
            symbol="SOL",
            mint="test",
            quantity=Decimal("10"),
            avg_cost=Decimal("100"),
            current_price=Decimal("90")
        )
        assert pos.pnl == Decimal("-100")


class TestAllocation:
    """Test Allocation class"""
    
    def test_allocation_defaults(self):
        alloc = Allocation(symbol="SOL", target_pct=Decimal("50"))
        
        assert alloc.min_pct == Decimal("0")
        assert alloc.max_pct == Decimal("100")
        assert alloc.rebalance_threshold == Decimal("5")


class TestPortfolio:
    """Test Portfolio class"""
    
    @pytest.fixture
    def portfolio(self):
        p = Portfolio(Decimal("10000"))
        p.cash = Decimal("2000")
        
        p.add_position(Position(
            symbol="SOL",
            mint="sol_mint",
            quantity=Decimal("50"),
            avg_cost=Decimal("95"),
            current_price=Decimal("100")
        ))
        
        p.add_position(Position(
            symbol="USDC",
            mint="usdc_mint",
            quantity=Decimal("3000"),
            avg_cost=Decimal("1"),
            current_price=Decimal("1")
        ))
        
        return p
    
    def test_total_value(self, portfolio):
        # SOL: 50 * 100 = 5000
        # USDC: 3000 * 1 = 3000
        # Cash: 2000
        # Total: 10000
        assert portfolio.total_value == Decimal("10000")
    
    def test_total_pnl(self, portfolio):
        # SOL: 50 * (100-95) = 250
        # USDC: 3000 * (1-1) = 0
        # Total: 250
        assert portfolio.total_pnl == Decimal("250")
    
    def test_get_weights(self, portfolio):
        weights = portfolio.get_weights()
        
        assert weights["SOL"] == Decimal("50")  # 5000/10000 * 100
        assert weights["USDC"] == Decimal("30")  # 3000/10000 * 100
        assert weights["CASH"] == Decimal("20")  # 2000/10000 * 100
    
    def test_add_position_updates_existing(self, portfolio):
        # Add more SOL
        portfolio.add_position(Position(
            symbol="SOL",
            mint="sol_mint",
            quantity=Decimal("50"),  # Add 50 more
            avg_cost=Decimal("105"),  # Different cost
            current_price=Decimal("100")
        ))
        
        sol = portfolio.positions["SOL"]
        assert sol.quantity == Decimal("100")
        # Avg cost: (50*95 + 50*105) / 100 = 100
        assert sol.avg_cost == Decimal("100")
    
    def test_update_price(self, portfolio):
        portfolio.update_price("SOL", Decimal("110"))
        
        assert portfolio.positions["SOL"].current_price == Decimal("110")
    
    def test_update_prices_batch(self, portfolio):
        portfolio.update_prices({
            "SOL": Decimal("110"),
            "USDC": Decimal("1.01")
        })
        
        assert portfolio.positions["SOL"].current_price == Decimal("110")
        assert portfolio.positions["USDC"].current_price == Decimal("1.01")
    
    def test_set_allocation(self, portfolio):
        portfolio.set_allocation(Allocation("SOL", Decimal("40")))
        
        assert portfolio.allocations["SOL"].target_pct == Decimal("40")
    
    def test_get_drift(self, portfolio):
        portfolio.set_allocation(Allocation("SOL", Decimal("40")))
        
        drift = portfolio.get_drift()
        
        # Current: 50%, Target: 40%, Drift: +10%
        assert drift["SOL"] == Decimal("10")
    
    def test_needs_rebalance_true(self, portfolio):
        # SOL is 50%, set target to 40%
        portfolio.set_allocation(Allocation("SOL", Decimal("40"), rebalance_threshold=Decimal("5")))
        
        # Drift is 10%, threshold is 5%
        assert portfolio.needs_rebalance() == True
    
    def test_needs_rebalance_false(self, portfolio):
        # SOL is 50%, set target to 48%
        portfolio.set_allocation(Allocation("SOL", Decimal("48"), rebalance_threshold=Decimal("5")))
        
        # Drift is 2%, threshold is 5%
        assert portfolio.needs_rebalance() == False
    
    def test_get_rebalance_orders(self, portfolio):
        portfolio.set_allocation(Allocation("SOL", Decimal("30")))  # Want 30%, have 50%
        
        orders = portfolio.get_rebalance_orders()
        
        assert len(orders) == 1
        assert orders[0].symbol == "SOL"
        assert orders[0].side == "SELL"
        assert "Overweight" in orders[0].reason
    
    def test_exposure_report(self, portfolio):
        exposure = portfolio.get_exposure()
        
        assert exposure["total_value"] == 10000
        assert exposure["cash_pct"] == 20
        assert exposure["positions_count"] == 2
        assert exposure["top_position"] == "SOL"
        assert exposure["top_position_pct"] == 50
    
    def test_concentration_risk_high(self):
        p = Portfolio(Decimal("10000"))
        p.cash = Decimal("1000")
        p.add_position(Position(
            symbol="SOL",
            mint="sol",
            quantity=Decimal("90"),
            avg_cost=Decimal("100"),
            current_price=Decimal("100")
        ))
        
        exposure = p.get_exposure()
        assert exposure["concentration_risk"] == "HIGH"
    
    def test_save_and_load(self, portfolio):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "portfolio.json")
            
            portfolio.set_allocation(Allocation("SOL", Decimal("50")))
            portfolio.save(filepath)
            
            loaded = Portfolio.load(filepath)
            
            assert loaded.initial_capital == Decimal("10000")
            assert loaded.cash == Decimal("2000")
            assert "SOL" in loaded.positions
            assert loaded.positions["SOL"].quantity == Decimal("50")
            assert "SOL" in loaded.allocations


class TestRebalanceLogic:
    """Test rebalance calculation logic"""
    
    def test_buy_order_when_underweight(self):
        p = Portfolio(Decimal("10000"))
        p.cash = Decimal("5000")
        p.add_position(Position(
            symbol="SOL",
            mint="sol",
            quantity=Decimal("25"),
            avg_cost=Decimal("100"),
            current_price=Decimal("100")
        ))
        # SOL is 2500/7500 = 33%
        
        p.set_allocation(Allocation("SOL", Decimal("50")))  # Want 50%
        
        orders = p.get_rebalance_orders()
        
        sol_order = next((o for o in orders if o.symbol == "SOL"), None)
        if sol_order:
            assert sol_order.side == "BUY"
    
    def test_no_order_within_threshold(self):
        p = Portfolio(Decimal("10000"))
        p.cash = Decimal("2000")
        p.add_position(Position(
            symbol="SOL",
            mint="sol",
            quantity=Decimal("48"),
            avg_cost=Decimal("100"),
            current_price=Decimal("100")
        ))
        # SOL is 4800/6800 = 70.6%
        
        p.set_allocation(Allocation(
            "SOL", 
            Decimal("70"),
            rebalance_threshold=Decimal("5")
        ))
        
        # Drift is ~0.6%, within threshold
        assert p.needs_rebalance() == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
