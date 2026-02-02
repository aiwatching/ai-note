"""
Task Service

High-level service API for task management.
"""
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from .models import (
    Task, TaskExecution, TaskStatus, TaskSchedule, ActionType,
    ScheduleType, IntervalUnit, CreateTaskRequest
)
from .store import TaskStore
from .executor import TaskExecutor
from .scheduler import TaskScheduler
from .actions import ActionRegistry


logger = logging.getLogger(__name__)


class TaskService:
    """
    Task management service.

    Provides high-level API for:
    - Creating and managing tasks
    - Scheduling tasks
    - Querying execution history
    - Searching results
    """

    def __init__(
        self,
        db_path: str = "./data/tasks.db",
        stock_service=None,
        notification_service=None,
        memory_index=None,
        scheduler_interval: int = 60,
    ):
        self.store = TaskStore(db_path)
        self.executor = TaskExecutor(
            store=self.store,
            stock_service=stock_service,
            notification_service=notification_service,
            memory_index=memory_index,
        )
        self.scheduler = TaskScheduler(
            store=self.store,
            executor=self.executor,
            check_interval=scheduler_interval,
        )

        # Store references for later updates
        self._stock_service = stock_service
        self._notification_service = notification_service
        self._memory_index = memory_index

    def update_services(
        self,
        stock_service=None,
        notification_service=None,
        memory_index=None,
    ):
        """Update service dependencies"""
        if stock_service:
            self._stock_service = stock_service
            self.executor.stock_service = stock_service
        if notification_service:
            self._notification_service = notification_service
            self.executor.notification_service = notification_service
        if memory_index:
            self._memory_index = memory_index
            self.executor.memory_index = memory_index

    # ==================== Task Management ====================

    def create_task(self, request: CreateTaskRequest) -> Task:
        """
        Create a new task.

        Args:
            request: Task creation request

        Returns:
            Created task
        """
        # Build schedule
        schedule = TaskSchedule(
            type=request.schedule_type,
            scheduled_at=request.scheduled_at,
            interval_value=request.interval_value,
            interval_unit=request.interval_unit,
            cron_expression=request.cron_expression,
            max_executions=request.max_executions,
            expires_at=request.expires_at,
        )

        # Create task
        task = Task(
            name=request.name,
            description=request.description,
            action_type=request.action_type,
            action_config=request.action_config,
            schedule=schedule,
            tags=request.tags,
        )

        # Validate action config
        action = ActionRegistry.create(
            task.action_type,
            stock_service=self._stock_service,
            notification_service=self._notification_service,
        )
        if action:
            errors = action.validate_config(task.action_config)
            if errors:
                raise ValueError(f"Invalid action config: {', '.join(errors)}")

        # Save task
        self.store.create_task(task)

        # Schedule if needed
        if request.schedule_type != ScheduleType.ONCE or request.scheduled_at:
            self.scheduler.schedule(task)

        logger.info(f"Created task: {task.id} ({task.name})")
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID"""
        return self.store.get_task(task_id)

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        action_type: Optional[ActionType] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[Task], int]:
        """
        List tasks with optional filters.

        Returns:
            Tuple of (tasks, total_count)
        """
        tasks = self.store.list_tasks(
            status=status,
            action_type=action_type,
            tags=tags,
            limit=limit,
            offset=offset,
        )
        total = self.store.count_tasks(status=status, action_type=action_type)
        return tasks, total

    def delete_task(self, task_id: str) -> bool:
        """Delete a task"""
        # Cancel if running
        if self.executor.is_running(task_id):
            import asyncio
            asyncio.create_task(self.executor.cancel(task_id))

        return self.store.delete_task(task_id)

    def update_task(
        self,
        task_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        action_config: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[Task]:
        """Update task properties"""
        task = self.store.get_task(task_id)
        if not task:
            return None

        if name:
            task.name = name
        if description is not None:
            task.description = description
        if action_config:
            task.action_config = action_config
        if tags is not None:
            task.tags = tags

        return self.store.update_task(task)

    # ==================== Task Control ====================

    async def trigger(self, task_id: str) -> bool:
        """Manually trigger a task"""
        return await self.scheduler.trigger(task_id)

    def pause(self, task_id: str) -> bool:
        """Pause a scheduled task"""
        return self.scheduler.pause(task_id)

    def resume(self, task_id: str) -> bool:
        """Resume a paused task"""
        return self.scheduler.resume(task_id)

    async def cancel(self, task_id: str) -> bool:
        """Cancel a running task"""
        task = self.store.get_task(task_id)
        if not task:
            return False

        if self.executor.is_running(task_id):
            await self.executor.cancel(task_id)
        else:
            task.status = TaskStatus.CANCELLED
            self.store.update_task(task)

        return True

    # ==================== Execution History ====================

    def get_executions(
        self,
        task_id: Optional[str] = None,
        success: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[TaskExecution], int]:
        """
        Get execution history.

        Returns:
            Tuple of (executions, total_count)
        """
        executions = self.store.list_executions(
            task_id=task_id,
            success=success,
            limit=limit,
            offset=offset,
        )
        total = self.store.count_executions(task_id=task_id)
        return executions, total

    def get_execution(self, execution_id: str) -> Optional[TaskExecution]:
        """Get a specific execution"""
        return self.store.get_execution(execution_id)

    def search_results(
        self,
        query: str,
        task_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[TaskExecution]:
        """Search execution results"""
        return self.store.search_execution_results(query, task_id, limit)

    # ==================== Scheduler Control ====================

    def start_scheduler(self):
        """Start the task scheduler"""
        self.scheduler.start()

    async def stop_scheduler(self):
        """Stop the task scheduler"""
        await self.scheduler.stop()

    def is_scheduler_running(self) -> bool:
        """Check if scheduler is running"""
        return self.scheduler.is_running()

    # ==================== Stats ====================

    def get_stats(self) -> Dict[str, Any]:
        """Get task system statistics"""
        return {
            "total_tasks": self.store.count_tasks(),
            "pending_tasks": self.store.count_tasks(status=TaskStatus.PENDING),
            "scheduled_tasks": self.store.count_tasks(status=TaskStatus.SCHEDULED),
            "running_tasks": len(self.executor.get_running_tasks()),
            "completed_tasks": self.store.count_tasks(status=TaskStatus.COMPLETED),
            "failed_tasks": self.store.count_tasks(status=TaskStatus.FAILED),
            "total_executions": self.store.count_executions(),
            "scheduler_running": self.scheduler.is_running(),
            "action_types": [t.value for t in ActionRegistry.list_types()],
        }


# Global task service instance
_task_service: Optional[TaskService] = None


def get_task_service() -> TaskService:
    """Get or create the global task service instance"""
    global _task_service
    if _task_service is None:
        _task_service = TaskService()
    return _task_service


def init_task_service(
    db_path: str = "./data/tasks.db",
    stock_service=None,
    notification_service=None,
    memory_index=None,
) -> TaskService:
    """Initialize the global task service with dependencies"""
    global _task_service
    _task_service = TaskService(
        db_path=db_path,
        stock_service=stock_service,
        notification_service=notification_service,
        memory_index=memory_index,
    )
    return _task_service
