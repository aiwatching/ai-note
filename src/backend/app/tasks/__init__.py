"""
Task Management System

Provides automated task scheduling and execution for background jobs,
with focus on stock analysis scenarios.
"""
from .models import (
    Task,
    TaskExecution,
    TaskStatus,
    TaskSchedule,
    ActionType,
    ScheduleType,
    IntervalUnit,
    StockAlertConfig,
    StockAnalysisConfig,
    PortfolioMonitorConfig,
    NewsWatchConfig,
    CreateTaskRequest,
    TaskResponse,
    TaskExecutionResponse,
    TaskListResponse,
    ExecutionListResponse,
    LastExecutionInfo,
)
from .store import TaskStore
from .executor import TaskExecutor
from .scheduler import TaskScheduler
from .service import TaskService, get_task_service, init_task_service
from .actions import BaseAction, ActionResult, ActionRegistry

__all__ = [
    # Models
    "Task",
    "TaskExecution",
    "TaskStatus",
    "TaskSchedule",
    "ActionType",
    "ScheduleType",
    "IntervalUnit",
    # Config models
    "StockAlertConfig",
    "StockAnalysisConfig",
    "PortfolioMonitorConfig",
    "NewsWatchConfig",
    # Request/Response models
    "CreateTaskRequest",
    "TaskResponse",
    "TaskExecutionResponse",
    "TaskListResponse",
    "ExecutionListResponse",
    "LastExecutionInfo",
    # Store
    "TaskStore",
    # Executor and Scheduler
    "TaskExecutor",
    "TaskScheduler",
    # Service
    "TaskService",
    "get_task_service",
    "init_task_service",
    # Actions
    "BaseAction",
    "ActionResult",
    "ActionRegistry",
]
