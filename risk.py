#!/usr/bin/env python3
"""
FRED Risk Management

Position limits, drawdown protection, and exposure tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json


@dataclass
class Position:
    symbol: str
    size: float
    entry_price: float
    entry_time: datetime
    current_price: float = 0.0
    
    @property
    def pnl(self) -> float:
        if self.entry_price == 0:
            return 0
        return (self.current_price - self.entry_price) / self.entry_price
    
    @property
    def pnl_usd(self) -> float:
        return self.size * (self.current_price - self.entry_price)


@dataclass
class RiskConfig:
    max_position_pct: float = 0.10       # Max 10% per position
    max_total_exposure: float = 0.50     # Max 50% total exposure
    max_daily_loss_pct: float = 0.05     # Stop trading at 5% daily loss
    max_drawdown_pct: float = 0.15       # Hard stop at 15% drawdown
    min_time_between_trades: int = 60    # Seconds between trades
    max_trades_per_hour: int = 10        # Rate limit


@dataclass
class TradingLimits:
    """Trading rate and timing limits."""
    max_trades_per_hour: int = 10
    min_trade_interval_sec: int = 60
    cooldown_after_loss_sec: int = 300


class RiskManager:
    """Manages trading risk and position limits."""
    
    def __init__(self, config: Optional[RiskConfig] = None, initial_capital: float = 1000.0):
        self.config = config or RiskConfig()
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[dict] = []
        self.daily_pnl: float = 0.0
        self.peak_capital: float = initial_capital
        self.last_trade_time: Optional[datetime] = None
        self.trades_this_hour: int = 0
        self.hour_start: datetime = datetime.now()
    
    # Compatibility properties for tests
    @property
    def capital(self) -> float:
        """Alias for current_capital (test compatibility)."""
        return self.current_capital
    
    @capital.setter
    def capital(self, value: float):
        self.current_capital = value
    
    @property
    def high_water_mark(self) -> float:
        """Alias for peak_capital (test compatibility)."""
        return self.peak_capital
    
    @high_water_mark.setter
    def high_water_mark(self, value: float):
        self.peak_capital = value
    
    def max_position_size(self) -> float:
        """Get max position size in USD."""
        return self.current_capital * self.config.max_position_pct
    
    def check_trade_allowed(self, size_usd: float, symbol: str) -> tuple[bool, str]:
        """Check if trade is allowed (test compatibility wrapper for can_trade)."""
        return self.can_trade(symbol, size_usd)
    
    def record_trade_result(self, symbol: str, pnl: float):
        """Record a trade result (simplified for tests)."""
        self.daily_pnl += pnl
        self.current_capital += pnl
        self.trade_history.append({
            "time": datetime.now().isoformat(),
            "action": "RESULT",
            "symbol": symbol,
            "pnl": pnl
        })
    
    def update_high_water_mark(self):
        """Update high water mark to current capital if higher."""
        self.peak_capital = max(self.peak_capital, self.current_capital)
    
    def add_position(self, symbol: str, size_usd: float):
        """Add a position (simplified for tests)."""
        self.positions[symbol] = Position(
            symbol=symbol,
            size=size_usd,
            entry_price=1.0,  # Placeholder
            entry_time=datetime.now(),
            current_price=1.0
        )
    
    def total_exposure(self) -> float:
        """Current total exposure in USD (method version for tests)."""
        return sum(p.size for p in self.positions.values())
    
    def check_drawdown(self) -> tuple[bool, str]:
        """Check if drawdown is within limits."""
        if self.current_drawdown > self.config.max_drawdown_pct:
            return False, f"Max drawdown exceeded: {self.current_drawdown:.1%}"
        return True, "OK"
    
    @property
    def _total_exposure_pct(self) -> float:
        """Current total exposure as fraction of capital."""
        total = sum(p.size for p in self.positions.values())
        return total / self.current_capital if self.current_capital > 0 else 0
    
    @property
    def current_drawdown(self) -> float:
        """Current drawdown from peak."""
        if self.peak_capital == 0:
            return 0
        return (self.peak_capital - self.current_capital) / self.peak_capital
    
    def can_trade(self, symbol: str, size_usd: float) -> tuple[bool, str]:
        """Check if a trade is allowed under risk rules."""
        
        # Rate limiting
        now = datetime.now()
        
        if now - self.hour_start > timedelta(hours=1):
            self.trades_this_hour = 0
            self.hour_start = now
        
        if self.trades_this_hour >= self.config.max_trades_per_hour:
            return False, f"Rate limit: {self.config.max_trades_per_hour} trades/hour"
        
        if self.last_trade_time:
            elapsed = (now - self.last_trade_time).total_seconds()
            if elapsed < self.config.min_time_between_trades:
                return False, f"Too fast: wait {self.config.min_time_between_trades - elapsed:.0f}s"
        
        # Position size limit
        position_pct = size_usd / self.current_capital
        if position_pct > self.config.max_position_pct:
            return False, f"Position too large: {position_pct:.1%} > {self.config.max_position_pct:.1%}"
        
        # Total exposure limit
        new_exposure = self._total_exposure_pct + position_pct
        if new_exposure > self.config.max_total_exposure:
            return False, f"Exposure limit: {new_exposure:.1%} > {self.config.max_total_exposure:.1%}"
        
        # Daily loss limit
        if self.daily_pnl < -self.config.max_daily_loss_pct * self.initial_capital:
            return False, f"Daily loss limit reached: {self.daily_pnl:.2f}"
        
        # Drawdown limit
        if self.current_drawdown > self.config.max_drawdown_pct:
            return False, f"Max drawdown: {self.current_drawdown:.1%} > {self.config.max_drawdown_pct:.1%}"
        
        return True, "OK"
    
    def open_position(self, symbol: str, size_usd: float, price: float) -> bool:
        """Record a new position."""
        allowed, reason = self.can_trade(symbol, size_usd)
        if not allowed:
            print(f"❌ Trade blocked: {reason}")
            return False
        
        self.positions[symbol] = Position(
            symbol=symbol,
            size=size_usd,
            entry_price=price,
            entry_time=datetime.now(),
            current_price=price
        )
        
        self.last_trade_time = datetime.now()
        self.trades_this_hour += 1
        
        self.trade_history.append({
            "time": datetime.now().isoformat(),
            "action": "OPEN",
            "symbol": symbol,
            "size": size_usd,
            "price": price
        })
        
        return True
    
    def close_position(self, symbol: str, price: float) -> Optional[float]:
        """Close a position and return PnL."""
        if symbol not in self.positions:
            return None
        
        pos = self.positions[symbol]
        pos.current_price = price
        pnl = pos.pnl_usd
        
        self.current_capital += pnl
        self.daily_pnl += pnl
        self.peak_capital = max(self.peak_capital, self.current_capital)
        
        self.trade_history.append({
            "time": datetime.now().isoformat(),
            "action": "CLOSE",
            "symbol": symbol,
            "size": pos.size,
            "price": price,
            "pnl": pnl
        })
        
        del self.positions[symbol]
        return pnl
    
    def update_prices(self, prices: Dict[str, float]):
        """Update current prices for all positions."""
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol].current_price = price
    
    def get_status(self) -> dict:
        """Get current risk status."""
        return {
            "capital": self.current_capital,
            "initial": self.initial_capital,
            "pnl_total": self.current_capital - self.initial_capital,
            "pnl_pct": (self.current_capital - self.initial_capital) / self.initial_capital,
            "daily_pnl": self.daily_pnl,
            "exposure": self._total_exposure_pct,
            "drawdown": self.current_drawdown,
            "positions": len(self.positions),
            "trades_today": len([t for t in self.trade_history 
                               if t["time"][:10] == datetime.now().isoformat()[:10]])
        }
    
    def save_state(self, path: str = "risk_state.json"):
        """Save state to file."""
        state = {
            "capital": self.current_capital,
            "peak": self.peak_capital,
            "daily_pnl": self.daily_pnl,
            "positions": {k: vars(v) for k, v in self.positions.items()},
            "history": self.trade_history[-100:]  # Last 100 trades
        }
        with open(path, "w") as f:
            json.dump(state, f, indent=2, default=str)
    
    def load_state(self, path: str = "risk_state.json"):
        """Load state from file."""
        try:
            with open(path) as f:
                state = json.load(f)
            self.current_capital = state["capital"]
            self.peak_capital = state["peak"]
            self.daily_pnl = state["daily_pnl"]
            self.trade_history = state.get("history", [])
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    # Test
    rm = RiskManager(initial_capital=1000)
    
    # Try to open position
    allowed, reason = rm.can_trade("SOL/USDC", 100)
    print(f"Can trade: {allowed} - {reason}")
    
    rm.open_position("SOL/USDC", 100, 96.42)
    print(f"Status: {rm.get_status()}")
    
    # Close with profit
    pnl = rm.close_position("SOL/USDC", 98.00)
    print(f"Closed with PnL: ${pnl:.2f}")
    print(f"Final status: {rm.get_status()}")
