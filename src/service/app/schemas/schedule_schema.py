"""Schedule schemas for API validation."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ScheduleBase(BaseModel):
    """Base schedule schema."""

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    location: Optional[str] = None
    participants: Optional[List[str]] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    is_all_day: bool = False
    recurrence: Optional[str] = None
    reminder_minutes: Optional[int] = None


class ScheduleCreate(ScheduleBase):
    """Schema for creating a schedule."""

    note_id: Optional[int] = None


class ScheduleUpdate(BaseModel):
    """Schema for updating a schedule."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    location: Optional[str] = None
    participants: Optional[List[str]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_all_day: Optional[bool] = None
    recurrence: Optional[str] = None
    reminder_minutes: Optional[int] = None


class ScheduleStatusUpdate(BaseModel):
    """Schema for updating schedule status."""

    status: str = Field(..., pattern="^(scheduled|completed|cancelled)$")


class ScheduleResponse(ScheduleBase):
    """Schema for schedule response."""

    id: int
    user_id: int
    note_id: Optional[int] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScheduleListResponse(BaseModel):
    """Schema for paginated schedule list."""

    total: int
    page: int
    page_size: int
    items: List[ScheduleResponse]
