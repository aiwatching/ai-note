"""
Task Executor

Handles the execution of tasks and manages execution lifecycle.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from .models import Task, TaskExecution, TaskStatus, ScheduleType
from .store import TaskStore
from .actions import ActionRegistry, ActionResult


logger = logging.getLogger(__name__)


class TaskExecutor:
    """
    Task executor that runs task actions.

    Manages task lifecycle:
    1. Create execution record
    2. Run action
    3. Update task status
    4. Store results
    5. Index to memory (optional)
    """

    def __init__(
        self,
        store: TaskStore,
        stock_service=None,
        notification_service=None,
        memory_index=None,
    ):
        self.store = store
        self.stock_service = stock_service
        self.notification_service = notification_service
        self.memory_index = memory_index
        self._running_tasks: dict[str, asyncio.Task] = {}

    async def execute(self, task: Task) -> TaskExecution:
        """
        Execute a task.

        Args:
            task: The task to execute

        Returns:
            TaskExecution record with results
        """
        logger.info(f"Executing task: {task.id} ({task.name})")

        # Create execution record
        execution = TaskExecution(task_id=task.id)
        self.store.create_execution(execution)

        # Update task status
        task.status = TaskStatus.RUNNING
        self.store.update_task(task)

        try:
            # Get action
            action = ActionRegistry.create(
                task.action_type,
                stock_service=self.stock_service,
                notification_service=self.notification_service,
                memory_index=self.memory_index,
            )

            if not action:
                raise ValueError(f"Unknown action type: {task.action_type}")

            # Validate config
            errors = action.validate_config(task.action_config)
            if errors:
                raise ValueError(f"Invalid config: {', '.join(errors)}")

            # Execute action
            result = await action.execute(task)

            # Complete execution
            execution.complete(
                success=result.success,
                result=result.data,
                error=result.message if not result.success else None,
            )

            # Index to memory if successful
            if result.success and result.data.get("memory_chunk_ids"):
                execution.indexed = True
                execution.memory_chunk_ids = result.data["memory_chunk_ids"]

            logger.info(f"Task {task.id} completed: success={result.success}")

        except Exception as e:
            logger.error(f"Task {task.id} failed: {e}")
            execution.complete(success=False, error=str(e))

        # Update execution record
        self.store.update_execution(execution)

        # Update task
        task.execution_count += 1
        task.last_executed_at = datetime.now()

        # Determine next status based on schedule type
        is_recurring = task.schedule.type in (ScheduleType.INTERVAL, ScheduleType.CRON)

        if is_recurring:
            # For recurring tasks, calculate next execution time
            next_time = self._calculate_next_execution(task)
            if next_time:
                task.next_execution_at = next_time
                task.status = TaskStatus.SCHEDULED
                logger.info(f"Recurring task {task.id} rescheduled for {next_time}")
            else:
                # Max executions reached or expired
                task.status = TaskStatus.COMPLETED
        else:
            # One-time task
            if execution.success:
                task.status = TaskStatus.COMPLETED
            else:
                task.status = TaskStatus.FAILED

        self.store.update_task(task)

        return execution

    def _calculate_next_execution(self, task: Task) -> Optional[datetime]:
        """Calculate next execution time for recurring tasks"""
        from datetime import timedelta

        schedule = task.schedule

        # Check if max executions reached
        if schedule.max_executions and task.execution_count >= schedule.max_executions:
            logger.info(f"Task {task.id} reached max executions ({schedule.max_executions})")
            return None

        # Check if expired
        if schedule.expires_at and datetime.now() >= schedule.expires_at:
            logger.info(f"Task {task.id} expired")
            return None

        if schedule.type == ScheduleType.INTERVAL:
            interval_seconds = schedule.get_interval_seconds()
            if interval_seconds:
                return datetime.now() + timedelta(seconds=interval_seconds)

        elif schedule.type == ScheduleType.CRON:
            # Simple implementation
            return datetime.now() + timedelta(hours=1)

        return None

    async def execute_async(self, task: Task) -> str:
        """
        Execute a task asynchronously (non-blocking).

        Args:
            task: The task to execute

        Returns:
            Task ID for tracking
        """
        async def run():
            try:
                await self.execute(task)
            finally:
                self._running_tasks.pop(task.id, None)

        async_task = asyncio.create_task(run())
        self._running_tasks[task.id] = async_task
        return task.id

    def is_running(self, task_id: str) -> bool:
        """Check if a task is currently running"""
        return task_id in self._running_tasks

    def get_running_tasks(self) -> list[str]:
        """Get list of running task IDs"""
        return list(self._running_tasks.keys())

    async def cancel(self, task_id: str) -> bool:
        """
        Cancel a running task.

        Args:
            task_id: ID of the task to cancel

        Returns:
            True if cancelled, False if not running
        """
        async_task = self._running_tasks.get(task_id)
        if async_task:
            async_task.cancel()
            try:
                await async_task
            except asyncio.CancelledError:
                pass
            self._running_tasks.pop(task_id, None)

            # Update task status
            task = self.store.get_task(task_id)
            if task:
                task.status = TaskStatus.CANCELLED
                self.store.update_task(task)

            return True
        return False

    async def shutdown(self):
        """Cancel all running tasks"""
        for task_id in list(self._running_tasks.keys()):
            await self.cancel(task_id)
