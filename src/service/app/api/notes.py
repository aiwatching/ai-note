"""Notes API routes."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..schemas.note_schema import (
    NoteCreate,
    NoteDetailResponse,
    NoteListResponse,
    NoteResponse,
    NoteUpdate,
)
from ..services.note_service import NoteService

router = APIRouter()

# Default user ID for MVP (no authentication)
DEFAULT_USER_ID = 1


def get_or_create_default_user(db: Session) -> int:
    """Get or create default user for MVP."""
    user = db.query(User).filter(User.id == DEFAULT_USER_ID).first()
    if not user:
        user = User(id=DEFAULT_USER_ID, username="default_user")
        db.add(user)
        db.commit()
    return DEFAULT_USER_ID


@router.post("", response_model=NoteResponse)
async def create_note(
    note_data: NoteCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new note with AI analysis.

    The note content will be automatically analyzed by AI to extract:
    - Category and subcategory
    - Tags and keywords
    - Summary
    - Related entities (people, dates, locations)
    - Whether it contains todo items or schedule information
    """
    user_id = get_or_create_default_user(db)
    service = NoteService(db)

    note, analysis = await service.create_note(user_id, note_data)

    return NoteResponse(
        id=note.id,
        title=note.title,
        category=note.category,
        subcategory=note.subcategory,
        tags=note.tags,
        summary=note.summary,
        is_todo=note.is_todo,
        is_schedule=note.is_schedule,
        priority=note.priority,
        status=note.status,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.get("", response_model=NoteListResponse)
async def get_notes(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    status: str = Query("active", description="Filter by status"),
    sort_by: str = Query("created_at", description="Sort field"),
    order: str = Query("desc", description="Sort order (asc/desc)"),
    db: Session = Depends(get_db),
):
    """
    Get paginated list of notes.

    Supports filtering by category and status, with customizable sorting.
    """
    user_id = get_or_create_default_user(db)
    service = NoteService(db)

    notes, total = service.get_notes(
        user_id=user_id,
        page=page,
        page_size=page_size,
        category=category,
        status=status,
        sort_by=sort_by,
        order=order,
    )

    items = [
        NoteResponse(
            id=note.id,
            title=note.title,
            category=note.category,
            subcategory=note.subcategory,
            tags=note.tags,
            summary=note.summary,
            is_todo=note.is_todo,
            is_schedule=note.is_schedule,
            priority=note.priority,
            status=note.status,
            created_at=note.created_at,
            updated_at=note.updated_at,
        )
        for note in notes
    ]

    return NoteListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.get("/{note_id}", response_model=NoteDetailResponse)
async def get_note(
    note_id: int,
    db: Session = Depends(get_db),
):
    """
    Get detailed information about a specific note.

    Includes raw content, AI analysis results, and related entities.
    """
    user_id = get_or_create_default_user(db)
    service = NoteService(db)

    note = service.get_note(note_id, user_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    return NoteDetailResponse(
        id=note.id,
        title=note.title,
        raw_content=note.raw_content,
        category=note.category,
        subcategory=note.subcategory,
        tags=note.tags,
        summary=note.summary,
        is_todo=note.is_todo,
        is_schedule=note.is_schedule,
        priority=note.priority,
        status=note.status,
        related_persons=note.related_persons,
        related_dates=note.related_dates,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: int,
    note_data: NoteUpdate,
    db: Session = Depends(get_db),
):
    """
    Update an existing note.

    Optionally re-run AI analysis on the updated content.
    """
    user_id = get_or_create_default_user(db)
    service = NoteService(db)

    result = await service.update_note(note_id, user_id, note_data)
    if not result:
        raise HTTPException(status_code=404, detail="Note not found")

    note, _ = result
    return NoteResponse(
        id=note.id,
        title=note.title,
        category=note.category,
        subcategory=note.subcategory,
        tags=note.tags,
        summary=note.summary,
        is_todo=note.is_todo,
        is_schedule=note.is_schedule,
        priority=note.priority,
        status=note.status,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.delete("/{note_id}")
async def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete a note (soft delete).

    The note is marked as deleted but not permanently removed.
    """
    user_id = get_or_create_default_user(db)
    service = NoteService(db)

    deleted = service.delete_note(note_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Note not found")

    return {"message": "Note deleted successfully"}
