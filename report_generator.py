#!/usr/bin/env python3
"""
FRED Backtest Report Generator

Generates beautiful HTML reports from backtest results.
No external dependencies required (uses vanilla HTML/CSS/JS).
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any


def generate_html_report(
    backtest_results: Dict[str, Any],
    output_path: str = "backtest_report.html"
) -> str:
    """Generate an interactive HTML report from backtest results."""
    
    # Extract data
    trades = backtest_results.get("trades", [])
    equity_curve = backtest_results.get("equity_curve", [])
    metrics = backtest_results.get("metrics", {})
    
    # Calculate additional metrics
    if trades:
        winning_trades = [t for t in trades if t.get("pnl", 0) > 0]
        losing_trades = [t for t in trades if t.get("pnl", 0) < 0]
        win_rate = len(winning_trades) / len(trades) * 100 if trades else 0
        avg_win = sum(t["pnl"] for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t["pnl"] for t in losing_trades) / len(losing_trades) if losing_trades else 0
    else:
        win_rate = 0
        avg_win = 0
        avg_loss = 0
    
    # Calculate max drawdown
    peak = equity_curve[0] if equity_curve else 1000
    max_drawdown = 0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak
        if dd > max_drawdown:
            max_drawdown = dd
    
    # Generate HTML
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FRED-SOL Backtest Report</title>
    <style>
        :root {{
            --bg: #0a0a0f;
            --card-bg: #1a1a2e;
            --text: #e0e0e0;
            --text-muted: #888;
            --accent: #00ff88;
            --red: #ff4444;
            --green: #00ff88;
            --border: #333;
        }}
        
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            padding: 40px;
            line-height: 1.6;
        }}
        
        .container {{ max-width: 1200px; margin: 0 auto; }}
        
        h1 {{
            color: var(--accent);
            font-size: 2.5rem;
            margin-bottom: 10px;
        }}
        
        .subtitle {{
            color: var(--text-muted);
            margin-bottom: 30px;
        }}
        
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .card {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid var(--border);
        }}
        
        .card h3 {{
            color: var(--text-muted);
            font-size: 12px;
            text-transform: uppercase;
            margin-bottom: 8px;
            font-weight: 500;
        }}
        
        .card .value {{
            font-size: 28px;
            font-weight: bold;
        }}
        
        .positive {{ color: var(--green); }}
        .negative {{ color: var(--red); }}
        
        .chart-container {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid var(--border);
            margin-bottom: 30px;
        }}
        
        .chart {{
            height: 300px;
            display: flex;
            align-items: flex-end;
            gap: 2px;
            padding-top: 20px;
        }}
        
        .chart-bar {{
            flex: 1;
            background: linear-gradient(180deg, var(--accent) 0%, transparent 100%);
            border-radius: 2px 2px 0 0;
            min-width: 4px;
            transition: opacity 0.2s;
        }}
        
        .chart-bar:hover {{ opacity: 0.8; }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        
        th {{
            color: var(--text-muted);
            font-weight: 500;
            font-size: 12px;
            text-transform: uppercase;
        }}
        
        tr:hover {{ background: rgba(255,255,255,0.02); }}
        
        .footer {{
            text-align: center;
            color: var(--text-muted);
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid var(--border);
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
        }}
        
        .badge-buy {{
            background: rgba(0,255,136,0.1);
            color: var(--green);
        }}
        
        .badge-sell {{
            background: rgba(255,68,68,0.1);
            color: var(--red);
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 FRED-SOL Backtest Report</h1>
        <p class="subtitle">Generated {datetime.now().strftime("%B %d, %Y at %H:%M")}</p>
        
        <div class="grid">
            <div class="card">
                <h3>Initial Capital</h3>
                <div class="value">${metrics.get("initial_capital", 1000):.2f}</div>
            </div>
            <div class="card">
                <h3>Final Equity</h3>
                <div class="value {'positive' if equity_curve and equity_curve[-1] > metrics.get('initial_capital', 1000) else 'negative'}">${equity_curve[-1] if equity_curve else 1000:.2f}</div>
            </div>
            <div class="card">
                <h3>Total Return</h3>
                <div class="value {'positive' if metrics.get('total_return', 0) > 0 else 'negative'}">{metrics.get("total_return", 0):.1f}%</div>
            </div>
            <div class="card">
                <h3>Max Drawdown</h3>
                <div class="value negative">{max_drawdown*100:.1f}%</div>
            </div>
            <div class="card">
                <h3>Win Rate</h3>
                <div class="value">{win_rate:.1f}%</div>
            </div>
            <div class="card">
                <h3>Total Trades</h3>
                <div class="value">{len(trades)}</div>
            </div>
            <div class="card">
                <h3>Avg Win</h3>
                <div class="value positive">${avg_win:.2f}</div>
            </div>
            <div class="card">
                <h3>Avg Loss</h3>
                <div class="value negative">${abs(avg_loss):.2f}</div>
            </div>
        </div>
        
        <div class="chart-container">
            <h3 style="color: var(--text-muted); margin-bottom: 15px; font-size: 14px;">📈 Equity Curve</h3>
            <div class="chart" id="equity-chart"></div>
        </div>
        
        <div class="card">
            <h3 style="margin-bottom: 15px;">📜 Trade History</h3>
            <table>
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Side</th>
                        <th>Price</th>
                        <th>Size</th>
                        <th>P&L</th>
                    </tr>
                </thead>
                <tbody id="trades-table">
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p><strong>FRED-SOL</strong> — Autonomous Solana Trading Agent</p>
            <p>Built for Solana AI Agent Hackathon 2026</p>
            <p><a href="https://github.com/rickyautobots/fred-sol" style="color: var(--accent);">github.com/rickyautobots/fred-sol</a></p>
        </div>
    </div>
    
    <script>
        // Equity curve data
        const equityCurve = {json.dumps(equity_curve[:200] if len(equity_curve) > 200 else equity_curve)};
        
        // Trades data
        const trades = {json.dumps(trades[-50:] if len(trades) > 50 else trades)};
        
        // Render equity chart
        const chartEl = document.getElementById('equity-chart');
        if (equityCurve.length > 0) {{
            const min = Math.min(...equityCurve);
            const max = Math.max(...equityCurve);
            const range = max - min || 1;
            
            equityCurve.forEach((val, i) => {{
                const bar = document.createElement('div');
                bar.className = 'chart-bar';
                const height = ((val - min) / range) * 250 + 20;
                bar.style.height = height + 'px';
                bar.title = '$' + val.toFixed(2);
                chartEl.appendChild(bar);
            }});
        }}
        
        // Render trades table
        const tableEl = document.getElementById('trades-table');
        trades.forEach(trade => {{
            const row = document.createElement('tr');
            const pnl = trade.pnl || 0;
            const pnlClass = pnl >= 0 ? 'positive' : 'negative';
            const sideClass = trade.side === 'BUY' ? 'badge-buy' : 'badge-sell';
            
            row.innerHTML = `
                <td>${{trade.timestamp || '-'}}</td>
                <td><span class="badge ${{sideClass}}">${{trade.side}}</span></td>
                <td>${{trade.price ? '$' + trade.price.toFixed(4) : '-'}}</td>
                <td>${{trade.size ? trade.size.toFixed(4) : '-'}}</td>
                <td class="${{pnlClass}}">${{pnl >= 0 ? '+' : ''}}${{pnl.toFixed(2)}}</td>
            `;
            tableEl.appendChild(row);
        }});
    </script>
</body>
</html>
'''
    
    # Write to file
    Path(output_path).write_text(html)
    return output_path


def main():
    """Generate sample report."""
    import random
    
    # Create sample backtest data
    trades = []
    equity = 1000.0
    equity_curve = [equity]
    
    for i in range(50):
        pnl = random.uniform(-20, 30)
        equity += pnl
        equity_curve.append(equity)
        trades.append({
            "timestamp": f"2026-02-0{i//10+1} {i%24:02d}:00",
            "side": random.choice(["BUY", "SELL"]),
            "price": random.uniform(90, 110),
            "size": random.uniform(0.1, 2),
            "pnl": pnl
        })
    
    results = {
        "trades": trades,
        "equity_curve": equity_curve,
        "metrics": {
            "initial_capital": 1000,
            "total_return": (equity - 1000) / 1000 * 100
        }
    }
    
    output = generate_html_report(results, "sample_report.html")
    print(f"✅ Report generated: {output}")


if __name__ == "__main__":
    main()
