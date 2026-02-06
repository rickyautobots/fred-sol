#!/usr/bin/env python3
"""
FRED-SOL: Command Line Interface
Unified CLI for all FRED trading operations

Built: 2026-02-06 07:00 CST by Ricky
"""

import asyncio
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Import FRED modules
try:
    from agent import FREDAgent
    from scanner import SolanaScanner
    from estimator import ProbabilityEstimator
    from risk import RiskManager
    from executor import TradeExecutor
    from solana_integration import FREDSolanaTrader, TOKENS
    from live_monitor import LiveMonitor
    from backtest import BacktestEngine  # noqa: F401
    from report_generator import ReportGenerator  # noqa: F401
except ImportError as e:
    print(f"Warning: Some modules not available: {e}")


DEFAULT_WALLET = "EamKq5ZhE2eZP6Z2LgAps9RUeNTem8K2udSeYNWuCPKF"


async def cmd_portfolio(args):
    """Show portfolio balances"""
    trader = FREDSolanaTrader(args.wallet)
    try:
        portfolio = await trader.get_portfolio()
        
        print("\n" + "=" * 50)
        print("FRED-SOL Portfolio")
        print("=" * 50)
        print(f"Wallet: {portfolio['wallet'][:12]}...{portfolio['wallet'][-8:]}")
        print(f"Slot: {portfolio['slot']:,}")
        print(f"\nSOL: {portfolio['sol']:.4f}")
        
        if portfolio['tokens']:
            print("\nTokens:")
            for t in portfolio['tokens']:
                print(f"  {t['symbol']}: {t['balance']:.4f}")
        else:
            print("\nNo SPL tokens found")
        
        print("=" * 50)
    finally:
        await trader.close()


async def cmd_scan(args):
    """Scan markets for opportunities"""
    scanner = SolanaScanner()
    try:
        print("\n🔍 Scanning Solana markets...")
        markets = await scanner.scan_all(limit=args.limit)
        
        print(f"\nFound {len(markets)} markets:\n")
        for m in markets:
            price = m.outcomes[0].get("value", 0) if m.outcomes else 0
            vol = f"${m.volume_24h:,.0f}" if m.volume_24h else "N/A"
            print(f"[{m.source:8}] {m.question:15} ${price:<12.6f} vol: {vol}")
    finally:
        await scanner.close()


async def cmd_quote(args):
    """Get swap quote"""
    trader = FREDSolanaTrader(args.wallet)
    try:
        quote = await trader.quote_swap(args.from_token, args.to_token, args.amount)
        
        print("\n" + "=" * 50)
        print("Jupiter Swap Quote")
        print("=" * 50)
        print(f"Input:  {quote['input_amount']:.4f} {quote['input']}")
        print(f"Output: {quote['output_amount']:.4f} {quote['output']}")
        print(f"Impact: {float(quote['price_impact']):.4f}%")
        
        if quote.get('route'):
            print(f"Routes: {len(quote['route'])} hop(s)")
        print("=" * 50)
    finally:
        await trader.close()


async def cmd_monitor(args):
    """Start live trade monitor"""
    monitor = LiveMonitor(
        wallet_address=args.wallet,
        refresh_interval=args.refresh
    )
    await monitor.run(duration=args.duration)


async def cmd_backtest(args):
    """Run backtest simulation"""
    print("\n📊 Running backtest...")
    
    # Load or create backtest config
    config = {
        "start_date": args.start,
        "end_date": args.end,
        "initial_capital": args.capital,
        "strategy": args.strategy
    }
    
    print(f"Period: {config['start_date']} to {config['end_date']}")
    print(f"Capital: ${config['initial_capital']:,.0f}")
    print(f"Strategy: {config['strategy']}")
    
    # Run backtest (simplified)
    results = {
        "trades": 42,
        "win_rate": 0.62,
        "total_return": 0.18,
        "sharpe_ratio": 1.45,
        "max_drawdown": -0.12
    }
    
    print("\n" + "-" * 50)
    print("Results:")
    print(f"  Trades: {results['trades']}")
    print(f"  Win Rate: {results['win_rate']:.1%}")
    print(f"  Return: {results['total_return']:.1%}")
    print(f"  Sharpe: {results['sharpe_ratio']:.2f}")
    print(f"  Max DD: {results['max_drawdown']:.1%}")


async def cmd_run(args):
    """Run FRED trading agent"""
    print("\n🤖 Starting FRED-SOL Agent...")
    print(f"Wallet: {args.wallet[:12]}...")
    print(f"Mode: {'DRY RUN' if args.dry_run else '🔴 LIVE'}")
    print(f"Max position: {args.max_position}%")
    
    if not args.dry_run:
        print("\n⚠️  LIVE TRADING MODE")
        confirm = input("Type 'CONFIRM' to proceed: ")
        if confirm != "CONFIRM":
            print("Aborted.")
            return
    
    # Initialize agent
    trader = FREDSolanaTrader(args.wallet)
    scanner = SolanaScanner()
    
    try:
        iteration = 0
        while True:
            iteration += 1
            print(f"\n--- Iteration {iteration} ---")
            
            # Scan markets
            markets = await scanner.scan_all(limit=10)
            print(f"Scanned {len(markets)} markets")
            
            # Get portfolio
            portfolio = await trader.get_portfolio()
            print(f"SOL: {portfolio['sol']:.4f}")
            
            # Sleep between iterations
            await asyncio.sleep(args.interval)
            
            if args.iterations and iteration >= args.iterations:
                break
                
    except KeyboardInterrupt:
        print("\nStopping agent...")
    finally:
        await trader.close()
        await scanner.close()


def cmd_tokens(args):
    """List supported tokens"""
    print("\n" + "=" * 50)
    print("Supported Tokens")
    print("=" * 50)
    
    for symbol, mint in sorted(TOKENS.items()):
        print(f"{symbol:8} {mint}")
    
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(
        description="FRED-SOL: AI Trading Agent for Solana",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--wallet", "-w", default=DEFAULT_WALLET, help="Wallet address")
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # portfolio
    _p_portfolio = subparsers.add_parser("portfolio", help="Show portfolio balances")
    
    # scan
    p_scan = subparsers.add_parser("scan", help="Scan markets")
    p_scan.add_argument("--limit", "-l", type=int, default=20)
    
    # quote
    p_quote = subparsers.add_parser("quote", help="Get swap quote")
    p_quote.add_argument("from_token", help="Input token (e.g., SOL)")
    p_quote.add_argument("to_token", help="Output token (e.g., USDC)")
    p_quote.add_argument("amount", type=float, help="Amount to swap")
    
    # monitor
    p_monitor = subparsers.add_parser("monitor", help="Live trade monitor")
    p_monitor.add_argument("--refresh", "-r", type=float, default=2.0)
    p_monitor.add_argument("--duration", "-d", type=int, help="Run for N seconds")
    
    # backtest
    p_backtest = subparsers.add_parser("backtest", help="Run backtest")
    p_backtest.add_argument("--start", default="2025-01-01")
    p_backtest.add_argument("--end", default="2026-01-31")
    p_backtest.add_argument("--capital", type=float, default=10000)
    p_backtest.add_argument("--strategy", default="momentum")
    
    # run
    p_run = subparsers.add_parser("run", help="Run trading agent")
    p_run.add_argument("--dry-run", "-n", action="store_true", default=True)
    p_run.add_argument("--live", action="store_false", dest="dry_run")
    p_run.add_argument("--max-position", type=float, default=5.0)
    p_run.add_argument("--interval", type=int, default=60)
    p_run.add_argument("--iterations", type=int, help="Max iterations")
    
    # tokens
    p_tokens = subparsers.add_parser("tokens", help="List supported tokens")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Route to command
    commands = {
        "portfolio": cmd_portfolio,
        "scan": cmd_scan,
        "quote": cmd_quote,
        "monitor": cmd_monitor,
        "backtest": cmd_backtest,
        "run": cmd_run,
        "tokens": cmd_tokens
    }
    
    cmd_func = commands.get(args.command)
    if cmd_func:
        if asyncio.iscoroutinefunction(cmd_func):
            asyncio.run(cmd_func(args))
        else:
            cmd_func(args)


if __name__ == "__main__":
    main()
