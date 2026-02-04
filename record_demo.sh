#!/bin/bash
# FRED Demo Recording Script
# Just screen record this running!

echo "Starting FRED demo in 3 seconds..."
echo "Make sure screen recording is ON"
sleep 3

clear
echo "═══════════════════════════════════════════════════════════════"
echo "                    FRED-SOL Demo"
echo "         Autonomous Solana Trading Agent"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Features:"
echo "  • LLM probability estimation (Claude API)"
echo "  • Kelly criterion position sizing"
echo "  • Risk management & drawdown protection"
echo "  • Jupiter aggregator execution"
echo ""
sleep 5

echo "Starting demo mode..."
sleep 2

python3 main.py --demo

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Demo complete. FRED: github.com/rickyautobots/fred-sol"
echo "═══════════════════════════════════════════════════════════════"
sleep 3
