"""
Task Management API Endpoints

REST API for task management including creation, scheduling,
execution, and history queries.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..tasks import (
    TaskStatus, ActionType, ScheduleType, IntervalUnit,
    CreateTaskRequest, TaskResponse, TaskExecutionResponse,
    TaskListResponse, ExecutionListResponse, LastExecutionInfo,
    Task,
    get_task_service,
)


router = APIRouter(prefix="/tasks", tags=["tasks"])


# ==================== Request/Response Models ====================

class TriggerResponse(BaseModel):
    success: bool
    message: str


class StatsResponse(BaseModel):
    total_tasks: int
    pending_tasks: int
    scheduled_tasks: int
    running_tasks: int
    completed_tasks: int
    failed_tasks: int
    total_executions: int
    scheduler_running: bool
    action_types: List[str]


# ==================== Service Dependency ====================

def get_service():
    """Get task service instance"""
    return get_task_service()


def build_task_response(task: Task, service=None) -> TaskResponse:
    """Build TaskResponse with last execution info"""
    last_execution = None

    if task.execution_count > 0 and service:
        # Get last execution
        executions, _ = service.get_executions(task_id=task.id, limit=1)
        if executions:
            exec_record = executions[0]
            # Build result summary
            result_summary = None
            result = exec_record.result or {}

            if task.action_type.value == "stock_alert":
                if result.get("triggered"):
                    result_summary = f"🔔 已触发 ${result.get('current_price', 0):.2f}"
                else:
                    result_summary = f"⏳ 未触发 ${result.get('current_price', 0):.2f}"
            elif task.action_type.value == "stock_analysis":
                symbol = result.get("symbol", "")
                result_summary = f"📊 {symbol} 分析完成"
            elif task.action_type.value == "portfolio_monitor":
                total = result.get("total_value", 0)
                change = result.get("change_pct", 0)
                result_summary = f"💼 ${total:,.0f} ({change:+.1f}%)"
            elif task.action_type.value == "news_watch":
                count = result.get("news_count", 0)
                result_summary = f"📰 发现 {count} 条新闻"

            last_execution = LastExecutionInfo(
                success=exec_record.success,
                executed_at=exec_record.started_at,
                duration_ms=exec_record.duration_ms,
                error=exec_record.error,
                result_summary=result_summary,
            )

    return TaskResponse(
        id=task.id,
        name=task.name,
        description=task.description,
        action_type=task.action_type,
        action_config=task.action_config,
        schedule=task.schedule,
        status=task.status,
        execution_count=task.execution_count,
        last_executed_at=task.last_executed_at,
        next_execution_at=task.next_execution_at,
        last_execution=last_execution,
        tags=task.tags,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


# ==================== Task CRUD ====================

@router.post("", response_model=TaskResponse)
async def create_task(request: CreateTaskRequest):
    """Create a new task"""
    service = get_service()
    try:
        task = service.create_task(request)
        return build_task_response(task, service)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[TaskStatus] = None,
    action_type: Optional[ActionType] = None,
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """List tasks with optional filters"""
    service = get_service()

    tag_list = tags.split(",") if tags else None

    tasks, total = service.list_tasks(
        status=status,
        action_type=action_type,
        tags=tag_list,
        limit=limit,
        offset=offset,
    )

    return TaskListResponse(
        tasks=[build_task_response(t, service) for t in tasks],
        total=total,
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get task system statistics"""
    service = get_service()
    stats = service.get_stats()
    return StatsResponse(**stats)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """Get a task by ID"""
    service = get_service()
    task = service.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return build_task_response(task, service)


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """Delete a task"""
    service = get_service()
    if not service.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True, "message": f"Task {task_id} deleted"}


# ==================== Task Control ====================

@router.post("/{task_id}/trigger", response_model=TriggerResponse)
async def trigger_task(task_id: str):
    """Manually trigger a task execution"""
    service = get_service()

    task = service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    success = await service.trigger(task_id)
    if not success:
        raise HTTPException(status_code=400, detail="Task is already running")

    return TriggerResponse(success=True, message=f"Task {task_id} triggered")


@router.post("/{task_id}/pause", response_model=TriggerResponse)
async def pause_task(task_id: str):
    """Pause a scheduled task"""
    service = get_service()

    if not service.pause(task_id):
        raise HTTPException(status_code=404, detail="Task not found")

    return TriggerResponse(success=True, message=f"Task {task_id} paused")


@router.post("/{task_id}/resume", response_model=TriggerResponse)
async def resume_task(task_id: str):
    """Resume a paused task"""
    service = get_service()

    if not service.resume(task_id):
        raise HTTPException(status_code=400, detail="Task not found or not paused")

    return TriggerResponse(success=True, message=f"Task {task_id} resumed")


@router.post("/{task_id}/cancel", response_model=TriggerResponse)
async def cancel_task(task_id: str):
    """Cancel a running or scheduled task"""
    service = get_service()

    if not await service.cancel(task_id):
        raise HTTPException(status_code=404, detail="Task not found")

    return TriggerResponse(success=True, message=f"Task {task_id} cancelled")


# ==================== Execution History ====================

@router.get("/{task_id}/executions", response_model=ExecutionListResponse)
async def get_task_executions(
    task_id: str,
    success: Optional[bool] = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """Get execution history for a task"""
    service = get_service()

    task = service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    executions, total = service.get_executions(
        task_id=task_id,
        success=success,
        limit=limit,
        offset=offset,
    )

    return ExecutionListResponse(
        executions=[
            TaskExecutionResponse(
                id=e.id,
                task_id=e.task_id,
                started_at=e.started_at,
                completed_at=e.completed_at,
                duration_ms=e.duration_ms,
                success=e.success,
                result=e.result,
                error=e.error,
            )
            for e in executions
        ],
        total=total,
    )


@router.get("/search/results")
async def search_results(
    q: str = Query(..., min_length=1, description="Search query"),
    task_id: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100),
):
    """Search execution results by keyword"""
    service = get_service()

    executions = service.search_results(q, task_id, limit)

    return {
        "query": q,
        "results": [
            {
                "execution_id": e.id,
                "task_id": e.task_id,
                "started_at": e.started_at.isoformat(),
                "success": e.success,
                "result": e.result,
            }
            for e in executions
        ],
    }


# ==================== Scheduler Control ====================

@router.post("/scheduler/start", response_model=TriggerResponse)
async def start_scheduler():
    """Start the task scheduler"""
    service = get_service()
    service.start_scheduler()
    return TriggerResponse(success=True, message="Scheduler started")


@router.post("/scheduler/stop", response_model=TriggerResponse)
async def stop_scheduler():
    """Stop the task scheduler"""
    service = get_service()
    await service.stop_scheduler()
    return TriggerResponse(success=True, message="Scheduler stopped")
