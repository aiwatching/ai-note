"""Note-related Pydantic schemas."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AIAnalysisResult(BaseModel):
    """AI analysis result schema."""

    title: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    is_todo: bool = False
    is_schedule: bool = False
    priority: Optional[str] = None
    entities: Optional[dict] = None
    suggested_actions: List[dict] = Field(default_factory=list)


class NoteCreate(BaseModel):
    """Schema for creating a note."""

    content: str = Field(..., min_length=1, description="Note content in Markdown format")
    custom_prompt: Optional[str] = Field(None, description="Custom prompt for AI analysis")


class NoteUpdate(BaseModel):
    """Schema for updating a note."""

    content: Optional[str] = Field(None, min_length=1)
    reanalyze: bool = Field(default=False, description="Whether to re-run AI analysis")
    custom_prompt: Optional[str] = Field(None, description="Custom prompt for AI analysis")


class NoteResponse(BaseModel):
    """Schema for note response."""

    id: int
    title: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    is_todo: bool = False
    is_schedule: bool = False
    priority: Optional[str] = None
    status: str = "active"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NoteDetailResponse(BaseModel):
    """Schema for detailed note response."""

    id: int
    title: Optional[str] = None
    raw_content: str
    category: Optional[str] = None
    subcategory: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    is_todo: bool = False
    is_schedule: bool = False
    priority: Optional[str] = None
    status: str = "active"
    related_persons: List[str] = Field(default_factory=list)
    related_dates: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    ai_analysis: Optional[AIAnalysisResult] = None

    class Config:
        from_attributes = True


class NoteListResponse(BaseModel):
    """Schema for paginated note list response."""

    total: int
    page: int
    page_size: int
    items: List[NoteResponse]
