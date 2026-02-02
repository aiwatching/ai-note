"""
Task Management Data Models
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
import uuid


class ActionType(str, Enum):
    """Task action types"""
    STOCK_ALERT = "stock_alert"
    STOCK_ANALYSIS = "stock_analysis"
    PORTFOLIO_MONITOR = "portfolio_monitor"
    NEWS_WATCH = "news_watch"
    CUSTOM = "custom"


class TaskStatus(str, Enum):
    """Task status"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ScheduleType(str, Enum):
    """Schedule types"""
    ONCE = "once"
    INTERVAL = "interval"
    CRON = "cron"


class IntervalUnit(str, Enum):
    """Interval units"""
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"


class TaskSchedule(BaseModel):
    """Task schedule configuration"""
    type: ScheduleType = ScheduleType.ONCE
    scheduled_at: Optional[datetime] = None  # For once type
    interval_value: Optional[int] = None  # For interval type
    interval_unit: Optional[IntervalUnit] = None  # For interval type
    cron_expression: Optional[str] = None  # For cron type
    max_executions: Optional[int] = None  # Max execution count
    expires_at: Optional[datetime] = None  # Expiration time

    def get_interval_seconds(self) -> Optional[int]:
        """Get interval in seconds"""
        if self.type != ScheduleType.INTERVAL or not self.interval_value:
            return None

        multiplier = {
            IntervalUnit.MINUTES: 60,
            IntervalUnit.HOURS: 3600,
            IntervalUnit.DAYS: 86400,
        }
        return self.interval_value * multiplier.get(self.interval_unit, 60)


# ==================== Action Configs ====================

class StockAlertConfig(BaseModel):
    """Stock price alert configuration"""
    symbol: str
    condition: str  # above, below, change_pct_above, change_pct_below
    target_price: Optional[float] = None
    target_change_pct: Optional[float] = None
    notify_channels: List[str] = []  # telegram, discord, etc.


class StockAnalysisConfig(BaseModel):
    """Stock analysis configuration"""
    symbol: str
    analysis_types: List[str] = ["technical", "fundamental", "sentiment"]
    save_to_memory: bool = True
    notify_channels: List[str] = []


class PortfolioMonitorConfig(BaseModel):
    """Portfolio monitor configuration"""
    portfolio_name: str = "main"
    alert_on_change_pct: float = 5.0  # Alert when portfolio changes by this %
    notify_channels: List[str] = []


class NewsWatchConfig(BaseModel):
    """News watch configuration"""
    keywords: List[str] = []
    symbols: List[str] = []
    sentiment_filter: Optional[str] = None  # bullish, bearish, or None for all
    notify_channels: List[str] = []


# ==================== Task Model ====================

class Task(BaseModel):
    """Task definition"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    action_type: ActionType
    action_config: Dict[str, Any] = {}  # Action-specific config
    schedule: TaskSchedule = Field(default_factory=TaskSchedule)
    status: TaskStatus = TaskStatus.PENDING
    execution_count: int = 0
    last_executed_at: Optional[datetime] = None
    next_execution_at: Optional[datetime] = None
    tags: List[str] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def get_typed_config(self):
        """Get typed action config based on action_type"""
        config_map = {
            ActionType.STOCK_ALERT: StockAlertConfig,
            ActionType.STOCK_ANALYSIS: StockAnalysisConfig,
            ActionType.PORTFOLIO_MONITOR: PortfolioMonitorConfig,
            ActionType.NEWS_WATCH: NewsWatchConfig,
        }
        config_class = config_map.get(self.action_type)
        if config_class:
            return config_class(**self.action_config)
        return self.action_config


# ==================== Execution Model ====================

class TaskExecution(BaseModel):
    """Task execution record"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    success: bool = False
    result: Dict[str, Any] = {}  # Execution result data
    error: Optional[str] = None
    indexed: bool = False  # Whether indexed to memory
    memory_chunk_ids: List[str] = []  # Memory index chunk IDs

    def complete(self, success: bool, result: Dict[str, Any] = None, error: str = None):
        """Mark execution as complete"""
        self.completed_at = datetime.now()
        self.success = success
        if result:
            self.result = result
        if error:
            self.error = error
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.duration_ms = int(delta.total_seconds() * 1000)


# ==================== API Request/Response Models ====================

class CreateTaskRequest(BaseModel):
    """Request to create a task"""
    name: str
    description: str = ""
    action_type: ActionType
    action_config: Dict[str, Any] = {}
    schedule_type: ScheduleType = ScheduleType.ONCE
    scheduled_at: Optional[datetime] = None
    interval_value: Optional[int] = None
    interval_unit: Optional[IntervalUnit] = None
    cron_expression: Optional[str] = None
    max_executions: Optional[int] = None
    expires_at: Optional[datetime] = None
    tags: List[str] = []


class LastExecutionInfo(BaseModel):
    """Last execution summary"""
    success: bool
    executed_at: datetime
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    result_summary: Optional[str] = None  # Brief summary of result


class TaskResponse(BaseModel):
    """Task response"""
    id: str
    name: str
    description: str
    action_type: ActionType
    action_config: Dict[str, Any]
    schedule: TaskSchedule
    status: TaskStatus
    execution_count: int
    last_executed_at: Optional[datetime]
    next_execution_at: Optional[datetime]
    last_execution: Optional[LastExecutionInfo] = None  # Last execution info
    tags: List[str]
    created_at: datetime
    updated_at: datetime


class TaskExecutionResponse(BaseModel):
    """Task execution response"""
    id: str
    task_id: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_ms: Optional[int]
    success: bool
    result: Dict[str, Any]
    error: Optional[str]


class TaskListResponse(BaseModel):
    """List of tasks response"""
    tasks: List[TaskResponse]
    total: int


class ExecutionListResponse(BaseModel):
    """List of executions response"""
    executions: List[TaskExecutionResponse]
    total: int
