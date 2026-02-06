#!/usr/bin/env python3
"""
FRED-SOL: Task Scheduler
Schedule and manage trading operations

Built: 2026-02-06 07:40 CST by Ricky
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Any, Coroutine
from pathlib import Path
from enum import Enum
import heapq


class TaskPriority(Enum):
    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(order=True)
class ScheduledTask:
    """Task scheduled for execution"""
    priority: int
    scheduled_time: datetime = field(compare=True)
    task_id: str = field(compare=False)
    name: str = field(compare=False)
    callback: Optional[Callable] = field(compare=False, default=None)
    args: tuple = field(compare=False, default_factory=tuple)
    kwargs: dict = field(compare=False, default_factory=dict)
    interval: Optional[timedelta] = field(compare=False, default=None)
    max_retries: int = field(compare=False, default=3)
    retry_count: int = field(compare=False, default=0)
    status: TaskStatus = field(compare=False, default=TaskStatus.PENDING)
    result: Any = field(compare=False, default=None)
    error: Optional[str] = field(compare=False, default=None)
    created_at: datetime = field(compare=False, default_factory=lambda: datetime.now(timezone.utc))


class Scheduler:
    """
    Async task scheduler for FRED operations
    
    Features:
    - Priority-based execution
    - Recurring tasks with intervals
    - Retry logic with backoff
    - Task history and metrics
    """
    
    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self.tasks: Dict[str, ScheduledTask] = {}
        self.task_queue: List[ScheduledTask] = []
        self.running_count = 0
        self.history: List[Dict] = []
        self.running = False
        self._task_counter = 0
    
    def _generate_id(self) -> str:
        """Generate unique task ID"""
        self._task_counter += 1
        return f"task_{self._task_counter:06d}"
    
    def schedule(
        self,
        callback: Callable,
        name: str = "task",
        delay: Optional[timedelta] = None,
        at: Optional[datetime] = None,
        interval: Optional[timedelta] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        args: tuple = (),
        kwargs: dict = None,
        max_retries: int = 3
    ) -> str:
        """
        Schedule a task for execution
        
        Args:
            callback: Function to execute (sync or async)
            name: Task name for logging
            delay: Run after this delay
            at: Run at specific time
            interval: Repeat at this interval
            priority: Task priority
            args: Positional arguments for callback
            kwargs: Keyword arguments for callback
            max_retries: Max retry attempts on failure
            
        Returns:
            Task ID
        """
        task_id = self._generate_id()
        
        if at:
            scheduled_time = at
        elif delay:
            scheduled_time = datetime.now(timezone.utc) + delay
        else:
            scheduled_time = datetime.now(timezone.utc)
        
        task = ScheduledTask(
            priority=priority.value,
            scheduled_time=scheduled_time,
            task_id=task_id,
            name=name,
            callback=callback,
            args=args,
            kwargs=kwargs or {},
            interval=interval,
            max_retries=max_retries
        )
        
        self.tasks[task_id] = task
        heapq.heappush(self.task_queue, task)
        
        return task_id
    
    def schedule_recurring(
        self,
        callback: Callable,
        interval: timedelta,
        name: str = "recurring_task",
        priority: TaskPriority = TaskPriority.NORMAL,
        start_immediately: bool = True,
        **kwargs
    ) -> str:
        """Schedule a recurring task"""
        delay = None if start_immediately else interval
        return self.schedule(
            callback=callback,
            name=name,
            delay=delay,
            interval=interval,
            priority=priority,
            **kwargs
        )
    
    def cancel(self, task_id: str) -> bool:
        """Cancel a scheduled task"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                return True
        return False
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get task by ID"""
        return self.tasks.get(task_id)
    
    def get_pending(self) -> List[ScheduledTask]:
        """Get all pending tasks"""
        return [t for t in self.tasks.values() if t.status == TaskStatus.PENDING]
    
    async def _execute_task(self, task: ScheduledTask):
        """Execute a single task"""
        task.status = TaskStatus.RUNNING
        self.running_count += 1
        
        try:
            if asyncio.iscoroutinefunction(task.callback):
                result = await task.callback(*task.args, **task.kwargs)
            else:
                result = task.callback(*task.args, **task.kwargs)
            
            task.result = result
            task.status = TaskStatus.COMPLETED
            
            self._record_history(task, success=True)
            
            # Reschedule if recurring
            if task.interval:
                self._reschedule_recurring(task)
                
        except Exception as e:
            task.error = str(e)
            task.retry_count += 1
            
            if task.retry_count < task.max_retries:
                # Retry with exponential backoff
                backoff = timedelta(seconds=2 ** task.retry_count)
                task.scheduled_time = datetime.now(timezone.utc) + backoff
                task.status = TaskStatus.PENDING
                heapq.heappush(self.task_queue, task)
            else:
                task.status = TaskStatus.FAILED
                self._record_history(task, success=False)
        
        finally:
            self.running_count -= 1
    
    def _reschedule_recurring(self, task: ScheduledTask):
        """Reschedule a recurring task"""
        new_task = ScheduledTask(
            priority=task.priority,
            scheduled_time=datetime.now(timezone.utc) + task.interval,
            task_id=self._generate_id(),
            name=task.name,
            callback=task.callback,
            args=task.args,
            kwargs=task.kwargs,
            interval=task.interval,
            max_retries=task.max_retries
        )
        
        self.tasks[new_task.task_id] = new_task
        heapq.heappush(self.task_queue, new_task)
    
    def _record_history(self, task: ScheduledTask, success: bool):
        """Record task execution in history"""
        self.history.append({
            "task_id": task.task_id,
            "name": task.name,
            "scheduled": task.scheduled_time.isoformat(),
            "completed": datetime.now(timezone.utc).isoformat(),
            "success": success,
            "retries": task.retry_count,
            "error": task.error
        })
        
        # Trim history
        if len(self.history) > 1000:
            self.history = self.history[-500:]
    
    async def run(self, duration: Optional[float] = None):
        """
        Run the scheduler
        
        Args:
            duration: Run for this many seconds, or indefinitely if None
        """
        self.running = True
        start_time = datetime.now()
        
        try:
            while self.running:
                now = datetime.now(timezone.utc)
                
                # Process due tasks
                while (self.task_queue and 
                       self.running_count < self.max_concurrent):
                    
                    # Peek at next task
                    next_task = self.task_queue[0]
                    
                    if next_task.scheduled_time > now:
                        break
                    
                    if next_task.status == TaskStatus.CANCELLED:
                        heapq.heappop(self.task_queue)
                        continue
                    
                    # Pop and execute
                    task = heapq.heappop(self.task_queue)
                    asyncio.create_task(self._execute_task(task))
                
                # Check duration
                if duration:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    if elapsed >= duration:
                        break
                
                await asyncio.sleep(0.1)
                
        except asyncio.CancelledError:
            self.running = False
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics"""
        completed = [h for h in self.history if h["success"]]
        failed = [h for h in self.history if not h["success"]]
        
        return {
            "total_tasks": len(self.tasks),
            "pending": len(self.get_pending()),
            "running": self.running_count,
            "completed": len(completed),
            "failed": len(failed),
            "success_rate": len(completed) / len(self.history) * 100 if self.history else 0,
            "queue_depth": len(self.task_queue)
        }
    
    def get_summary(self) -> str:
        """Get formatted summary"""
        stats = self.get_stats()
        
        return f"""
╔════════════════════════════════════╗
║     FRED-SOL Scheduler Status      ║
╠════════════════════════════════════╣
║ Total Tasks:   {stats['total_tasks']:>6}             ║
║ Pending:       {stats['pending']:>6}             ║
║ Running:       {stats['running']:>6}             ║
║ Completed:     {stats['completed']:>6}             ║
║ Failed:        {stats['failed']:>6}             ║
║ Success Rate:  {stats['success_rate']:>5.1f}%            ║
╚════════════════════════════════════╝
        """.strip()


# Example task functions
async def scan_markets():
    """Example: Scan markets for opportunities"""
    await asyncio.sleep(0.5)  # Simulate work
    return {"markets_scanned": 10}


async def check_positions():
    """Example: Check open positions"""
    await asyncio.sleep(0.3)
    return {"positions": 3}


async def main():
    """Demo the scheduler"""
    scheduler = Scheduler(max_concurrent=3)
    
    # Schedule one-time task
    scheduler.schedule(
        scan_markets,
        name="market_scan",
        delay=timedelta(seconds=1),
        priority=TaskPriority.HIGH
    )
    
    # Schedule recurring task
    scheduler.schedule_recurring(
        check_positions,
        interval=timedelta(seconds=5),
        name="position_check"
    )
    
    print("Starting scheduler...")
    print(scheduler.get_summary())
    
    # Run for 15 seconds
    await scheduler.run(duration=15)
    
    print("\nFinal stats:")
    print(scheduler.get_summary())
    
    print("\nRecent history:")
    for h in scheduler.history[-5:]:
        status = "✅" if h["success"] else "❌"
        print(f"  {status} {h['name']} @ {h['completed']}")


if __name__ == "__main__":
    asyncio.run(main())
