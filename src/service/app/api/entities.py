"""Entities API routes."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..services.entity_service import EntityService

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


class EntityResponse(BaseModel):
    """Entity response schema."""
    id: int
    entity_type: str
    canonical_name: str
    aliases: List[str]
    mention_count: int
    first_note_id: Optional[int]
    last_note_id: Optional[int]

    class Config:
        from_attributes = True


class EntityMergeRequest(BaseModel):
    """Request to merge two entities."""
    primary_id: int
    secondary_id: int


@router.get("", response_model=List[EntityResponse])
async def get_entities(
    entity_type: Optional[str] = Query(None, description="Filter by entity type (person, company, project, location, term)"),
    limit: int = Query(100, ge=1, le=500, description="Maximum entities to return"),
    db: Session = Depends(get_db),
):
    """
    Get all entities for the current user.

    Optionally filter by entity type. Returns entities sorted by mention count.
    """
    user_id = get_or_create_default_user(db)
    service = EntityService(db)

    entities = service.get_user_entities(user_id, entity_type, limit)

    return [
        EntityResponse(
            id=e.id,
            entity_type=e.entity_type,
            canonical_name=e.canonical_name,
            aliases=e.aliases,
            mention_count=e.mention_count,
            first_note_id=e.first_note_id,
            last_note_id=e.last_note_id,
        )
        for e in entities
    ]


@router.get("/{entity_id}/notes")
async def get_entity_notes(
    entity_id: int,
    db: Session = Depends(get_db),
):
    """
    Get all notes that mention a specific entity.
    """
    user_id = get_or_create_default_user(db)
    service = EntityService(db)

    notes = service.get_notes_for_entity(entity_id)

    # Filter to user's notes only
    user_notes = [n for n in notes if n.user_id == user_id]

    return {
        "entity_id": entity_id,
        "notes": [
            {
                "id": n.id,
                "title": n.title,
                "summary": n.summary,
                "category": n.category,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in user_notes
        ],
    }


@router.post("/merge")
async def merge_entities(
    request: EntityMergeRequest,
    db: Session = Depends(get_db),
):
    """
    Merge two entities into one.

    The secondary entity's notes and aliases are transferred to the primary entity,
    then the secondary entity is deleted.
    """
    user_id = get_or_create_default_user(db)
    service = EntityService(db)

    result = service.merge_entities(request.primary_id, request.secondary_id, user_id)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to merge entities. Check that both entities exist and are of the same type.")

    return {
        "message": "Entities merged successfully",
        "merged_entity": {
            "id": result.id,
            "canonical_name": result.canonical_name,
            "aliases": result.aliases,
            "mention_count": result.mention_count,
        },
    }


@router.get("/stats")
async def get_entity_stats(
    db: Session = Depends(get_db),
):
    """
    Get entity statistics for the current user.
    """
    user_id = get_or_create_default_user(db)
    service = EntityService(db)

    # Get counts by type
    persons = service.get_user_entities(user_id, "person", 1000)
    companies = service.get_user_entities(user_id, "company", 1000)
    projects = service.get_user_entities(user_id, "project", 1000)
    locations = service.get_user_entities(user_id, "location", 1000)
    terms = service.get_user_entities(user_id, "term", 1000)

    return {
        "total": len(persons) + len(companies) + len(projects) + len(locations) + len(terms),
        "by_type": {
            "person": len(persons),
            "company": len(companies),
            "project": len(projects),
            "location": len(locations),
            "term": len(terms),
        },
        "top_entities": [
            {
                "id": e.id,
                "type": e.entity_type,
                "name": e.canonical_name,
                "mentions": e.mention_count,
            }
            for e in sorted(
                persons + companies + projects,
                key=lambda x: x.mention_count,
                reverse=True,
            )[:10]
        ],
    }
