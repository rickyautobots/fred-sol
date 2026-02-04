#!/usr/bin/env python3
"""FRED Backtesting Engine"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List


@dataclass
class PricePoint:
    timestamp: str
    price: float


@dataclass
class Trade:
    timestamp: str
    side: str
    price: float
    size: float
    pnl: float = 0.0


class BacktestEngine:
    """Backtest trading strategy against historical data."""
    
    def __init__(self, initial_capital: float = 1000.0):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.position = 0.0
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = []
        
    def kelly_size(self, prob: float, odds: float = 2.0) -> float:
        """Half-Kelly position sizing."""
        if odds <= 1 or prob <= 0 or prob >= 1:
            return 0
        b = odds - 1
        f = (b * prob - (1 - prob)) / b
        return max(0, min(f * 0.5, 0.25))  # Max 25%
    
    def estimate_probability(self, prices: List[float], lookback: int = 10) -> float:
        """Simple momentum-based probability estimate."""
        if len(prices) < lookback:
            return 0.5
        
        recent = prices[-lookback:]
        up_moves = sum(1 for i in range(1, len(recent)) if recent[i] > recent[i-1])
        momentum = up_moves / (lookback - 1)
        
        # Mean reversion adjustment
        if momentum > 0.7:
            return 0.45  # Expect pullback
        elif momentum < 0.3:
            return 0.55  # Expect bounce
        else:
            return 0.5 + (momentum - 0.5) * 0.1
    
    def run(self, prices: List[PricePoint]) -> dict:
        """Run backtest on price data."""
        price_list = [p.price for p in prices]
        
        for i, point in enumerate(prices):
            if i < 10:  # Need history
                self.equity_curve.append(self.capital)
                continue
            
            prob = self.estimate_probability(price_list[:i+1])
            size_pct = self.kelly_size(prob)
            
            # Trading logic
            if prob > 0.52 and self.position == 0 and size_pct > 0.02:
                # Buy signal
                size_usd = self.capital * size_pct
                self.position = size_usd / point.price
                self.capital -= size_usd
                self.trades.append(Trade(
                    timestamp=point.timestamp,
                    side="BUY",
                    price=point.price,
                    size=self.position
                ))
            
            elif prob < 0.48 and self.position > 0:
                # Sell signal
                sell_value = self.position * point.price
                entry_price = self.trades[-1].price if self.trades else point.price
                pnl = (point.price - entry_price) * self.position
                self.capital += sell_value
                self.trades.append(Trade(
                    timestamp=point.timestamp,
                    side="SELL",
                    price=point.price,
                    size=self.position,
                    pnl=pnl
                ))
                self.position = 0
            
            # Track equity
            equity = self.capital + (self.position * point.price)
            self.equity_curve.append(equity)
        
        # Close any open position
        if self.position > 0 and prices:
            final_price = prices[-1].price
            self.capital += self.position * final_price
            self.position = 0
        
        return self.calculate_metrics()
    
    def calculate_metrics(self) -> dict:
        """Calculate performance metrics."""
        if not self.equity_curve:
            return {}
        
        final_equity = self.equity_curve[-1]
        total_return = (final_equity - self.initial_capital) / self.initial_capital
        
        # Max drawdown
        peak = self.equity_curve[0]
        max_dd = 0
        for eq in self.equity_curve:
            peak = max(peak, eq)
            dd = (peak - eq) / peak
            max_dd = max(max_dd, dd)
        
        # Win rate
        pnls = [t.pnl for t in self.trades if t.side == "SELL"]
        wins = sum(1 for p in pnls if p > 0)
        win_rate = wins / len(pnls) if pnls else 0
        
        # Sharpe (simplified)
        if len(self.equity_curve) > 1:
            returns = [(self.equity_curve[i] - self.equity_curve[i-1]) / self.equity_curve[i-1] 
                      for i in range(1, len(self.equity_curve))]
            avg_ret = sum(returns) / len(returns) if returns else 0
            std_ret = (sum((r - avg_ret)**2 for r in returns) / len(returns))**0.5 if returns else 1
            sharpe = (avg_ret / std_ret) * (252**0.5) if std_ret > 0 else 0
        else:
            sharpe = 0
        
        return {
            "initial_capital": self.initial_capital,
            "final_equity": round(final_equity, 2),
            "total_return": round(total_return * 100, 2),
            "max_drawdown": round(max_dd * 100, 2),
            "sharpe_ratio": round(sharpe, 2),
            "total_trades": len(self.trades),
            "win_rate": round(win_rate * 100, 2),
        }


def load_sample_data() -> List[PricePoint]:
    """Generate sample price data."""
    import random
    
    prices = []
    price = 100.0
    base_time = datetime(2024, 1, 1)
    
    for i in range(365):  # 1 year daily
        # Random walk with slight upward drift
        change = random.gauss(0.0002, 0.02)
        price *= (1 + change)
        prices.append(PricePoint(
            timestamp=(base_time.replace(day=1) if i == 0 else base_time).isoformat(),
            price=round(price, 4)
        ))
        base_time = base_time.replace(day=min(28, base_time.day + 1))
    
    return prices


def main():
    """Run backtest and display results."""
    print("📊 FRED Backtesting Engine")
    print("=" * 40)
    
    # Load or generate data
    data_path = Path("data/sample_prices.json")
    if data_path.exists():
        with open(data_path) as f:
            raw = json.load(f)
            prices = [PricePoint(**p) for p in raw]
    else:
        print("Generating sample data...")
        prices = load_sample_data()
        # Save for reproducibility
        data_path.parent.mkdir(exist_ok=True)
        with open(data_path, "w") as f:
            json.dump([{"timestamp": p.timestamp, "price": p.price} for p in prices], f, indent=2)
    
    print(f"Loaded {len(prices)} price points")
    
    # Run backtest
    engine = BacktestEngine(initial_capital=1000.0)
    metrics = engine.run(prices)
    
    # Display results
    print("\n📈 Results:")
    print("-" * 40)
    print(f"Initial Capital: ${metrics['initial_capital']:.2f}")
    print(f"Final Equity:    ${metrics['final_equity']:.2f}")
    print(f"Total Return:    {metrics['total_return']}%")
    print(f"Max Drawdown:    {metrics['max_drawdown']}%")
    print(f"Sharpe Ratio:    {metrics['sharpe_ratio']}")
    print(f"Total Trades:    {metrics['total_trades']}")
    print(f"Win Rate:        {metrics['win_rate']}%")
    
    # Save results
    results = {
        "metrics": metrics,
        "trades": [{"timestamp": t.timestamp, "side": t.side, "price": t.price, "size": t.size, "pnl": t.pnl} 
                  for t in engine.trades]
    }
    with open("backtest_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\n💾 Results saved to backtest_results.json")


if __name__ == "__main__":
    main()
