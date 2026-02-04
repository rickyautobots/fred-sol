# FRED Demo Recording Guide

**Total time needed: 5 minutes**

## Pre-Recording Setup (30 seconds)

```bash
cd ~/projects/solana-hackathon/fred-sol
pip install -r requirements.txt  # If not done
```

## Recording Script

### Scene 1: Intro (15 seconds)
**Show:** Terminal with FRED logo

```bash
python main.py --demo
```

**Narrate:** "FRED is an autonomous Solana trading agent that uses LLM probability estimation and Kelly criterion position sizing."

### Scene 2: Market Scanning (20 seconds)
**Show:** Demo scanning markets with progress bars

**Narrate:** "FRED scans markets via Jupiter and Birdeye, looking for trading opportunities."

### Scene 3: Probability Estimation (20 seconds)
**Show:** Analysis result panel with probability/confidence

**Narrate:** "Each opportunity is analyzed using Claude for probability estimation. FRED outputs both the probability AND its confidence level."

### Scene 4: Position Sizing (15 seconds)
**Show:** Kelly sizing calculation

**Narrate:** "Position sizes are calculated using the Kelly criterion - mathematically optimal bet sizing that maximizes long-term growth."

### Scene 5: Trade Execution (15 seconds)
**Show:** Trade confirmation panel

**Narrate:** "Trades execute via Jupiter aggregator for best prices."

### Scene 6: Dashboard (15 seconds)
**New terminal:**
```bash
python main.py --dashboard
```
**Open browser:** http://localhost:8080

**Narrate:** "FRED includes a real-time dashboard for monitoring."

### Scene 7: API (15 seconds)
**Show:** API docs or curl command

```bash
curl localhost:8000/estimate -X POST -H "Content-Type: application/json" \
  -d '{"symbol":"SOL/USDC","price":96.42,"volume_24h":500000}'
```

**Narrate:** "And a REST API so other agents can use FRED's estimation engine."

### Scene 8: Close (10 seconds)
**Show:** GitHub repo

**Narrate:** "FRED. Autonomous trading with mathematical precision. github.com/rickyautobots/fred-sol"

---

## Recording Tips
- Use a dark terminal theme
- Zoom to ~150% so text is readable
- Record at 1080p minimum
- Keep narration concise
- Total video: ~2 minutes

## After Recording
1. Upload to YouTube (unlisted)
2. Submit link on DoraHacks
3. Tag @coinbaseDev on X (if unsuspended)
