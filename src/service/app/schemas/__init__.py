"""Pydantic schemas for request/response validation."""
from .note_schema import (
    NoteCreate,
    NoteUpdate,
    NoteResponse,
    NoteListResponse,
    NoteDetailResponse,
    AIAnalysisResult,
)
from .todo_schema import (
    TodoCreate,
    TodoUpdate,
    TodoStatusUpdate,
    TodoResponse,
    TodoListResponse,
    TodoFromNoteCreate,
)
from .search_schema import (
    SearchQuery,
    SearchResponse,
    SearchResult,
    SearchFilters,
)

__all__ = [
    "NoteCreate",
    "NoteUpdate",
    "NoteResponse",
    "NoteListResponse",
    "NoteDetailResponse",
    "AIAnalysisResult",
    "TodoCreate",
    "TodoUpdate",
    "TodoStatusUpdate",
    "TodoResponse",
    "TodoListResponse",
    "TodoFromNoteCreate",
    "SearchQuery",
    "SearchResponse",
    "SearchResult",
    "SearchFilters",
]
