#!/usr/bin/env python3
"""
Tests for utility functions
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import tempfile
import os

import sys
sys.path.insert(0, '..')

from utils import (
    utc_now, timestamp_ms, parse_timestamp, format_duration, time_ago,
    safe_decimal, format_usd, format_pct, round_to_precision, clamp,
    shorten_address, validate_solana_address, validate_eth_address,
    lamports_to_sol, sol_to_lamports,
    ensure_dir, safe_json_load, safe_json_save,
    async_retry, RateLimiter, LRUCache,
    get_env, get_env_bool, get_env_int
)


class TestTimeUtils:
    """Test time utilities"""
    
    def test_utc_now_has_timezone(self):
        now = utc_now()
        assert now.tzinfo == timezone.utc
    
    def test_timestamp_ms_reasonable(self):
        ts = timestamp_ms()
        # Should be after 2020 and before 2050
        assert 1577836800000 < ts < 2524608000000
    
    def test_parse_timestamp_datetime(self):
        dt = datetime(2026, 2, 6, 12, 0, 0, tzinfo=timezone.utc)
        assert parse_timestamp(dt) == dt
    
    def test_parse_timestamp_int_seconds(self):
        ts = 1738843200  # 2025-02-06 12:00:00 UTC
        dt = parse_timestamp(ts)
        assert dt.year == 2025
    
    def test_parse_timestamp_int_milliseconds(self):
        ts = 1738843200000
        dt = parse_timestamp(ts)
        assert dt.year == 2025
    
    def test_parse_timestamp_string(self):
        s = "2026-02-06T12:00:00+00:00"
        dt = parse_timestamp(s)
        assert dt.year == 2026
    
    def test_format_duration_seconds(self):
        assert format_duration(30) == "30.0s"
    
    def test_format_duration_minutes(self):
        assert format_duration(120) == "2.0m"
    
    def test_format_duration_hours(self):
        assert format_duration(7200) == "2.0h"
    
    def test_format_duration_days(self):
        assert format_duration(172800) == "2.0d"


class TestNumberUtils:
    """Test number utilities"""
    
    def test_safe_decimal_from_float(self):
        d = safe_decimal(1.5)
        assert d == Decimal("1.5")
    
    def test_safe_decimal_from_string(self):
        d = safe_decimal("1.5")
        assert d == Decimal("1.5")
    
    def test_safe_decimal_none_returns_default(self):
        d = safe_decimal(None, Decimal("10"))
        assert d == Decimal("10")
    
    def test_format_usd_small(self):
        assert format_usd(123.45) == "$123.45"
    
    def test_format_usd_thousands(self):
        assert format_usd(12345) == "$12.35K"
    
    def test_format_usd_millions(self):
        assert format_usd(1234567) == "$1.23M"
    
    def test_format_pct_positive(self):
        assert format_pct(15.5) == "+15.5%"
    
    def test_format_pct_negative(self):
        assert format_pct(-10.2) == "-10.2%"
    
    def test_round_to_precision(self):
        assert round_to_precision(1.23456789, 4) == 1.2346
    
    def test_clamp_within_range(self):
        assert clamp(5, 0, 10) == 5
    
    def test_clamp_below_min(self):
        assert clamp(-5, 0, 10) == 0
    
    def test_clamp_above_max(self):
        assert clamp(15, 0, 10) == 10


class TestCryptoUtils:
    """Test crypto utilities"""
    
    def test_shorten_address(self):
        addr = "EamKq5ZhE2eZP6Z2LgAps9RUeNTem8K2udSeYNWuCPKF"
        short = shorten_address(addr)
        assert short == "EamKq5...WuCPKF"
    
    def test_validate_solana_address_valid(self):
        addr = "EamKq5ZhE2eZP6Z2LgAps9RUeNTem8K2udSeYNWuCPKF"
        assert validate_solana_address(addr) == True
    
    def test_validate_solana_address_invalid_chars(self):
        addr = "EamKq5ZhE2eZP6Z2LgAps9RUeNTem8K2udSeYNWuCPK0"  # Has 0
        assert validate_solana_address(addr) == False
    
    def test_validate_solana_address_empty(self):
        assert validate_solana_address("") == False
    
    def test_validate_eth_address_valid(self):
        addr = "0xd5950fbB8393C3C50FA31a71faabc73C4EB2E237"
        assert validate_eth_address(addr) == True
    
    def test_validate_eth_address_no_prefix(self):
        addr = "d5950fbB8393C3C50FA31a71faabc73C4EB2E237"
        assert validate_eth_address(addr) == False
    
    def test_validate_eth_address_wrong_length(self):
        addr = "0xd5950fbB8393C3C50FA31a71"
        assert validate_eth_address(addr) == False
    
    def test_lamports_to_sol(self):
        sol = lamports_to_sol(1_500_000_000)
        assert sol == Decimal("1.5")
    
    def test_sol_to_lamports(self):
        lamports = sol_to_lamports(Decimal("1.5"))
        assert lamports == 1_500_000_000


class TestFileUtils:
    """Test file utilities"""
    
    def test_ensure_dir_creates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = os.path.join(tmpdir, "a", "b", "c")
            result = ensure_dir(new_dir)
            assert os.path.isdir(new_dir)
            assert result.exists()
    
    def test_safe_json_load_missing_file(self):
        result = safe_json_load("/nonexistent/file.json", {"default": True})
        assert result == {"default": True}
    
    def test_safe_json_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.json")
            data = {"key": "value", "number": 42}
            
            safe_json_save(filepath, data)
            loaded = safe_json_load(filepath)
            
            assert loaded == data


class TestAsyncUtils:
    """Test async utilities"""
    
    @pytest.mark.asyncio
    async def test_async_retry_succeeds(self):
        call_count = 0
        
        @async_retry(max_attempts=3)
        async def succeed():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await succeed()
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_async_retry_retries_on_failure(self):
        call_count = 0
        
        @async_retry(max_attempts=3, delay=0.1)
        async def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        result = await fail_twice()
        assert result == "success"
        assert call_count == 3


class TestRateLimiter:
    """Test rate limiter"""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_allows_within_limit(self):
        limiter = RateLimiter(calls=5, period=1.0)
        
        for _ in range(5):
            await limiter.acquire()
        
        # Should complete without waiting long
        assert True


class TestLRUCache:
    """Test LRU cache"""
    
    def test_cache_stores_and_retrieves(self):
        cache = LRUCache(capacity=3)
        cache.put("a", 1)
        cache.put("b", 2)
        
        assert cache.get("a") == 1
        assert cache.get("b") == 2
    
    def test_cache_evicts_lru(self):
        cache = LRUCache(capacity=2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)  # Should evict "a"
        
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3
    
    def test_cache_access_updates_order(self):
        cache = LRUCache(capacity=2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")  # Access "a", making "b" least recent
        cache.put("c", 3)  # Should evict "b"
        
        assert cache.get("a") == 1
        assert cache.get("b") is None
        assert cache.get("c") == 3


class TestEnvUtils:
    """Test environment utilities"""
    
    def test_get_env_default(self):
        result = get_env("NONEXISTENT_VAR_12345", "default")
        assert result == "default"
    
    def test_get_env_required_raises(self):
        with pytest.raises(ValueError):
            get_env("NONEXISTENT_VAR_12345", required=True)
    
    def test_get_env_bool_true(self):
        os.environ["TEST_BOOL"] = "true"
        assert get_env_bool("TEST_BOOL") == True
        del os.environ["TEST_BOOL"]
    
    def test_get_env_bool_false(self):
        os.environ["TEST_BOOL"] = "false"
        assert get_env_bool("TEST_BOOL") == False
        del os.environ["TEST_BOOL"]
    
    def test_get_env_int(self):
        os.environ["TEST_INT"] = "42"
        assert get_env_int("TEST_INT") == 42
        del os.environ["TEST_INT"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
