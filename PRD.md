# PRD: FRED Demo Mode

## Objective
Add a demo mode that simulates trading without real money, outputs compelling terminal UI for video recording.

## Requirements
- [ ] Add `--demo` flag to main.py
- [ ] Create mock wallet with fake balances
- [ ] Simulate trades with realistic delays (500ms-2s)
- [ ] Rich terminal output with colors (use `rich` library)
- [ ] Show: market scan → probability estimate → position sizing → trade execution
- [ ] Include ASCII art logo at startup
- [ ] Log all "trades" to demo_trades.json

## Validation Checklist
- [ ] `python main.py --demo` runs without errors
- [ ] Output is visually compelling (colors, progress bars)
- [ ] No real API calls made in demo mode
- [ ] demo_trades.json contains sample trades

## Files to Create/Modify
- `main.py` — add --demo flag and demo flow
- `demo.py` — demo mode implementation
- `requirements.txt` — add `rich` if not present

## Out of Scope
- Real trading
- Wallet connections
