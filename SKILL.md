---
name: fred-sol
version: 0.1.0
description: Autonomous Solana trading agent. Scans markets, estimates probabilities, sizes positions with Kelly criterion, executes via Jupiter.
---

# FRED-SOL

Autonomous trading agent for Solana.

## Commands

```bash
# Single scan
./run.sh

# Continuous loop (60s interval)
./run.sh loop

# Custom interval (30s)
./run.sh loop 30

# Individual components
./run.sh scan    # Market scanner only
./run.sh wallet  # Check wallet balance
./run.sh swap    # Test Jupiter swap quote
```

## Configuration

Set wallet path:
```bash
export SOLANA_WALLET=~/.config/solana/ricky-wallet.json
```

Set Anthropic key for LLM estimation:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

## Architecture

1. **Scanner** — Fetches markets from Jupiter, Birdeye
2. **Estimator** — LLM-based probability estimation
3. **Sizer** — Kelly criterion position sizing
4. **Executor** — Jupiter swap execution
5. **Main** — Orchestrates the trading loop

## Files

| File | Purpose |
|------|---------|
| scanner.py | Market discovery |
| wallet.py | Keypair management |
| executor.py | Jupiter swaps |
| agent.py | LLM estimation |
| main.py | Trading loop |
| run.sh | CLI entry point |

## Markets Supported

- Jupiter (spot swaps)
- Birdeye (token prices)
- Drift (perps) — coming soon

## Safety

- Half-Kelly sizing (conservative)
- Max 10% position size
- 5% minimum edge requirement
- Slippage protection (0.5% default)
