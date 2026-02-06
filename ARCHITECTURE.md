# FRED-SOL Architecture

> Self-funding AI trading agent for Solana

## Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    FRED-SOL System                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │  Scanner │───▶│ Estimator│───▶│   Risk   │              │
│  │ (markets)│    │  (LLM)   │    │ Manager  │              │
│  └──────────┘    └──────────┘    └────┬─────┘              │
│                                       │                     │
│                                       ▼                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │  Wallet  │◀───│ Executor │◀───│  Agent   │              │
│  │ (Solana) │    │ (trades) │    │ (brain)  │              │
│  └──────────┘    └──────────┘    └──────────┘              │
│                                                             │
│  ┌─────────────────────────────────────────────┐           │
│  │              Jupiter Aggregator              │           │
│  │         (best-price swap routing)            │           │
│  └─────────────────────────────────────────────┘           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Modules

### Core Trading
| Module | Lines | Purpose |
|--------|-------|---------|
| `agent.py` | 247 | Main trading brain |
| `scanner.py` | 116 | Market discovery (Jupiter, Birdeye) |
| `estimator.py` | 285 | LLM probability estimation |
| `risk.py` | 292 | Position sizing (optimal-f, R-multiple) |
| `executor.py` | 310 | Trade execution |
| `wallet.py` | 134 | Solana wallet operations |

### Solana Integration
| Module | Lines | Purpose |
|--------|-------|---------|
| `solana_integration.py` | 353 | Native RPC + Jupiter swaps |
| `cli.py` | 266 | Unified command interface |

### Analysis & Monitoring
| Module | Lines | Purpose |
|--------|-------|---------|
| `backtest.py` | 275 | Historical simulation |
| `dashboard.py` | 264 | Streamlit web UI |
| `live_monitor.py` | 280 | Real-time terminal UI |
| `report_generator.py` | 184 | Performance reports |
| `alerts.py` | 244 | Notification system |

### Memory & Persistence
| Module | Lines | Purpose |
|--------|-------|---------|
| `memory_evermind.py` | 256 | EverMind long-term memory |
| `logger.py` | 89 | Structured logging |

### API & Demo
| Module | Lines | Purpose |
|--------|-------|---------|
| `api.py` | 142 | REST API endpoints |
| `streamlit_app.py` | 359 | Demo application |
| `demo.py` | 156 | Quick demo script |
| `main.py` | 98 | Entry point |

## Key Features

### 1. Self-Funding Loop
```
Trade Volume → LP Fees → Fund Inference → Better Trades
```

The agent generates revenue through trading, which funds its own LLM inference costs via x402 micropayments.

### 2. Optimal-f Position Sizing
Based on Van K. Tharp's R-multiple framework:
- Calculate edge (estimate - market)
- Compute reward:risk ratio
- Apply Kelly criterion with caps
- Never risk >5% on single trade

### 3. Multi-Source Market Data
- Jupiter: Price feeds for major tokens
- Birdeye: Trending tokens and volume
- (Future) Polymarket: Prediction markets

### 4. Risk Management
- Position limits per trade
- Daily drawdown limits
- Correlation-aware portfolio
- Automatic stop-losses

## CLI Usage

```bash
# Check portfolio
python cli.py portfolio

# Scan markets
python cli.py scan --limit 20

# Get swap quote
python cli.py quote SOL USDC 1.0

# Run live monitor
python cli.py monitor --duration 60

# Run agent (dry run)
python cli.py run --dry-run --iterations 10
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=. --cov-report=html
```

## Deployment

### Requirements
- Python 3.10+
- Solana wallet with SOL for gas
- (Optional) RPC endpoint for production

### Environment
```bash
export SOLANA_WALLET="your-wallet-address"
export SOLANA_RPC="https://api.mainnet-beta.solana.com"
export ANTHROPIC_API_KEY="sk-..."  # For LLM inference
```

## Hackathon Submission

**Solana AI Agent Hackathon 2026**
- Prize Pool: $100,000
- Project ID: 294
- Agent Registration: #603

### Judges: What to Look For
1. **Self-funding mechanism** - Agent pays for its own inference
2. **Real Solana integration** - Native RPC, Jupiter swaps
3. **Risk management** - Optimal-f position sizing
4. **Test coverage** - 80+ tests
5. **Production-ready** - CLI, API, monitoring

---

*Built by Ricky 🎭 | github.com/rickyautobots/fred-sol*
