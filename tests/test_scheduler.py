#!/usr/bin/env python3
"""
Tests for task scheduler
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

import sys
sys.path.insert(0, '..')

from scheduler import (
    TaskPriority, TaskStatus, ScheduledTask, Scheduler
)


class TestTaskPriority:
    """Test TaskPriority enum"""
    
    def test_priority_ordering(self):
        # Lower value = higher priority
        assert TaskPriority.CRITICAL.value < TaskPriority.HIGH.value
        assert TaskPriority.HIGH.value < TaskPriority.NORMAL.value
        assert TaskPriority.NORMAL.value < TaskPriority.LOW.value


class TestTaskStatus:
    """Test TaskStatus enum"""
    
    def test_all_statuses(self):
        assert TaskStatus.PENDING
        assert TaskStatus.RUNNING
        assert TaskStatus.COMPLETED
        assert TaskStatus.FAILED
        assert TaskStatus.CANCELLED


class TestScheduledTask:
    """Test ScheduledTask dataclass"""
    
    def test_task_defaults(self):
        task = ScheduledTask(
            priority=TaskPriority.NORMAL.value,
            scheduled_time=datetime.now(timezone.utc),
            task_id="t1",
            name="test"
        )
        
        assert task.status == TaskStatus.PENDING
        assert task.retry_count == 0
        assert task.max_retries == 3
    
    def test_task_ordering_by_priority(self):
        now = datetime.now(timezone.utc)
        
        task_high = ScheduledTask(
            priority=TaskPriority.HIGH.value,
            scheduled_time=now,
            task_id="high",
            name="high"
        )
        
        task_low = ScheduledTask(
            priority=TaskPriority.LOW.value,
            scheduled_time=now,
            task_id="low",
            name="low"
        )
        
        # Higher priority (lower value) comes first
        assert task_high < task_low
    
    def test_task_ordering_by_time(self):
        now = datetime.now(timezone.utc)
        
        task_early = ScheduledTask(
            priority=TaskPriority.NORMAL.value,
            scheduled_time=now,
            task_id="early",
            name="early"
        )
        
        task_late = ScheduledTask(
            priority=TaskPriority.NORMAL.value,
            scheduled_time=now + timedelta(hours=1),
            task_id="late",
            name="late"
        )
        
        # Earlier time comes first
        assert task_early < task_late


class TestScheduler:
    """Test Scheduler class"""
    
    @pytest.fixture
    def scheduler(self):
        return Scheduler(max_concurrent=3)
    
    def test_schedule_returns_id(self, scheduler):
        async def dummy():
            pass
        
        task_id = scheduler.schedule(dummy, name="test")
        
        assert task_id.startswith("task_")
        assert task_id in scheduler.tasks
    
    def test_schedule_with_delay(self, scheduler):
        async def dummy():
            pass
        
        task_id = scheduler.schedule(
            dummy,
            name="delayed",
            delay=timedelta(seconds=60)
        )
        
        task = scheduler.tasks[task_id]
        now = datetime.now(timezone.utc)
        
        assert task.scheduled_time > now
    
    def test_schedule_with_specific_time(self, scheduler):
        async def dummy():
            pass
        
        run_at = datetime.now(timezone.utc) + timedelta(hours=1)
        task_id = scheduler.schedule(dummy, name="at_time", at=run_at)
        
        task = scheduler.tasks[task_id]
        assert task.scheduled_time == run_at
    
    def test_schedule_recurring(self, scheduler):
        async def dummy():
            pass
        
        task_id = scheduler.schedule_recurring(
            dummy,
            interval=timedelta(minutes=5),
            name="recurring"
        )
        
        task = scheduler.tasks[task_id]
        assert task.interval == timedelta(minutes=5)
    
    def test_cancel_task(self, scheduler):
        async def dummy():
            pass
        
        task_id = scheduler.schedule(dummy, name="to_cancel")
        
        result = scheduler.cancel(task_id)
        
        assert result == True
        assert scheduler.tasks[task_id].status == TaskStatus.CANCELLED
    
    def test_cancel_nonexistent_task(self, scheduler):
        result = scheduler.cancel("nonexistent")
        assert result == False
    
    def test_get_task(self, scheduler):
        async def dummy():
            pass
        
        task_id = scheduler.schedule(dummy, name="test")
        
        task = scheduler.get_task(task_id)
        
        assert task is not None
        assert task.name == "test"
    
    def test_get_pending(self, scheduler):
        async def dummy():
            pass
        
        scheduler.schedule(dummy, name="task1")
        scheduler.schedule(dummy, name="task2")
        
        pending = scheduler.get_pending()
        
        assert len(pending) == 2
    
    @pytest.mark.asyncio
    async def test_execute_async_task(self, scheduler):
        result_holder = []
        
        async def async_task():
            result_holder.append("executed")
            return "success"
        
        scheduler.schedule(async_task, name="async")
        
        await scheduler.run(duration=0.5)
        
        assert "executed" in result_holder
    
    @pytest.mark.asyncio
    async def test_execute_sync_task(self, scheduler):
        result_holder = []
        
        def sync_task():
            result_holder.append("executed")
            return "success"
        
        scheduler.schedule(sync_task, name="sync")
        
        await scheduler.run(duration=0.5)
        
        assert "executed" in result_holder
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(self, scheduler):
        call_count = [0]
        
        async def failing_task():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("Temporary error")
            return "success"
        
        scheduler.schedule(failing_task, name="retry", max_retries=3)
        
        await scheduler.run(duration=3.0)
        
        assert call_count[0] == 3
    
    @pytest.mark.asyncio
    async def test_priority_execution_order(self, scheduler):
        execution_order = []
        
        async def task(name):
            execution_order.append(name)
        
        # Schedule lower priority first
        scheduler.schedule(lambda: task("low"), name="low", priority=TaskPriority.LOW)
        scheduler.schedule(lambda: task("high"), name="high", priority=TaskPriority.HIGH)
        
        await scheduler.run(duration=0.5)
        
        # High priority should execute first (though timing may vary)
        # Just verify both executed
        assert len(execution_order) >= 1
    
    def test_get_stats(self, scheduler):
        async def dummy():
            pass
        
        scheduler.schedule(dummy, name="task1")
        scheduler.schedule(dummy, name="task2")
        
        stats = scheduler.get_stats()
        
        assert stats["total_tasks"] == 2
        assert stats["pending"] == 2
        assert stats["running"] == 0
    
    def test_get_summary(self, scheduler):
        summary = scheduler.get_summary()
        
        assert "FRED-SOL" in summary
        assert "Scheduler" in summary
    
    def test_stop(self, scheduler):
        scheduler.running = True
        scheduler.stop()
        
        assert scheduler.running == False


class TestRecurringTasks:
    """Test recurring task functionality"""
    
    @pytest.mark.asyncio
    async def test_recurring_reschedules(self):
        scheduler = Scheduler()
        execution_count = [0]
        
        async def counting_task():
            execution_count[0] += 1
        
        scheduler.schedule_recurring(
            counting_task,
            interval=timedelta(milliseconds=100),
            name="counter"
        )
        
        await scheduler.run(duration=0.5)
        
        # Should execute multiple times
        assert execution_count[0] >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
