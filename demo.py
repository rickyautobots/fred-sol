#!/usr/bin/env python3
"""FRED Demo Mode - Simulated trading for video recording"""

import asyncio
import json
import random
from datetime import datetime
from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
except ImportError:
    print("Installing rich...")
    import subprocess
    subprocess.run(["pip", "install", "rich"], check=True)
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table

console = Console()

VERSION = "1.1.0"
BUILD = "2026.02.05"

LOGO = """
[bold cyan]
  ███████╗██████╗ ███████╗██████╗       [bold white]v{version}[/bold white]
  ██╔════╝██╔══██╗██╔════╝██╔══██╗
  █████╗  ██████╔╝█████╗  ██║  ██║
  ██╔══╝  ██╔══██╗██╔══╝  ██║  ██║      [dim]Build {build}[/dim]
  ██║     ██║  ██║███████╗██████╔╝
  ╚═╝     ╚═╝  ╚═╝╚══════╝╚═════╝ 
[/bold cyan]
[bold green]Autonomous Solana Trading Agent[/bold green]
[dim]Kelly Criterion × LLM Estimation × Persistent Memory[/dim]
""".format(version=VERSION, build=BUILD)

MOCK_MARKETS = [
    {"name": "SOL/USDC", "price": 96.42, "change": -2.1},
    {"name": "JUP/USDC", "price": 0.82, "change": 5.3},
    {"name": "BONK/USDC", "price": 0.000023, "change": -8.2},
    {"name": "WIF/USDC", "price": 1.45, "change": 12.1},
]

class DemoWallet:
    def __init__(self):
        self.sol_balance = 10.5
        self.usdc_balance = 500.0
        self.positions = {}

    def to_dict(self):
        return {
            "sol": self.sol_balance,
            "usdc": self.usdc_balance,
            "positions": self.positions
        }

async def scan_markets():
    """Simulate market scanning"""
    console.print("\n[bold yellow]📡 Scanning Markets...[/bold yellow]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Fetching market data...", total=None)
        await asyncio.sleep(1.2)
        progress.update(task, description="Analyzing opportunities...")
        await asyncio.sleep(0.8)
    
    table = Table(title="Active Markets")
    table.add_column("Market", style="cyan")
    table.add_column("Price", justify="right")
    table.add_column("24h Change", justify="right")
    
    for m in MOCK_MARKETS:
        change_style = "green" if m["change"] > 0 else "red"
        change_str = f"+{m['change']}%" if m["change"] > 0 else f"{m['change']}%"
        table.add_row(m["name"], f"${m['price']}", f"[{change_style}]{change_str}[/{change_style}]")
    
    console.print(table)
    return random.choice(MOCK_MARKETS)

async def estimate_probability(market):
    """Simulate LLM probability estimation"""
    console.print(f"\n[bold magenta]🧠 Estimating probability for {market['name']}...[/bold magenta]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        _task = progress.add_task("Running LLM inference...", total=None)  # noqa: F841
        await asyncio.sleep(1.5)
    
    prob = round(random.uniform(0.45, 0.75), 2)
    edge = round(prob - 0.5, 2)
    
    console.print(Panel(
        f"[bold]Estimated Probability:[/bold] {prob:.0%}\n"
        f"[bold]Edge vs Market:[/bold] {edge:+.0%}\n"
        f"[bold]Confidence:[/bold] {'High' if prob > 0.6 else 'Medium'}",
        title="📊 Analysis Result",
        border_style="magenta"
    ))
    
    return prob, edge

async def calculate_position(wallet, edge):
    """Kelly criterion position sizing"""
    console.print("\n[bold blue]📐 Calculating Position Size...[/bold blue]")
    await asyncio.sleep(0.5)
    
    kelly_fraction = edge * 2  # Simplified Kelly
    max_position = wallet.usdc_balance * 0.25  # Max 25% per trade
    position = min(max_position, wallet.usdc_balance * max(kelly_fraction, 0.05))
    
    console.print(Panel(
        f"[bold]Kelly Fraction:[/bold] {kelly_fraction:.1%}\n"
        f"[bold]Available USDC:[/bold] ${wallet.usdc_balance:.2f}\n"
        f"[bold]Position Size:[/bold] ${position:.2f}",
        title="💰 Position Sizing",
        border_style="blue"
    ))
    
    return position

async def execute_trade(wallet, market, position):
    """Simulate trade execution"""
    console.print(f"\n[bold green]🚀 Executing Trade on {market['name']}...[/bold green]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Preparing transaction...", total=None)
        await asyncio.sleep(0.7)
        progress.update(task, description="Sending to Jupiter...")
        await asyncio.sleep(1.0)
        progress.update(task, description="Confirming on Solana...")
        await asyncio.sleep(0.8)
    
    # Simulate trade
    tokens_bought = position / market["price"]
    wallet.usdc_balance -= position
    wallet.positions[market["name"]] = wallet.positions.get(market["name"], 0) + tokens_bought
    
    trade = {
        "timestamp": datetime.now().isoformat(),
        "market": market["name"],
        "side": "BUY",
        "amount_usdc": position,
        "tokens": tokens_bought,
        "price": market["price"]
    }
    
    console.print(Panel(
        f"[bold green]✅ Trade Executed![/bold green]\n\n"
        f"[bold]Market:[/bold] {market['name']}\n"
        f"[bold]Side:[/bold] BUY\n"
        f"[bold]Amount:[/bold] ${position:.2f}\n"
        f"[bold]Tokens:[/bold] {tokens_bought:.6f}\n"
        f"[bold]Price:[/bold] ${market['price']}",
        title="📝 Trade Confirmation",
        border_style="green"
    ))
    
    return trade

async def run_demo():
    """Main demo loop"""
    console.clear()
    console.print(LOGO)
    console.print("[dim]Demo Mode - No real trades[/dim]\n")
    
    wallet = DemoWallet()
    trades = []
    
    console.print(Panel(
        f"[bold]SOL Balance:[/bold] {wallet.sol_balance} SOL\n"
        f"[bold]USDC Balance:[/bold] ${wallet.usdc_balance:.2f}",
        title="💳 Wallet Status",
        border_style="cyan"
    ))
    
    for i in range(3):
        console.print(f"\n[bold white]{'='*50}[/bold white]")
        console.print(f"[bold white]TRADING CYCLE {i+1}/3[/bold white]")
        console.print(f"[bold white]{'='*50}[/bold white]")
        
        market = await scan_markets()
        prob, edge = await estimate_probability(market)
        
        if edge > 0.05:
            position = await calculate_position(wallet, edge)
            trade = await execute_trade(wallet, market, position)
            trades.append(trade)
        else:
            console.print("\n[yellow]⏸️ No edge detected, skipping trade[/yellow]")
        
        await asyncio.sleep(1)
    
    # Final summary
    console.print(f"\n[bold white]{'='*50}[/bold white]")
    console.print("[bold white]SESSION COMPLETE[/bold white]")
    console.print(f"[bold white]{'='*50}[/bold white]\n")
    
    console.print(Panel(
        f"[bold]Final SOL:[/bold] {wallet.sol_balance} SOL\n"
        f"[bold]Final USDC:[/bold] ${wallet.usdc_balance:.2f}\n"
        f"[bold]Trades Executed:[/bold] {len(trades)}\n"
        f"[bold]Positions:[/bold] {wallet.positions}",
        title="📈 Session Summary",
        border_style="cyan"
    ))
    
    # Save trades
    Path("demo_trades.json").write_text(json.dumps(trades, indent=2))
    console.print("\n[dim]Trades saved to demo_trades.json[/dim]")

if __name__ == "__main__":
    asyncio.run(run_demo())
