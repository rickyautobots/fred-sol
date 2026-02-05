#!/usr/bin/env python3
"""FRED-SOL Live Demo — Streamlit App for Hackathon Judges"""

import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime
import random

# Page config
st.set_page_config(
    page_title="FRED-SOL | Autonomous Trading Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main { background-color: #0a0a0f; }
    .stApp { background-color: #0a0a0f; }
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 16px;
        padding: 20px;
        border: 1px solid rgba(0, 255, 136, 0.2);
    }
    .highlight { color: #00ff88; font-weight: bold; }
    .stButton>button {
        background: linear-gradient(90deg, #00ff88, #00cc6a);
        color: black;
        border: none;
        border-radius: 8px;
        font-weight: bold;
    }
    h1, h2, h3 { color: #e0e0e0; }
    .positive { color: #00ff88; }
    .negative { color: #ff4444; }
</style>
""", unsafe_allow_html=True)

# ============ SIMULATED MARKET DATA ============

MARKETS = [
    {"symbol": "SOL/USDC", "base": "SOL", "price": 96.42, "volume_24h": 1_234_567_890, "change_24h": -2.1},
    {"symbol": "JUP/USDC", "base": "JUP", "price": 0.82, "volume_24h": 45_678_901, "change_24h": 5.3},
    {"symbol": "BONK/USDC", "base": "BONK", "price": 0.000023, "volume_24h": 89_012_345, "change_24h": -8.2},
    {"symbol": "WIF/USDC", "base": "WIF", "price": 1.45, "volume_24h": 67_890_123, "change_24h": 12.1},
    {"symbol": "PYTH/USDC", "base": "PYTH", "price": 0.35, "volume_24h": 23_456_789, "change_24h": 3.7},
    {"symbol": "JTO/USDC", "base": "JTO", "price": 2.87, "volume_24h": 12_345_678, "change_24h": -1.2},
]

# ============ KELLY CRITERION LOGIC ============

def kelly_criterion(p: float, b: float = 1.0) -> float:
    """
    Calculate optimal bet fraction using Kelly criterion.
    p: probability of winning
    b: odds received (1.0 for even money)
    """
    q = 1 - p
    if p <= 0 or p >= 1:
        return 0
    kelly = (b * p - q) / b
    return max(0, min(kelly, 0.25))  # Cap at 25%

def half_kelly(p: float, confidence: float = 0.8) -> float:
    """Half-Kelly with confidence adjustment for reduced variance."""
    full_kelly = kelly_criterion(p)
    return full_kelly * 0.5 * confidence

# ============ LLM ESTIMATION SIMULATION ============

def estimate_probability(market: dict) -> tuple:
    """
    Simulate LLM probability estimation.
    In production, this calls Claude API with market context.
    """
    # Factors that influence our estimate
    momentum = market["change_24h"] / 100
    volume_factor = np.log10(market["volume_24h"]) / 10
    
    # Base estimate with noise
    base_prob = 0.5 + (momentum * 0.3) + (volume_factor * 0.05)
    noise = np.random.normal(0, 0.05)
    prob = np.clip(base_prob + noise, 0.1, 0.9)
    
    # Confidence based on volume
    confidence = min(0.95, 0.5 + (volume_factor * 0.3))
    
    return round(prob, 3), round(confidence, 3)

# ============ TRADING SIMULATION ============

def simulate_trade_execution(market: dict, position_size: float, side: str) -> dict:
    """Simulate trade execution with realistic slippage."""
    slippage = random.uniform(0.001, 0.003)  # 0.1-0.3% slippage
    executed_price = market["price"] * (1 + slippage if side == "BUY" else 1 - slippage)
    
    return {
        "timestamp": datetime.now().isoformat(),
        "market": market["symbol"],
        "side": side,
        "size_usdc": position_size,
        "tokens": position_size / executed_price,
        "price": executed_price,
        "slippage_bps": slippage * 10000,
        "tx_hash": f"sim_{random.randint(10000, 99999)}...{random.randint(1000, 9999)}"
    }

# ============ SESSION STATE ============

if "wallet" not in st.session_state:
    st.session_state.wallet = {"USDC": 1000.0, "SOL": 0, "positions": {}}

if "trades" not in st.session_state:
    st.session_state.trades = []

if "pnl_history" not in st.session_state:
    st.session_state.pnl_history = [1000.0]

# ============ SIDEBAR ============

with st.sidebar:
    st.image("https://raw.githubusercontent.com/rickyautobots/fred-sol/main/docs/logo.png", width=100)
    st.title("🤖 FRED-SOL")
    st.caption("Autonomous Solana Trading Agent")
    
    st.divider()
    
    st.subheader("📊 Configuration")
    risk_mode = st.selectbox("Risk Mode", ["Conservative (Half-Kelly)", "Moderate (Full Kelly)", "Aggressive (1.5x Kelly)"])
    max_position = st.slider("Max Position Size", 5, 50, 25, format="%d%%")
    
    st.divider()
    
    st.subheader("🔗 Links")
    st.markdown("""
    - [GitHub](https://github.com/rickyautobots/fred-sol)
    - [Documentation](https://github.com/rickyautobots/fred-sol#readme)
    - [Hackathon](https://colosseum.org/agent-hackathon)
    """)
    
    st.divider()
    
    st.caption("Built for Solana AI Agent Hackathon 2026")
    st.caption("Prize Pool: $100,000 USDC")

# ============ MAIN CONTENT ============

st.title("🤖 FRED-SOL Demo")
st.caption("Autonomous trading agent using Kelly criterion + LLM probability estimation")

# Metrics row
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("💰 Portfolio Value", f"${st.session_state.wallet['USDC']:.2f}")
    
with col2:
    total_trades = len(st.session_state.trades)
    st.metric("📈 Total Trades", total_trades)
    
with col3:
    if st.session_state.trades:
        winning = sum(1 for t in st.session_state.trades if t.get("pnl", 0) > 0)
        win_rate = (winning / total_trades * 100) if total_trades > 0 else 0
    else:
        win_rate = 0
    st.metric("🎯 Win Rate", f"{win_rate:.1f}%")
    
with col4:
    pnl = st.session_state.wallet["USDC"] - 1000
    st.metric("💵 Total P&L", f"${pnl:+.2f}", delta=f"{pnl/10:.1f}%")

st.divider()

# ============ LIVE MARKET SCANNER ============

st.header("📡 Market Scanner")

# Add some randomness to prices
for m in MARKETS:
    m["price"] = m["price"] * (1 + random.uniform(-0.001, 0.001))
    m["change_24h"] = m["change_24h"] + random.uniform(-0.5, 0.5)

market_df = pd.DataFrame(MARKETS)
market_df["Volume"] = market_df["volume_24h"].apply(lambda x: f"${x/1e6:.1f}M")
market_df["24h Change"] = market_df["change_24h"].apply(lambda x: f"{x:+.1f}%")
market_df["Price"] = market_df["price"].apply(lambda x: f"${x:.6f}" if x < 0.01 else f"${x:.2f}")

display_df = market_df[["symbol", "Price", "Volume", "24h Change"]].copy()
display_df.columns = ["Market", "Price", "24h Volume", "Change"]

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)

st.divider()

# ============ TRADING INTERFACE ============

st.header("🎯 Trade Execution")

col1, col2 = st.columns(2)

with col1:
    selected_market = st.selectbox("Select Market", [m["symbol"] for m in MARKETS])
    market = next(m for m in MARKETS if m["symbol"] == selected_market)
    
    st.info(f"**Current Price:** ${market['price']:.4f}")

with col2:
    if st.button("🧠 Run LLM Analysis", use_container_width=True):
        with st.spinner("Running probability estimation..."):
            time.sleep(1.5)  # Simulate API call
            prob, confidence = estimate_probability(market)
            
            st.session_state.last_analysis = {
                "market": market["symbol"],
                "probability": prob,
                "confidence": confidence,
                "kelly": half_kelly(prob, confidence),
                "timestamp": datetime.now()
            }
            
            st.success("Analysis complete!")

# Show analysis results
if "last_analysis" in st.session_state:
    analysis = st.session_state.last_analysis
    
    st.subheader("📊 Analysis Results")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Estimated Probability", f"{analysis['probability']:.1%}")
    
    with col2:
        st.metric("Confidence Score", f"{analysis['confidence']:.1%}")
    
    with col3:
        kelly_pct = analysis['kelly'] * 100
        st.metric("Kelly Fraction", f"{kelly_pct:.1f}%")
    
    # Position sizing
    position_size = st.session_state.wallet["USDC"] * analysis['kelly']
    st.info(f"**Recommended Position:** ${position_size:.2f} ({analysis['kelly']*100:.1f}% of portfolio)")
    
    # Execute trade button
    edge = analysis['probability'] - 0.5
    if edge > 0.05:  # Only trade if we have edge
        if st.button("🚀 Execute Trade", type="primary", use_container_width=True):
            with st.spinner("Executing trade on Jupiter..."):
                time.sleep(1)
                trade = simulate_trade_execution(market, position_size, "BUY")
                trade["analysis"] = analysis
                st.session_state.trades.append(trade)
                st.session_state.wallet["USDC"] -= position_size
                st.session_state.wallet["positions"][market["symbol"]] = position_size
                st.session_state.pnl_history.append(st.session_state.wallet["USDC"])
                
            st.success(f"✅ Trade executed! Bought ${position_size:.2f} of {market['symbol']}")
            st.balloons()
    else:
        st.warning("⚠️ No significant edge detected. Skipping trade.")

st.divider()

# ============ TRADE HISTORY ============

st.header("📜 Trade History")

if st.session_state.trades:
    trade_df = pd.DataFrame(st.session_state.trades)
    trade_df["Time"] = pd.to_datetime(trade_df["timestamp"]).dt.strftime("%H:%M:%S")
    trade_df["Size"] = trade_df["size_usdc"].apply(lambda x: f"${x:.2f}")
    trade_df["Price"] = trade_df["price"].apply(lambda x: f"${x:.4f}")
    trade_df["Slippage"] = trade_df["slippage_bps"].apply(lambda x: f"{x:.1f} bps")
    
    display_trades = trade_df[["Time", "market", "side", "Size", "Price", "Slippage"]].copy()
    display_trades.columns = ["Time", "Market", "Side", "Size", "Price", "Slippage"]
    
    st.dataframe(display_trades, use_container_width=True, hide_index=True)
else:
    st.info("No trades executed yet. Run an analysis and execute a trade to see history.")

st.divider()

# ============ P&L CHART ============

st.header("📈 Portfolio Performance")

if len(st.session_state.pnl_history) > 1:
    chart_data = pd.DataFrame({
        "Trade #": range(len(st.session_state.pnl_history)),
        "Portfolio Value": st.session_state.pnl_history
    })
    st.line_chart(chart_data.set_index("Trade #"))
else:
    st.info("Execute trades to see portfolio performance chart.")

st.divider()

# ============ TECHNICAL DETAILS ============

with st.expander("🔧 Technical Details"):
    st.markdown("""
    ### Kelly Criterion
    
    FRED uses the Kelly criterion for mathematically optimal position sizing:
    
    ```
    f* = (bp - q) / b
    
    where:
      f* = optimal fraction of capital
      b  = odds (payout ratio)  
      p  = probability of winning
      q  = 1 - p
    ```
    
    We use **half-Kelly with confidence adjustment** for reduced variance:
    
    ```python
    adjusted_size = kelly_fraction * confidence * 0.5
    ```
    
    ### Risk Management
    
    | Parameter | Value |
    |-----------|-------|
    | Max Position | 25% of portfolio |
    | Min Edge | 5% above market |
    | Max Drawdown | 15% hard stop |
    | Daily Loss Limit | 5% |
    
    ### Architecture
    
    ```
    Scanner (Jupiter) → Estimator (Claude) → Agent (Kelly) → Executor (Jupiter)
    ```
    """)

# ============ FOOTER ============

st.divider()

st.caption("""
**FRED-SOL** — Autonomous Solana Trading Agent  
Built by Ricky (@rickyautobots) for the Solana AI Agent Hackathon 2026  
⚠️ This is a demo with simulated trades. No real assets are traded.
""")
