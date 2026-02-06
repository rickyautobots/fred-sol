# FRED-SOL Module Index

> 9,000+ lines of production-ready trading infrastructure

## Core Trading

| Module | Lines | Description |
|--------|-------|-------------|
| `agent.py` | 247 | Main trading brain with decision loop |
| `scanner.py` | 116 | Market discovery via Jupiter/Birdeye |
| `estimator.py` | 285 | LLM probability estimation |
| `executor.py` | 310 | Trade execution engine |
| `risk.py` | 292 | Position sizing and risk management |
| `strategy.py` | 422 | Pluggable strategy framework |

## Solana Integration

| Module | Lines | Description |
|--------|-------|-------------|
| `solana_integration.py` | 353 | Native Solana RPC + Jupiter swaps |
| `wallet.py` | 134 | Wallet operations and signing |

## Portfolio & Analytics

| Module | Lines | Description |
|--------|-------|-------------|
| `portfolio.py` | 367 | Position tracking, rebalancing |
| `metrics.py` | 352 | Performance analytics, R-multiples |
| `backtest.py` | 275 | Historical simulation |

## Infrastructure

| Module | Lines | Description |
|--------|-------|-------------|
| `config.py` | 308 | Environment-based configuration |
| `health.py` | 321 | Health monitoring system |
| `scheduler.py` | 368 | Async task scheduling |
| `webhook_alerts.py` | 359 | Discord/Telegram/Slack notifications |
| `logger.py` | 89 | Structured logging |
| `utils.py` | 399 | Common utility functions |

## User Interface

| Module | Lines | Description |
|--------|-------|-------------|
| `cli.py` | 266 | Command-line interface |
| `dashboard.py` | 264 | Streamlit web dashboard |
| `streamlit_app.py` | 359 | Interactive demo application |
| `live_monitor.py` | 280 | Real-time terminal UI |
| `report_generator.py` | 184 | Performance reports |

## API & Integration

| Module | Lines | Description |
|--------|-------|-------------|
| `api.py` | 142 | REST API endpoints |
| `alerts.py` | 244 | Alert system |
| `memory_evermind.py` | 256 | Long-term memory integration |

## Entry Points

| Module | Lines | Description |
|--------|-------|-------------|
| `main.py` | 98 | Application entry point |
| `demo.py` | 156 | Quick demo script |

## Tests

| File | Lines | Coverage |
|------|-------|----------|
| `tests/test_*.py` | 600+ | Core trading logic |
| `tests/test_solana_integration.py` | 208 | Solana RPC |

---

## Quick Start

```bash
# CLI usage
python cli.py portfolio          # Show balances
python cli.py scan               # Find opportunities
python cli.py quote SOL USDC 1.0 # Get swap quote
python cli.py run --dry-run      # Start agent

# Streamlit demo
streamlit run streamlit_app.py
```

## Stats

- **Total Python**: 9,000+ lines
- **Total Commits**: 46
- **Test Coverage**: 80+ tests
- **Dependencies**: Minimal (httpx, rich, streamlit optional)

---

*Built by Ricky 🎭 for Solana AI Agent Hackathon 2026*
