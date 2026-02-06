#!/usr/bin/env python3
"""
FRED-SOL: Portfolio Management
Track positions, rebalancing, and multi-asset allocation

Built: 2026-02-06 07:25 CST by Ricky
"""

import json
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path
from decimal import Decimal, ROUND_DOWN


@dataclass
class Position:
    """Single position in portfolio"""
    symbol: str
    mint: str
    quantity: Decimal
    avg_cost: Decimal
    current_price: Decimal = Decimal("0")
    
    @property
    def value(self) -> Decimal:
        return self.quantity * self.current_price
    
    @property
    def cost_basis(self) -> Decimal:
        return self.quantity * self.avg_cost
    
    @property
    def pnl(self) -> Decimal:
        return self.value - self.cost_basis
    
    @property
    def pnl_pct(self) -> Decimal:
        if self.cost_basis == 0:
            return Decimal("0")
        return (self.pnl / self.cost_basis) * 100


@dataclass
class Allocation:
    """Target allocation for an asset"""
    symbol: str
    target_pct: Decimal  # Target percentage (0-100)
    min_pct: Decimal = Decimal("0")
    max_pct: Decimal = Decimal("100")
    rebalance_threshold: Decimal = Decimal("5")  # Trigger rebalance if off by this %


@dataclass
class RebalanceOrder:
    """Order needed to rebalance portfolio"""
    symbol: str
    side: str  # BUY or SELL
    quantity: Decimal
    target_value: Decimal
    current_value: Decimal
    reason: str


class Portfolio:
    """
    Portfolio management for FRED
    
    Features:
    - Position tracking with P&L
    - Target allocation management
    - Automatic rebalance signals
    - Risk exposure monitoring
    """
    
    def __init__(self, initial_capital: Decimal = Decimal("1000")):
        self.initial_capital = initial_capital
        self.positions: Dict[str, Position] = {}
        self.allocations: Dict[str, Allocation] = {}
        self.cash: Decimal = initial_capital
        self.history: List[Dict] = []
        
    def add_position(self, position: Position):
        """Add or update position"""
        if position.symbol in self.positions:
            # Update existing
            existing = self.positions[position.symbol]
            total_qty = existing.quantity + position.quantity
            total_cost = (existing.quantity * existing.avg_cost) + (position.quantity * position.avg_cost)
            existing.quantity = total_qty
            existing.avg_cost = total_cost / total_qty if total_qty > 0 else Decimal("0")
        else:
            self.positions[position.symbol] = position
    
    def update_price(self, symbol: str, price: Decimal):
        """Update current price for position"""
        if symbol in self.positions:
            self.positions[symbol].current_price = price
    
    def update_prices(self, prices: Dict[str, Decimal]):
        """Batch update prices"""
        for symbol, price in prices.items():
            self.update_price(symbol, price)
    
    def set_allocation(self, allocation: Allocation):
        """Set target allocation for asset"""
        self.allocations[allocation.symbol] = allocation
    
    @property
    def total_value(self) -> Decimal:
        """Total portfolio value including cash"""
        position_value = sum(p.value for p in self.positions.values())
        return position_value + self.cash
    
    @property
    def total_pnl(self) -> Decimal:
        """Total unrealized P&L"""
        return sum(p.pnl for p in self.positions.values())
    
    @property
    def total_pnl_pct(self) -> Decimal:
        """Total P&L percentage"""
        if self.initial_capital == 0:
            return Decimal("0")
        return (self.total_pnl / self.initial_capital) * 100
    
    def get_weights(self) -> Dict[str, Decimal]:
        """Get current portfolio weights"""
        total = self.total_value
        if total == 0:
            return {}
        
        weights = {}
        for symbol, pos in self.positions.items():
            weights[symbol] = (pos.value / total) * 100
        weights["CASH"] = (self.cash / total) * 100
        
        return weights
    
    def get_drift(self) -> Dict[str, Decimal]:
        """Calculate drift from target allocations"""
        weights = self.get_weights()
        drift = {}
        
        for symbol, alloc in self.allocations.items():
            current = weights.get(symbol, Decimal("0"))
            drift[symbol] = current - alloc.target_pct
        
        return drift
    
    def needs_rebalance(self) -> bool:
        """Check if portfolio needs rebalancing"""
        drift = self.get_drift()
        
        for symbol, d in drift.items():
            alloc = self.allocations.get(symbol)
            if alloc and abs(d) > alloc.rebalance_threshold:
                return True
        
        return False
    
    def get_rebalance_orders(self) -> List[RebalanceOrder]:
        """Generate orders to rebalance portfolio"""
        orders = []
        total = self.total_value
        weights = self.get_weights()
        
        for symbol, alloc in self.allocations.items():
            current_weight = weights.get(symbol, Decimal("0"))
            target_weight = alloc.target_pct
            drift = current_weight - target_weight
            
            if abs(drift) < alloc.rebalance_threshold:
                continue
            
            current_value = (current_weight / 100) * total
            target_value = (target_weight / 100) * total
            value_diff = target_value - current_value
            
            if value_diff > 0:
                # Need to buy
                orders.append(RebalanceOrder(
                    symbol=symbol,
                    side="BUY",
                    quantity=self._value_to_quantity(symbol, value_diff),
                    target_value=target_value,
                    current_value=current_value,
                    reason=f"Underweight by {abs(drift):.1f}%"
                ))
            else:
                # Need to sell
                orders.append(RebalanceOrder(
                    symbol=symbol,
                    side="SELL",
                    quantity=self._value_to_quantity(symbol, abs(value_diff)),
                    target_value=target_value,
                    current_value=current_value,
                    reason=f"Overweight by {abs(drift):.1f}%"
                ))
        
        return orders
    
    def _value_to_quantity(self, symbol: str, value: Decimal) -> Decimal:
        """Convert value to quantity using current price"""
        if symbol not in self.positions:
            return Decimal("0")
        price = self.positions[symbol].current_price
        if price == 0:
            return Decimal("0")
        return (value / price).quantize(Decimal("0.0001"), rounding=ROUND_DOWN)
    
    def get_exposure(self) -> Dict[str, Any]:
        """Get risk exposure breakdown"""
        weights = self.get_weights()
        total = self.total_value
        
        # Concentration risk (top position %)
        sorted_weights = sorted(
            [(s, w) for s, w in weights.items() if s != "CASH"],
            key=lambda x: x[1],
            reverse=True
        )
        
        top_position = sorted_weights[0] if sorted_weights else ("N/A", Decimal("0"))
        
        return {
            "total_value": float(total),
            "cash_pct": float(weights.get("CASH", Decimal("0"))),
            "invested_pct": 100 - float(weights.get("CASH", Decimal("0"))),
            "positions_count": len(self.positions),
            "top_position": top_position[0],
            "top_position_pct": float(top_position[1]),
            "concentration_risk": "HIGH" if float(top_position[1]) > 30 else "MEDIUM" if float(top_position[1]) > 20 else "LOW"
        }
    
    def get_summary(self) -> str:
        """Get formatted portfolio summary"""
        weights = self.get_weights()
        
        lines = [
            "╔══════════════════════════════════════════════╗",
            "║          FRED-SOL Portfolio Summary          ║",
            "╠══════════════════════════════════════════════╣",
            f"║ Total Value:    ${float(self.total_value):>12,.2f}            ║",
            f"║ Total P&L:      ${float(self.total_pnl):>+12,.2f}            ║",
            f"║ P&L %:          {float(self.total_pnl_pct):>+12.2f}%           ║",
            "╠══════════════════════════════════════════════╣",
            "║ Position        │ Value      │ Weight │ P&L  ║",
            "╠═══════════════════╪════════════╪════════╪══════╣",
        ]
        
        for symbol, pos in sorted(self.positions.items()):
            weight = weights.get(symbol, Decimal("0"))
            lines.append(
                f"║ {symbol:<15} │ ${float(pos.value):>8,.0f} │ {float(weight):>5.1f}% │ {float(pos.pnl_pct):>+.0f}% ║"
            )
        
        # Cash
        cash_weight = weights.get("CASH", Decimal("0"))
        lines.append(f"║ {'CASH':<15} │ ${float(self.cash):>8,.0f} │ {float(cash_weight):>5.1f}% │    - ║")
        
        lines.extend([
            "╠══════════════════════════════════════════════╣",
            f"║ Needs Rebalance: {'YES ⚠️' if self.needs_rebalance() else 'NO ✅':>22}   ║",
            "╚══════════════════════════════════════════════╝",
        ])
        
        return "\n".join(lines)
    
    def save(self, filepath: str):
        """Save portfolio state"""
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "initial_capital": str(self.initial_capital),
            "cash": str(self.cash),
            "positions": {
                s: {
                    "symbol": p.symbol,
                    "mint": p.mint,
                    "quantity": str(p.quantity),
                    "avg_cost": str(p.avg_cost),
                    "current_price": str(p.current_price)
                }
                for s, p in self.positions.items()
            },
            "allocations": {
                s: {
                    "symbol": a.symbol,
                    "target_pct": str(a.target_pct),
                    "min_pct": str(a.min_pct),
                    "max_pct": str(a.max_pct),
                    "rebalance_threshold": str(a.rebalance_threshold)
                }
                for s, a in self.allocations.items()
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    @classmethod
    def load(cls, filepath: str) -> "Portfolio":
        """Load portfolio from file"""
        with open(filepath) as f:
            data = json.load(f)
        
        portfolio = cls(Decimal(data["initial_capital"]))
        portfolio.cash = Decimal(data["cash"])
        
        for pos_data in data.get("positions", {}).values():
            portfolio.positions[pos_data["symbol"]] = Position(
                symbol=pos_data["symbol"],
                mint=pos_data["mint"],
                quantity=Decimal(pos_data["quantity"]),
                avg_cost=Decimal(pos_data["avg_cost"]),
                current_price=Decimal(pos_data["current_price"])
            )
        
        for alloc_data in data.get("allocations", {}).values():
            portfolio.allocations[alloc_data["symbol"]] = Allocation(
                symbol=alloc_data["symbol"],
                target_pct=Decimal(alloc_data["target_pct"]),
                min_pct=Decimal(alloc_data["min_pct"]),
                max_pct=Decimal(alloc_data["max_pct"]),
                rebalance_threshold=Decimal(alloc_data["rebalance_threshold"])
            )
        
        return portfolio


if __name__ == "__main__":
    # Demo
    portfolio = Portfolio(Decimal("10000"))
    portfolio.cash = Decimal("2000")
    
    # Add positions
    portfolio.add_position(Position(
        symbol="SOL",
        mint="So11111111111111111111111111111111111111112",
        quantity=Decimal("50"),
        avg_cost=Decimal("95"),
        current_price=Decimal("98.50")
    ))
    
    portfolio.add_position(Position(
        symbol="USDC",
        mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        quantity=Decimal("3000"),
        avg_cost=Decimal("1"),
        current_price=Decimal("1")
    ))
    
    # Set allocations
    portfolio.set_allocation(Allocation("SOL", Decimal("50")))
    portfolio.set_allocation(Allocation("USDC", Decimal("30")))
    
    print(portfolio.get_summary())
    
    print("\nExposure:")
    for k, v in portfolio.get_exposure().items():
        print(f"  {k}: {v}")
    
    if portfolio.needs_rebalance():
        print("\nRebalance Orders:")
        for order in portfolio.get_rebalance_orders():
            print(f"  {order.side} {order.quantity} {order.symbol} ({order.reason})")
