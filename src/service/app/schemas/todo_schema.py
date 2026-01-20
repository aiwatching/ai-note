"""Todo-related Pydantic schemas."""
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class TodoCreate(BaseModel):
    """Schema for creating a todo."""

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    due_date: Optional[date] = None
    priority: str = Field(default="medium", pattern="^(high|medium|low)$")
    note_id: Optional[int] = None


class TodoUpdate(BaseModel):
    """Schema for updating a todo."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    due_date: Optional[date] = None
    priority: Optional[str] = Field(None, pattern="^(high|medium|low)$")


class TodoStatusUpdate(BaseModel):
    """Schema for updating todo status."""

    status: str = Field(..., pattern="^(pending|in_progress|completed|cancelled)$")


class TodoResponse(BaseModel):
    """Schema for todo response."""

    id: int
    title: str
    description: Optional[str] = None
    due_date: Optional[date] = None
    priority: str
    status: str
    note_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TodoListResponse(BaseModel):
    """Schema for paginated todo list response."""

    total: int
    page: int
    page_size: int
    items: List[TodoResponse]


class TodoFromNoteCreate(BaseModel):
    """Schema for creating todos from a note."""

    note_id: int
    auto_extract: bool = Field(
        default=True, description="Whether to let AI auto-extract todos"
    )


class TodoFromNoteResponse(BaseModel):
    """Schema for todos created from a note."""

    todos: List[TodoResponse]
