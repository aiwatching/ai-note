"""Search-related Pydantic schemas."""
from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    """Search filter parameters."""

    category: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None
    is_todo: Optional[bool] = None
    is_schedule: Optional[bool] = None
    priority: Optional[str] = None
    persons: Optional[List[str]] = None


class TimeRange(BaseModel):
    """Time range for search."""

    start: Optional[date] = None
    end: Optional[date] = None


class SearchQuery(BaseModel):
    """Schema for search query."""

    query: str = Field(..., min_length=1, description="Natural language search query")
    context: Optional[dict] = Field(
        default=None, description="Additional context for search"
    )


class SearchResult(BaseModel):
    """Single search result item."""

    note_id: int
    title: Optional[str] = None
    summary: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    highlight: Optional[str] = None
    created_at: str


class SearchSuggestion(BaseModel):
    """Suggested action from search."""

    action: str
    description: str
    data: Optional[dict] = None


class SearchResponse(BaseModel):
    """Schema for search response."""

    intent: str = Field(description="Understood search intent")
    results: List[SearchResult] = Field(default_factory=list)
    suggestions: List[SearchSuggestion] = Field(default_factory=list)
    total: int = 0


class ParsedSearchQuery(BaseModel):
    """Parsed search query from AI."""

    intent: str
    filters: SearchFilters = Field(default_factory=SearchFilters)
    time_range: Optional[TimeRange] = None
    keywords: List[str] = Field(default_factory=list)
    sort_by: str = "created_at"
    order: str = "desc"
