#!/usr/bin/env python3
"""
FRED Trade Logger

Structured logging for trades, decisions, and performance tracking.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class TradeLog:
    timestamp: str
    action: str  # SCAN, ESTIMATE, SIZE, EXECUTE, SKIP
    symbol: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> dict:
        d = asdict(self)
        if d["details"] is None:
            del d["details"]
        if d["symbol"] is None:
            del d["symbol"]
        return d


class TradeLogger:
    """Logs all trading activity for analysis."""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.logs: list = []
    
    def _log(self, action: str, symbol: Optional[str] = None, **details):
        """Internal logging method."""
        entry = TradeLog(
            timestamp=datetime.now().isoformat(),
            action=action,
            symbol=symbol,
            details=details if details else None
        )
        self.logs.append(entry)
        
        # Also print
        msg = f"[{entry.timestamp}] {action}"
        if symbol:
            msg += f" | {symbol}"
        if details:
            msg += f" | {json.dumps(details)}"
        print(msg)
    
    def scan_start(self, markets_count: int):
        self._log("SCAN_START", markets=markets_count)
    
    def scan_complete(self, opportunities: int):
        self._log("SCAN_COMPLETE", opportunities=opportunities)
    
    def estimate(self, symbol: str, probability: float, confidence: float, reasoning: str):
        self._log("ESTIMATE", symbol, 
                  probability=probability, 
                  confidence=confidence,
                  reasoning=reasoning)
    
    def size_calculated(self, symbol: str, kelly_fraction: float, position_size: float):
        self._log("SIZE", symbol,
                  kelly=kelly_fraction,
                  size_usd=position_size)
    
    def trade_executed(self, symbol: str, side: str, size: float, price: float, tx_hash: Optional[str] = None):
        self._log("EXECUTE", symbol,
                  side=side,
                  size=size,
                  price=price,
                  tx=tx_hash)
    
    def trade_skipped(self, symbol: str, reason: str):
        self._log("SKIP", symbol, reason=reason)
    
    def error(self, message: str, **details):
        self._log("ERROR", error=message, **details)
    
    def save(self):
        """Save logs to file."""
        path = self.log_dir / f"session_{self.session_id}.json"
        with open(path, "w") as f:
            json.dump([l.to_dict() for l in self.logs], f, indent=2)
        return path
    
    def get_summary(self) -> dict:
        """Get session summary."""
        trades = [l for l in self.logs if l.action == "EXECUTE"]
        skips = [l for l in self.logs if l.action == "SKIP"]
        errors = [l for l in self.logs if l.action == "ERROR"]
        
        return {
            "session_id": self.session_id,
            "total_logs": len(self.logs),
            "trades_executed": len(trades),
            "trades_skipped": len(skips),
            "errors": len(errors),
            "symbols_traded": list(set(l.symbol for l in trades if l.symbol))
        }


# Global logger instance
_logger: Optional[TradeLogger] = None

def get_logger() -> TradeLogger:
    global _logger
    if _logger is None:
        _logger = TradeLogger()
    return _logger


if __name__ == "__main__":
    # Test
    logger = TradeLogger()
    
    logger.scan_start(10)
    logger.estimate("SOL/USDC", 0.55, 0.6, "Volume-based heuristic")
    logger.size_calculated("SOL/USDC", 0.08, 100.0)
    logger.trade_executed("SOL/USDC", "BUY", 100, 96.42)
    logger.scan_complete(1)
    
    path = logger.save()
    print(f"\nLogs saved to: {path}")
    print(f"Summary: {logger.get_summary()}")
