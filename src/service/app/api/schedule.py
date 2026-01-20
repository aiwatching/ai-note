"""Schedule API endpoints."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.schedule_schema import (
    ScheduleCreate,
    ScheduleListResponse,
    ScheduleResponse,
    ScheduleStatusUpdate,
    ScheduleUpdate,
)
from ..services.schedule_service import ScheduleService

router = APIRouter(prefix="/schedules", tags=["schedules"])

# Default user ID for MVP (simplified authentication)
DEFAULT_USER_ID = 1


@router.post("", response_model=ScheduleResponse)
async def create_schedule(
    data: ScheduleCreate,
    db: Session = Depends(get_db),
) -> ScheduleResponse:
    """Create a new schedule."""
    service = ScheduleService(db)
    schedule = service.create_schedule(DEFAULT_USER_ID, data)
    return ScheduleResponse.model_validate(schedule)


@router.get("", response_model=ScheduleListResponse)
async def list_schedules(
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
) -> ScheduleListResponse:
    """List schedules with optional filters."""
    service = ScheduleService(db)
    skip = (page - 1) * page_size

    schedules, total = service.list_schedules(
        user_id=DEFAULT_USER_ID,
        start_date=start_date,
        end_date=end_date,
        status=status,
        skip=skip,
        limit=page_size,
    )

    return ScheduleListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[ScheduleResponse.model_validate(s) for s in schedules],
    )


@router.get("/upcoming", response_model=list[ScheduleResponse])
async def get_upcoming_schedules(
    limit: int = Query(10, ge=1, le=50, description="Maximum items to return"),
    db: Session = Depends(get_db),
) -> list[ScheduleResponse]:
    """Get upcoming schedules."""
    service = ScheduleService(db)
    schedules = service.get_upcoming_schedules(DEFAULT_USER_ID, limit)
    return [ScheduleResponse.model_validate(s) for s in schedules]


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
) -> ScheduleResponse:
    """Get a schedule by ID."""
    service = ScheduleService(db)
    schedule = service.get_schedule(DEFAULT_USER_ID, schedule_id)

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return ScheduleResponse.model_validate(schedule)


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: int,
    data: ScheduleUpdate,
    db: Session = Depends(get_db),
) -> ScheduleResponse:
    """Update a schedule."""
    service = ScheduleService(db)
    schedule = service.update_schedule(DEFAULT_USER_ID, schedule_id, data)

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return ScheduleResponse.model_validate(schedule)


@router.patch("/{schedule_id}/status", response_model=ScheduleResponse)
async def update_schedule_status(
    schedule_id: int,
    data: ScheduleStatusUpdate,
    db: Session = Depends(get_db),
) -> ScheduleResponse:
    """Update schedule status."""
    service = ScheduleService(db)
    schedule = service.update_status(DEFAULT_USER_ID, schedule_id, data.status)

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return ScheduleResponse.model_validate(schedule)


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Delete a schedule."""
    service = ScheduleService(db)
    deleted = service.delete_schedule(DEFAULT_USER_ID, schedule_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return {"message": "Schedule deleted successfully"}
