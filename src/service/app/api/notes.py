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


@router.get("/grouped")
async def get_notes_grouped(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db),
):
    """
    Get notes grouped by title.

    Returns groups of notes that share the same title, sorted by latest update.
    """
    user_id = get_or_create_default_user(db)
    service = NoteService(db)

    groups, total = service.get_notes_grouped_by_title(
        user_id=user_id,
        page=page,
        page_size=page_size,
        category=category,
    )

    # Format response
    result = []
    for group in groups:
        result.append({
            "title": group["title"],
            "note_count": len(group["notes"]),
            "latest_updated_at": group["latest_updated_at"].isoformat() if group["latest_updated_at"] else None,
            "notes": [
                {
                    "id": note.id,
                    "title": note.title,
                    "category": note.category,
                    "summary": note.summary,
                    "created_at": note.created_at.isoformat() if note.created_at else None,
                    "updated_at": note.updated_at.isoformat() if note.updated_at else None,
                }
                for note in group["notes"]
            ],
        })

    return {
        "total_groups": total,
        "page": page,
        "page_size": page_size,
        "groups": result,
    }


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


@router.delete("")
async def delete_all_notes(
    hard_delete: bool = Query(False, description="Permanently delete all notes"),
    db: Session = Depends(get_db),
):
    """
    Delete all notes (for debugging purposes).

    Use hard_delete=true to permanently remove all notes.
    """
    user_id = get_or_create_default_user(db)
    service = NoteService(db)

    count = service.delete_all_notes(user_id, hard_delete=hard_delete)

    return {"message": f"Deleted {count} notes", "count": count}


@router.get("/{note_id}/related")
async def get_related_notes(
    note_id: int,
    min_score: float = Query(0.2, ge=0, le=1, description="Minimum relation score"),
    limit: int = Query(10, ge=1, le=50, description="Maximum related notes to return"),
    db: Session = Depends(get_db),
):
    """
    Get notes related to a specific note.

    Returns notes with similar entities, topics, or temporal proximity.
    Each result includes the relation type and score.
    """
    user_id = get_or_create_default_user(db)
    service = NoteService(db)

    note = service.get_note(note_id, user_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    related = service.get_related_notes(note_id, user_id, min_score, limit)

    return {"note_id": note_id, "related_notes": related}


@router.get("/{note_id}/entities")
async def get_note_entities(
    note_id: int,
    db: Session = Depends(get_db),
):
    """
    Get entities (persons, companies, projects, etc.) associated with a note.

    Entities are extracted during AI analysis and standardized across notes.
    """
    user_id = get_or_create_default_user(db)
    service = NoteService(db)

    note = service.get_note(note_id, user_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    entities = service.get_note_entities(note_id)

    return {"note_id": note_id, "entities": entities}


@router.get("/{note_id}/full")
async def get_note_with_relations(
    note_id: int,
    db: Session = Depends(get_db),
):
    """
    Get note with all related data including entities and related notes.

    This is a comprehensive view for detailed note inspection.
    """
    user_id = get_or_create_default_user(db)
    service = NoteService(db)

    result = service.get_note_with_relations(note_id, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Note not found")

    note = result["note"]

    return {
        "note": {
            "id": note.id,
            "title": note.title,
            "raw_content": note.raw_content,
            "category": note.category,
            "subcategory": note.subcategory,
            "domain": note.domain,
            "tags": note.tags,
            "keywords": note.keywords,
            "summary": note.summary,
            "core_topic": note.core_topic,
            "is_todo": note.is_todo,
            "is_schedule": note.is_schedule,
            "is_follow_up": note.is_follow_up,
            "priority": note.priority,
            "urgency": note.urgency,
            "status": note.status,
            "key_points": note.key_points,
            "action_suggestions": note.action_suggestions,
            "time_info": note.time_info,
            "created_at": note.created_at,
            "updated_at": note.updated_at,
        },
        "entities": result["entities"],
        "related_notes": result["related_notes"],
    }


@router.delete("/{note_id}/relations/{related_note_id}")
async def delete_note_relation(
    note_id: int,
    related_note_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete/break the relationship between two notes.

    This allows users to manually remove incorrect or unwanted relations.
    """
    user_id = get_or_create_default_user(db)
    service = NoteService(db)

    # Verify note exists
    note = service.get_note(note_id, user_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Delete the relation
    deleted = service.delete_relation(note_id, related_note_id)

    if deleted:
        return {"message": "Relation deleted successfully"}
    else:
        return {"message": "No relation found to delete"}
