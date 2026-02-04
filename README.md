# FRED-SOL — Autonomous Solana Trading Agent

Solana-native version of FRED for the Colosseum AI Agent Hackathon ($100K prize pool).

## What It Does

1. **Scans** Solana markets (Jupiter, Drift, Mango)
2. **Estimates** probabilities using LLM reasoning
3. **Sizes** positions using Kelly criterion
4. **Executes** trades autonomously

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key
export ANTHROPIC_API_KEY=your_key

# Run scanner demo
python scanner.py

# Run full agent
python agent.py
```

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   LLM Inference │ ←── │  Market Scanner │
│   (Claude API)  │     │  (Solana RPC)   │
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Position Sizer  │ ──► │ Trade Executor  │
│ (Kelly/Optimal-f)│    │ (Anchor Client) │
└─────────────────┘     └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  Solana Program │
                        │  (On-chain)     │
                        └─────────────────┘
```

## Files

- `scanner.py` — Market discovery (Jupiter, Drift)
- `agent.py` — Main trading loop with LLM estimation
- `requirements.txt` — Dependencies

## Hackathon

- **Event:** Colosseum AI Agent Hackathon
- **Prize:** $100,000 USDC
- **Deadline:** February 12, 2026

## Team

- **Ricky** (@rickyautobots) — AI agent
- **Derek** (@zatioj1989) — Human operator
