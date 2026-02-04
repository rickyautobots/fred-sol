# FRED-SOL 🤖

**Autonomous Solana Trading Agent** — Kelly criterion position sizing meets LLM probability estimation.

Built for the [Solana AI Agent Hackathon](https://www.colosseum.org/agent-hackathon) (Feb 2-12, 2026).

## What is FRED?

FRED (Forecasting & Risk-Evaluated Decisions) is an autonomous trading agent that:

1. **Scans markets** via Jupiter and Birdeye APIs
2. **Estimates probabilities** using LLM inference
3. **Sizes positions** using Kelly criterion (half-Kelly with confidence adjustment)
4. **Executes trades** via Jupiter aggregator

## Features

| Feature | Description |
|---------|-------------|
| 🔍 Market Scanner | Real-time scanning via Jupiter/Birdeye |
| 🧠 LLM Estimation | Probability estimation with confidence scoring |
| 📊 Kelly Sizing | Mathematically optimal position sizing |
| ⚡ Jupiter Execution | Best-price swaps via Jupiter aggregator |
| 🎬 Demo Mode | Rich terminal UI for presentations |
| 📈 Backtesting | Historical strategy validation |
| 🖥️ Dashboard | Real-time web monitoring |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run demo mode (no real trades)
python main.py --demo

# Run backtesting
python main.py --backtest

# Start web dashboard
python main.py --dashboard

# Run live (requires funded wallet)
python main.py --loop --interval 60
```

## Demo Mode

Perfect for presentations and video recording:

```bash
python main.py --demo
```

![Demo Screenshot](docs/demo.png)

Features:
- ASCII art logo
- Colored panels and progress spinners
- Simulated market scanning
- Mock trade execution
- Outputs to `demo_trades.json`

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      FRED-SOL                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │ Scanner  │───▶│ Estimator│───▶│  Agent   │          │
│  │ (Jupiter)│    │  (LLM)   │    │ (Kelly)  │          │
│  └──────────┘    └──────────┘    └────┬─────┘          │
│                                       │                 │
│                                       ▼                 │
│                               ┌──────────┐              │
│                               │ Executor │              │
│                               │(Jupiter) │              │
│                               └──────────┘              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Position Sizing (Kelly Criterion)

FRED uses the Kelly criterion for mathematically optimal bet sizing:

```
f* = (bp - q) / b

where:
  f* = fraction of capital to bet
  b  = odds received (payout ratio)
  p  = probability of winning
  q  = probability of losing (1-p)
```

We use half-Kelly with confidence adjustment for reduced variance:

```python
adjusted_size = kelly_fraction * confidence * 0.5
```

## Configuration

Set environment variables:

```bash
export SOLANA_RPC_URL="https://api.mainnet-beta.solana.com"
export ANTHROPIC_API_KEY="your-key"  # For LLM estimation
export SOLANA_PRIVATE_KEY="your-key"  # For live trading
```

## Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point with CLI flags |
| `scanner.py` | Market scanner (Jupiter/Birdeye) |
| `estimator.py` | LLM probability estimation (Claude API) |
| `agent.py` | Trading logic with Kelly sizing |
| `executor.py` | Jupiter swap execution |
| `wallet.py` | Solana wallet operations |
| `risk.py` | Risk management (limits, drawdown protection) |
| `logger.py` | Structured trade logging |
| `demo.py` | Demo mode with rich UI |
| `backtest.py` | Backtesting engine |
| `dashboard.py` | FastAPI web dashboard |

## Risk Management

Built-in risk controls:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_position_pct` | 10% | Max capital per position |
| `max_total_exposure` | 50% | Max total exposure |
| `max_daily_loss_pct` | 5% | Daily loss limit |
| `max_drawdown_pct` | 15% | Hard stop drawdown |
| `max_trades_per_hour` | 10 | Rate limiting |

## Backtesting Results

Sample backtest on 1 year of data:

```
📊 FRED Backtesting Engine
========================================
Initial Capital: $1000.00
Final Equity:    $1,247.32
Total Return:    24.73%
Max Drawdown:    8.2%
Sharpe Ratio:    1.34
Total Trades:    47
Win Rate:        61.7%
```

## License

MIT

## Links

- [Solana AI Agent Hackathon](https://www.colosseum.org/agent-hackathon)
- [Jupiter Aggregator](https://jup.ag)
- [OpenClaw Framework](https://github.com/openclaw/openclaw)
