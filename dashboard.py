#!/usr/bin/env python3
"""FRED Web Dashboard - FastAPI backend"""

import json
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI(title="FRED Dashboard")

# Mock data store
MOCK_WALLET = {"sol": 10.5, "usdc": 487.32, "address": "Demo...xyz"}
MOCK_TRADES = [
    {"id": 1, "timestamp": "2024-02-04T10:30:00", "market": "SOL/USDC", "side": "BUY", "amount": 50, "price": 96.42},
    {"id": 2, "timestamp": "2024-02-04T11:15:00", "market": "JUP/USDC", "side": "BUY", "amount": 25, "price": 0.82},
    {"id": 3, "timestamp": "2024-02-04T12:00:00", "market": "SOL/USDC", "side": "SELL", "amount": 50, "price": 98.10},
]
MOCK_METRICS = {"total_pnl": 12.68, "win_rate": 66.7, "trades_today": 3, "active_positions": 1}

@app.get("/api/status")
async def get_status():
    return {
        "status": "running",
        "uptime": "4h 32m",
        "wallet": MOCK_WALLET,
        "last_scan": datetime.now().isoformat()
    }

@app.get("/api/trades")
async def get_trades():
    return {"trades": MOCK_TRADES}

@app.get("/api/metrics")
async def get_metrics():
    return MOCK_METRICS

@app.get("/", response_class=HTMLResponse)
async def root():
    return """<!DOCTYPE html>
<html>
<head>
    <title>FRED Dashboard</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               background: #0a0a0f; color: #e0e0e0; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #00ff88; margin-bottom: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { background: #1a1a2e; border-radius: 12px; padding: 20px; border: 1px solid #333; }
        .card h3 { color: #888; font-size: 12px; text-transform: uppercase; margin-bottom: 10px; }
        .card .value { font-size: 28px; font-weight: bold; color: #fff; }
        .positive { color: #00ff88 !important; }
        .negative { color: #ff4444 !important; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #333; }
        th { color: #888; font-weight: normal; }
        .status { display: inline-block; width: 8px; height: 8px; background: #00ff88; 
                  border-radius: 50%; margin-right: 8px; animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        #chart { height: 200px; background: linear-gradient(180deg, rgba(0,255,136,0.1) 0%, transparent 100%); 
                 border-radius: 8px; display: flex; align-items: flex-end; padding: 10px; gap: 2px; }
        .bar { background: #00ff88; width: 20px; border-radius: 2px 2px 0 0; transition: height 0.3s; }
    </style>
</head>
<body>
    <div class="container">
        <h1><span class="status"></span>FRED Dashboard</h1>
        
        <div class="grid">
            <div class="card">
                <h3>Wallet Balance</h3>
                <div class="value" id="sol-balance">--</div>
                <div style="color:#888">SOL</div>
                <div class="value" style="margin-top:10px" id="usdc-balance">--</div>
                <div style="color:#888">USDC</div>
            </div>
            
            <div class="card">
                <h3>Today's P&L</h3>
                <div class="value positive" id="pnl">--</div>
            </div>
            
            <div class="card">
                <h3>Win Rate</h3>
                <div class="value" id="win-rate">--</div>
            </div>
            
            <div class="card">
                <h3>Trades Today</h3>
                <div class="value" id="trades-count">--</div>
            </div>
        </div>
        
        <div class="card" style="margin-top:20px">
            <h3>P&L Chart (24h)</h3>
            <div id="chart"></div>
        </div>
        
        <div class="card" style="margin-top:20px">
            <h3>Recent Trades</h3>
            <table>
                <thead><tr><th>Time</th><th>Market</th><th>Side</th><th>Amount</th><th>Price</th></tr></thead>
                <tbody id="trades-table"></tbody>
            </table>
        </div>
    </div>
    
    <script>
        async function fetchData() {
            try {
                const [status, trades, metrics] = await Promise.all([
                    fetch('/api/status').then(r => r.json()),
                    fetch('/api/trades').then(r => r.json()),
                    fetch('/api/metrics').then(r => r.json())
                ]);
                
                document.getElementById('sol-balance').textContent = status.wallet.sol.toFixed(4);
                document.getElementById('usdc-balance').textContent = '$' + status.wallet.usdc.toFixed(2);
                document.getElementById('pnl').textContent = (metrics.total_pnl >= 0 ? '+' : '') + '$' + metrics.total_pnl.toFixed(2);
                document.getElementById('pnl').className = 'value ' + (metrics.total_pnl >= 0 ? 'positive' : 'negative');
                document.getElementById('win-rate').textContent = metrics.win_rate.toFixed(1) + '%';
                document.getElementById('trades-count').textContent = metrics.trades_today;
                
                // Trades table
                const tbody = document.getElementById('trades-table');
                tbody.innerHTML = trades.trades.map(t => 
                    `<tr><td>${new Date(t.timestamp).toLocaleTimeString()}</td><td>${t.market}</td>
                     <td style="color:${t.side==='BUY'?'#00ff88':'#ff4444'}">${t.side}</td>
                     <td>$${t.amount}</td><td>$${t.price}</td></tr>`
                ).join('');
                
                // Chart (mock data)
                const chart = document.getElementById('chart');
                chart.innerHTML = '';
                for(let i = 0; i < 24; i++) {
                    const h = 20 + Math.random() * 150;
                    chart.innerHTML += `<div class="bar" style="height:${h}px"></div>`;
                }
            } catch(e) { console.error(e); }
        }
        
        fetchData();
        setInterval(fetchData, 30000);
    </script>
</body>
</html>"""


def run_dashboard(host: str = "0.0.0.0", port: int = 8080):
    """Run the dashboard server."""
    print(f"🚀 FRED Dashboard starting on http://localhost:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    run_dashboard()
