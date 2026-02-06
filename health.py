#!/usr/bin/env python3
"""
FRED-SOL: Health Check System
Monitor agent health and dependencies

Built: 2026-02-06 07:15 CST by Ricky
"""

import asyncio
import os
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum

import httpx


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class CheckResult:
    """Result of a health check"""
    name: str
    status: HealthStatus
    latency_ms: Optional[float] = None
    message: Optional[str] = None
    metadata: Optional[Dict] = None


class HealthChecker:
    """
    Health monitoring for FRED trading agent
    
    Checks:
    - Solana RPC connectivity
    - Jupiter API availability
    - Wallet balance sufficiency
    - LLM API status
    - Alert webhook reachability
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.client = httpx.AsyncClient(timeout=10.0)
        self.last_check: Optional[datetime] = None
        self.results: List[CheckResult] = []
    
    async def check_solana_rpc(self) -> CheckResult:
        """Check Solana RPC connectivity"""
        rpc_url = self.config.get("rpc_url", "https://api.mainnet-beta.solana.com")
        
        start = datetime.now()
        try:
            resp = await self.client.post(
                rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getHealth"
                }
            )
            latency = (datetime.now() - start).total_seconds() * 1000
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get("result") == "ok":
                    return CheckResult(
                        name="solana_rpc",
                        status=HealthStatus.HEALTHY,
                        latency_ms=latency,
                        message=f"Connected to {rpc_url}"
                    )
            
            return CheckResult(
                name="solana_rpc",
                status=HealthStatus.DEGRADED,
                latency_ms=latency,
                message=f"RPC returned status {resp.status_code}"
            )
            
        except Exception as e:
            return CheckResult(
                name="solana_rpc",
                status=HealthStatus.UNHEALTHY,
                message=f"RPC error: {str(e)}"
            )
    
    async def check_jupiter(self) -> CheckResult:
        """Check Jupiter API availability"""
        start = datetime.now()
        try:
            resp = await self.client.get("https://quote-api.jup.ag/v6/tokens")
            latency = (datetime.now() - start).total_seconds() * 1000
            
            if resp.status_code == 200:
                return CheckResult(
                    name="jupiter",
                    status=HealthStatus.HEALTHY,
                    latency_ms=latency,
                    message="Jupiter API available"
                )
            
            return CheckResult(
                name="jupiter",
                status=HealthStatus.DEGRADED,
                latency_ms=latency,
                message=f"Jupiter returned {resp.status_code}"
            )
            
        except Exception as e:
            return CheckResult(
                name="jupiter",
                status=HealthStatus.UNHEALTHY,
                message=f"Jupiter error: {str(e)}"
            )
    
    async def check_wallet_balance(self) -> CheckResult:
        """Check wallet has sufficient balance"""
        wallet = self.config.get("wallet_address")
        min_sol = self.config.get("min_sol_balance", 0.01)
        rpc_url = self.config.get("rpc_url", "https://api.mainnet-beta.solana.com")
        
        if not wallet:
            return CheckResult(
                name="wallet_balance",
                status=HealthStatus.UNKNOWN,
                message="No wallet configured"
            )
        
        try:
            resp = await self.client.post(
                rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getBalance",
                    "params": [wallet]
                }
            )
            
            data = resp.json()
            balance_lamports = data.get("result", {}).get("value", 0)
            balance_sol = balance_lamports / 1_000_000_000
            
            if balance_sol >= min_sol:
                return CheckResult(
                    name="wallet_balance",
                    status=HealthStatus.HEALTHY,
                    message=f"Balance: {balance_sol:.4f} SOL",
                    metadata={"balance_sol": balance_sol}
                )
            else:
                return CheckResult(
                    name="wallet_balance",
                    status=HealthStatus.DEGRADED,
                    message=f"Low balance: {balance_sol:.4f} SOL (min: {min_sol})",
                    metadata={"balance_sol": balance_sol}
                )
                
        except Exception as e:
            return CheckResult(
                name="wallet_balance",
                status=HealthStatus.UNHEALTHY,
                message=f"Balance check error: {str(e)}"
            )
    
    async def check_llm_api(self) -> CheckResult:
        """Check LLM API availability"""
        api_key = self.config.get("llm_api_key") or os.environ.get("ANTHROPIC_API_KEY")
        
        if not api_key:
            return CheckResult(
                name="llm_api",
                status=HealthStatus.UNKNOWN,
                message="No API key configured"
            )
        
        start = datetime.now()
        try:
            # Simple validation endpoint check
            resp = await self.client.get(
                "https://api.anthropic.com/v1/models",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01"
                }
            )
            latency = (datetime.now() - start).total_seconds() * 1000
            
            if resp.status_code in [200, 401]:  # 401 means API is up but key invalid
                status = HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.DEGRADED
                return CheckResult(
                    name="llm_api",
                    status=status,
                    latency_ms=latency,
                    message="Anthropic API reachable" if status == HealthStatus.HEALTHY else "Invalid API key"
                )
            
            return CheckResult(
                name="llm_api",
                status=HealthStatus.DEGRADED,
                message=f"API returned {resp.status_code}"
            )
            
        except Exception as e:
            return CheckResult(
                name="llm_api",
                status=HealthStatus.UNHEALTHY,
                message=f"LLM API error: {str(e)}"
            )
    
    async def check_all(self) -> Dict[str, Any]:
        """Run all health checks"""
        self.last_check = datetime.now(timezone.utc)
        
        # Run checks in parallel
        checks = await asyncio.gather(
            self.check_solana_rpc(),
            self.check_jupiter(),
            self.check_wallet_balance(),
            self.check_llm_api(),
            return_exceptions=True
        )
        
        self.results = []
        for check in checks:
            if isinstance(check, CheckResult):
                self.results.append(check)
            else:
                # Exception occurred
                self.results.append(CheckResult(
                    name="unknown",
                    status=HealthStatus.UNHEALTHY,
                    message=str(check)
                ))
        
        # Determine overall status
        statuses = [r.status for r in self.results]
        if all(s == HealthStatus.HEALTHY for s in statuses):
            overall = HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall = HealthStatus.UNHEALTHY
        else:
            overall = HealthStatus.DEGRADED
        
        return {
            "status": overall.value,
            "timestamp": self.last_check.isoformat(),
            "checks": [
                {
                    "name": r.name,
                    "status": r.status.value,
                    "latency_ms": r.latency_ms,
                    "message": r.message,
                    "metadata": r.metadata
                }
                for r in self.results
            ]
        }
    
    async def close(self):
        await self.client.aclose()


async def main():
    """Run health check"""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="FRED Health Check")
    parser.add_argument("--wallet", "-w", help="Wallet address to check")
    parser.add_argument("--rpc", help="Custom RPC URL")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()
    
    config = {}
    if args.wallet:
        config["wallet_address"] = args.wallet
    if args.rpc:
        config["rpc_url"] = args.rpc
    
    checker = HealthChecker(config)
    
    try:
        results = await checker.check_all()
        
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print("\n" + "=" * 50)
            print("FRED-SOL Health Check")
            print("=" * 50)
            print(f"Overall: {results['status'].upper()}")
            print(f"Time: {results['timestamp']}")
            print("-" * 50)
            
            for check in results['checks']:
                status_emoji = {
                    "healthy": "✅",
                    "degraded": "⚠️",
                    "unhealthy": "❌",
                    "unknown": "❓"
                }.get(check['status'], "❓")
                
                latency = f" ({check['latency_ms']:.0f}ms)" if check['latency_ms'] else ""
                print(f"{status_emoji} {check['name']}: {check['message']}{latency}")
            
            print("=" * 50)
    
    finally:
        await checker.close()


if __name__ == "__main__":
    asyncio.run(main())
