#!/usr/bin/env python3
"""
FRED-SOL: Utility Functions
Common helpers and utilities

Built: 2026-02-06 07:50 CST by Ricky
"""

import os
import json
import hashlib
import base64
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, TypeVar, Union
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
import asyncio
from functools import wraps
import time


T = TypeVar('T')


# ============ Time Utilities ============

def utc_now() -> datetime:
    """Get current UTC timestamp"""
    return datetime.now(timezone.utc)


def timestamp_ms() -> int:
    """Get current timestamp in milliseconds"""
    return int(time.time() * 1000)


def parse_timestamp(ts: Union[int, str, datetime]) -> datetime:
    """Parse various timestamp formats to datetime"""
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, int):
        # Assume milliseconds if large
        if ts > 1e12:
            ts = ts / 1000
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    if isinstance(ts, str):
        return datetime.fromisoformat(ts.replace('Z', '+00:00'))
    raise ValueError(f"Cannot parse timestamp: {ts}")


def format_duration(seconds: float) -> str:
    """Format duration in human-readable form"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds / 60:.1f}m"
    elif seconds < 86400:
        return f"{seconds / 3600:.1f}h"
    else:
        return f"{seconds / 86400:.1f}d"


def time_ago(dt: datetime) -> str:
    """Get human-readable time ago string"""
    now = utc_now()
    diff = now - dt
    return format_duration(diff.total_seconds()) + " ago"


# ============ Number Utilities ============

def safe_decimal(value: Any, default: Decimal = Decimal("0")) -> Decimal:
    """Safely convert value to Decimal"""
    if value is None:
        return default
    try:
        return Decimal(str(value))
    except:
        return default


def format_usd(amount: float, decimals: int = 2) -> str:
    """Format amount as USD string"""
    if abs(amount) >= 1_000_000:
        return f"${amount / 1_000_000:.2f}M"
    elif abs(amount) >= 1_000:
        return f"${amount / 1_000:.2f}K"
    else:
        return f"${amount:,.{decimals}f}"


def format_pct(value: float, decimals: int = 1, plus: bool = True) -> str:
    """Format value as percentage"""
    if plus and value > 0:
        return f"+{value:.{decimals}f}%"
    return f"{value:.{decimals}f}%"


def round_to_precision(value: float, precision: int = 4) -> float:
    """Round to specified decimal precision"""
    factor = 10 ** precision
    return round(value * factor) / factor


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value to range"""
    return max(min_val, min(max_val, value))


# ============ Crypto Utilities ============

def shorten_address(address: str, chars: int = 6) -> str:
    """Shorten blockchain address for display"""
    if len(address) <= chars * 2 + 3:
        return address
    return f"{address[:chars]}...{address[-chars:]}"


def validate_solana_address(address: str) -> bool:
    """Basic validation of Solana address"""
    if not address:
        return False
    # Base58 alphabet (no 0, O, I, l)
    base58_chars = set("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")
    if not all(c in base58_chars for c in address):
        return False
    return 32 <= len(address) <= 44


def validate_eth_address(address: str) -> bool:
    """Basic validation of Ethereum address"""
    if not address:
        return False
    if not address.startswith("0x"):
        return False
    if len(address) != 42:
        return False
    try:
        int(address, 16)
        return True
    except:
        return False


def lamports_to_sol(lamports: int) -> Decimal:
    """Convert lamports to SOL"""
    return Decimal(lamports) / Decimal(1_000_000_000)


def sol_to_lamports(sol: Decimal) -> int:
    """Convert SOL to lamports"""
    return int(sol * Decimal(1_000_000_000))


# ============ File Utilities ============

def ensure_dir(path: Union[str, Path]) -> Path:
    """Ensure directory exists, create if not"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def safe_json_load(filepath: Union[str, Path], default: Any = None) -> Any:
    """Safely load JSON file"""
    try:
        with open(filepath) as f:
            return json.load(f)
    except:
        return default


def safe_json_save(filepath: Union[str, Path], data: Any, indent: int = 2):
    """Safely save data to JSON file"""
    ensure_dir(Path(filepath).parent)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=indent, default=str)


def file_hash(filepath: Union[str, Path]) -> str:
    """Get SHA256 hash of file"""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


# ============ Async Utilities ============

def async_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """Decorator for async function with retry logic"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
            
            raise last_exception
        return wrapper
    return decorator


async def gather_with_timeout(
    coros: List,
    timeout: float = 30.0,
    return_exceptions: bool = True
) -> List:
    """Gather coroutines with timeout"""
    try:
        return await asyncio.wait_for(
            asyncio.gather(*coros, return_exceptions=return_exceptions),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        return [TimeoutError("Operation timed out")] * len(coros)


def run_async(coro):
    """Run async function from sync context"""
    try:
        loop = asyncio.get_running_loop()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


# ============ Rate Limiting ============

class RateLimiter:
    """Simple rate limiter"""
    
    def __init__(self, calls: int, period: float):
        """
        Args:
            calls: Max calls per period
            period: Period in seconds
        """
        self.calls = calls
        self.period = period
        self.timestamps: List[float] = []
    
    async def acquire(self):
        """Wait if rate limit exceeded"""
        now = time.time()
        
        # Remove old timestamps
        self.timestamps = [t for t in self.timestamps if now - t < self.period]
        
        if len(self.timestamps) >= self.calls:
            wait_time = self.timestamps[0] + self.period - now
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        self.timestamps.append(time.time())


# ============ Environment ============

def get_env(key: str, default: str = None, required: bool = False) -> str:
    """Get environment variable with validation"""
    value = os.environ.get(key, default)
    if required and not value:
        raise ValueError(f"Required environment variable not set: {key}")
    return value


def get_env_bool(key: str, default: bool = False) -> bool:
    """Get boolean environment variable"""
    value = os.environ.get(key, "").lower()
    if value in ("true", "1", "yes"):
        return True
    elif value in ("false", "0", "no"):
        return False
    return default


def get_env_int(key: str, default: int = 0) -> int:
    """Get integer environment variable"""
    try:
        return int(os.environ.get(key, default))
    except:
        return default


# ============ Logging Helpers ============

class Colors:
    """ANSI color codes"""
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"


def color_text(text: str, color: str) -> str:
    """Wrap text in color codes"""
    return f"{color}{text}{Colors.RESET}"


def log_info(msg: str):
    """Log info message"""
    print(f"{Colors.BLUE}[INFO]{Colors.RESET} {msg}")


def log_success(msg: str):
    """Log success message"""
    print(f"{Colors.GREEN}[SUCCESS]{Colors.RESET} {msg}")


def log_warning(msg: str):
    """Log warning message"""
    print(f"{Colors.YELLOW}[WARNING]{Colors.RESET} {msg}")


def log_error(msg: str):
    """Log error message"""
    print(f"{Colors.RED}[ERROR]{Colors.RESET} {msg}")


# ============ Data Structures ============

class LRUCache:
    """Simple LRU cache"""
    
    def __init__(self, capacity: int = 100):
        self.capacity = capacity
        self.cache: Dict[str, Any] = {}
        self.order: List[str] = []
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            self.order.remove(key)
            self.order.append(key)
            return self.cache[key]
        return None
    
    def put(self, key: str, value: Any):
        if key in self.cache:
            self.order.remove(key)
        elif len(self.cache) >= self.capacity:
            oldest = self.order.pop(0)
            del self.cache[oldest]
        
        self.cache[key] = value
        self.order.append(key)
    
    def clear(self):
        self.cache.clear()
        self.order.clear()


if __name__ == "__main__":
    # Demo
    print("=== FRED-SOL Utilities Demo ===\n")
    
    # Time
    print(f"UTC Now: {utc_now()}")
    print(f"Timestamp: {timestamp_ms()}")
    print(f"Duration: {format_duration(3725)}")
    
    # Numbers
    print(f"\nUSD: {format_usd(1234567.89)}")
    print(f"Percent: {format_pct(15.5)}")
    
    # Addresses
    sol_addr = "EamKq5ZhE2eZP6Z2LgAps9RUeNTem8K2udSeYNWuCPKF"
    eth_addr = "0xd5950fbB8393C3C50FA31a71faabc73C4EB2E237"
    print(f"\nSolana: {shorten_address(sol_addr)} (valid: {validate_solana_address(sol_addr)})")
    print(f"ETH: {shorten_address(eth_addr)} (valid: {validate_eth_address(eth_addr)})")
    
    # Conversion
    print(f"\n1 SOL = {sol_to_lamports(Decimal('1'))} lamports")
    print(f"1B lamports = {lamports_to_sol(1_000_000_000)} SOL")
    
    # Colors
    print(f"\n{color_text('Success!', Colors.GREEN)}")
    log_info("This is info")
    log_success("This is success")
    log_warning("This is warning")
    log_error("This is error")
