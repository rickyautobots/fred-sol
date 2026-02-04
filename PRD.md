# PRD: FRED Backtesting Engine

## Objective
Add backtesting capability to validate trading strategy against historical data.

## Requirements
- [ ] Create backtest.py with BacktestEngine class
- [ ] Load historical price data (mock or from file)
- [ ] Simulate trades using existing agent logic
- [ ] Calculate metrics: total return, Sharpe ratio, max drawdown, win rate
- [ ] Output results as JSON and terminal summary
- [ ] Add `--backtest` flag to main.py

## Validation Checklist
- [ ] `python main.py --backtest` runs without errors
- [ ] Outputs performance metrics
- [ ] Uses same position sizing logic as live trading

## Files to Create/Modify
- `backtest.py` — backtesting engine
- `main.py` — add --backtest flag
- `data/sample_prices.json` — sample historical data

## Out of Scope
- Live data fetching for backtest
- Complex slippage modeling
