#!/usr/bin/env python3
"""
FRED API Server

REST API for external integrations.
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

from estimator import ProbabilityEstimator
from risk import RiskManager

app = FastAPI(
    title="FRED API",
    description="Autonomous Solana Trading Agent API",
    version="1.0.0"
)

# Global instances
estimator = ProbabilityEstimator()
risk_manager = RiskManager()


class MarketData(BaseModel):
    symbol: str
    price: float
    volume_24h: float = 0
    price_change_24h: float = 0
    market_cap: float = 0


class EstimateResponse(BaseModel):
    symbol: str
    probability: float
    confidence: float
    reasoning: str
    kelly_size: float


class TradeRequest(BaseModel):
    symbol: str
    size_usd: float
    price: float


class StatusResponse(BaseModel):
    capital: float
    pnl_total: float
    pnl_pct: float
    exposure: float
    drawdown: float
    positions: int


@app.get("/")
async def root():
    return {"name": "FRED API", "status": "running", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/estimate", response_model=EstimateResponse)
async def estimate_probability(market: MarketData):
    """Estimate probability for a market."""
    result = await estimator.estimate(market.dict())
    
    # Calculate Kelly size
    if result.probability > 0.5:
        edge = result.probability - 0.5
        kelly = edge * result.confidence * 0.5  # Half-Kelly
    else:
        kelly = 0
    
    return EstimateResponse(
        symbol=market.symbol,
        probability=result.probability,
        confidence=result.confidence,
        reasoning=result.reasoning,
        kelly_size=kelly
    )


@app.post("/estimate/batch", response_model=List[EstimateResponse])
async def estimate_batch(markets: List[MarketData]):
    """Estimate probabilities for multiple markets."""
    results = []
    for market in markets:
        result = await estimator.estimate(market.dict())
        edge = max(0, result.probability - 0.5)
        kelly = edge * result.confidence * 0.5
        results.append(EstimateResponse(
            symbol=market.symbol,
            probability=result.probability,
            confidence=result.confidence,
            reasoning=result.reasoning,
            kelly_size=kelly
        ))
    return results


@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Get current risk/capital status."""
    status = risk_manager.get_status()
    return StatusResponse(
        capital=status["capital"],
        pnl_total=status["pnl_total"],
        pnl_pct=status["pnl_pct"],
        exposure=status["exposure"],
        drawdown=status["drawdown"],
        positions=status["positions"]
    )


@app.post("/can_trade")
async def can_trade(request: TradeRequest):
    """Check if a trade is allowed under risk rules."""
    allowed, reason = risk_manager.can_trade(request.symbol, request.size_usd)
    return {"allowed": allowed, "reason": reason}


@app.get("/positions")
async def get_positions():
    """Get open positions."""
    return {
        symbol: {
            "size": pos.size,
            "entry_price": pos.entry_price,
            "current_price": pos.current_price,
            "pnl": pos.pnl,
            "pnl_usd": pos.pnl_usd
        }
        for symbol, pos in risk_manager.positions.items()
    }


def run_api(host: str = "0.0.0.0", port: int = 8000):
    """Run the API server."""
    import uvicorn
    print(f"🚀 FRED API starting on http://localhost:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_api()
