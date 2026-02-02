"""
Task Scheduler

Manages task scheduling and triggers execution at appropriate times.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable

from .models import Task, TaskStatus, ScheduleType
from .store import TaskStore
from .executor import TaskExecutor


logger = logging.getLogger(__name__)


class TaskScheduler:
    """
    Task scheduler that manages task timing.

    Features:
    - Schedule tasks for one-time or recurring execution
    - Calculate next execution times
    - Run check loop to trigger due tasks
    """

    def __init__(
        self,
        store: TaskStore,
        executor: TaskExecutor,
        check_interval: int = 60,  # seconds
    ):
        self.store = store
        self.executor = executor
        self.check_interval = check_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def schedule(self, task: Task) -> Task:
        """
        Schedule a task for execution.

        Calculates and sets the next_execution_at based on schedule config.

        Args:
            task: The task to schedule

        Returns:
            Updated task with schedule info
        """
        schedule = task.schedule

        if schedule.type == ScheduleType.ONCE:
            if schedule.scheduled_at:
                task.next_execution_at = schedule.scheduled_at
            else:
                task.next_execution_at = datetime.now()

        elif schedule.type == ScheduleType.INTERVAL:
            interval_seconds = schedule.get_interval_seconds()
            if interval_seconds:
                task.next_execution_at = datetime.now() + timedelta(seconds=interval_seconds)
            else:
                task.next_execution_at = datetime.now()

        elif schedule.type == ScheduleType.CRON:
            # Simple cron support - for now just use interval
            # Full cron parsing would require croniter library
            task.next_execution_at = datetime.now() + timedelta(hours=1)
            logger.warning("Full cron support not yet implemented, using 1 hour interval")

        task.status = TaskStatus.SCHEDULED
        self.store.update_task(task)

        logger.info(f"Scheduled task {task.id} for {task.next_execution_at}")
        return task

    def calculate_next_execution(self, task: Task) -> Optional[datetime]:
        """
        Calculate the next execution time for a recurring task.

        Args:
            task: The task to calculate for

        Returns:
            Next execution datetime or None if task should not repeat
        """
        schedule = task.schedule

        # Check if max executions reached
        if schedule.max_executions and task.execution_count >= schedule.max_executions:
            logger.info(f"Task {task.id} reached max executions ({schedule.max_executions})")
            return None

        # Check if expired
        if schedule.expires_at and datetime.now() >= schedule.expires_at:
            logger.info(f"Task {task.id} expired at {schedule.expires_at}")
            return None

        if schedule.type == ScheduleType.ONCE:
            # One-time tasks don't repeat
            return None

        elif schedule.type == ScheduleType.INTERVAL:
            interval_seconds = schedule.get_interval_seconds()
            if interval_seconds:
                return datetime.now() + timedelta(seconds=interval_seconds)

        elif schedule.type == ScheduleType.CRON:
            # Simple implementation - use interval for now
            return datetime.now() + timedelta(hours=1)

        return None

    async def check_and_execute(self):
        """Check for due tasks and execute them"""
        due_tasks = self.store.get_due_tasks()

        for task in due_tasks:
            if self.executor.is_running(task.id):
                logger.debug(f"Task {task.id} already running, skipping")
                continue

            logger.info(f"Triggering due task: {task.id} ({task.name})")

            # Execute task
            await self.executor.execute_async(task)

            # Calculate next execution for recurring tasks
            next_time = self.calculate_next_execution(task)
            if next_time:
                # Refresh task from store (may have been updated)
                task = self.store.get_task(task.id)
                if task:
                    task.next_execution_at = next_time
                    task.status = TaskStatus.SCHEDULED
                    self.store.update_task(task)
                    logger.info(f"Task {task.id} rescheduled for {next_time}")

    async def _run_loop(self):
        """Main scheduler loop"""
        logger.info("Task scheduler started")

        while self._running:
            try:
                await self.check_and_execute()
            except Exception as e:
                logger.error(f"Scheduler check error: {e}")

            await asyncio.sleep(self.check_interval)

        logger.info("Task scheduler stopped")

    def start(self):
        """Start the scheduler"""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Task scheduler starting...")

    async def stop(self):
        """Stop the scheduler"""
        if not self._running:
            return

        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        # Shutdown executor
        await self.executor.shutdown()

        logger.info("Task scheduler stopped")

    def is_running(self) -> bool:
        """Check if scheduler is running"""
        return self._running

    async def trigger(self, task_id: str) -> bool:
        """
        Manually trigger a task execution.

        Args:
            task_id: ID of the task to trigger

        Returns:
            True if triggered, False if task not found or already running
        """
        task = self.store.get_task(task_id)
        if not task:
            return False

        if self.executor.is_running(task_id):
            return False

        await self.executor.execute_async(task)
        return True

    def pause(self, task_id: str) -> bool:
        """
        Pause a scheduled task.

        Args:
            task_id: ID of the task to pause

        Returns:
            True if paused
        """
        task = self.store.get_task(task_id)
        if not task:
            return False

        task.status = TaskStatus.PAUSED
        self.store.update_task(task)
        return True

    def resume(self, task_id: str) -> bool:
        """
        Resume a paused or cancelled task.

        Args:
            task_id: ID of the task to resume

        Returns:
            True if resumed
        """
        task = self.store.get_task(task_id)
        if not task:
            return False

        # Can resume from paused, cancelled, completed, or failed status
        resumable_statuses = {
            TaskStatus.PAUSED,
            TaskStatus.CANCELLED,
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
        }

        if task.status not in resumable_statuses:
            return False

        # Recalculate next execution and set to scheduled
        self.schedule(task)
        return True
