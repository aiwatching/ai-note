"""Todos API routes."""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..schemas.todo_schema import (
    TodoCreate,
    TodoFromNoteCreate,
    TodoListResponse,
    TodoResponse,
    TodoStatusUpdate,
    TodoUpdate,
)
from ..services.todo_service import TodoService

router = APIRouter()

DEFAULT_USER_ID = 1


def get_or_create_default_user(db: Session) -> int:
    """Get or create default user for MVP."""
    user = db.query(User).filter(User.id == DEFAULT_USER_ID).first()
    if not user:
        user = User(id=DEFAULT_USER_ID, username="default_user")
        db.add(user)
        db.commit()
    return DEFAULT_USER_ID


@router.post("", response_model=TodoResponse)
async def create_todo(
    todo_data: TodoCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new todo item.

    Can optionally be linked to a note via note_id.
    """
    user_id = get_or_create_default_user(db)
    service = TodoService(db)

    todo = service.create_todo(user_id, todo_data)
    return TodoResponse(
        id=todo.id,
        title=todo.title,
        description=todo.description,
        due_date=todo.due_date,
        priority=todo.priority,
        status=todo.status,
        note_id=todo.note_id,
        created_at=todo.created_at,
        updated_at=todo.updated_at,
        completed_at=todo.completed_at,
    )


@router.get("", response_model=TodoListResponse)
async def get_todos(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    due_date_from: Optional[date] = Query(None, description="Filter by due date start"),
    due_date_to: Optional[date] = Query(None, description="Filter by due date end"),
    db: Session = Depends(get_db),
):
    """
    Get paginated list of todos.

    Supports filtering by status, priority, and due date range.
    Results are sorted by priority (high first) and due date.
    """
    user_id = get_or_create_default_user(db)
    service = TodoService(db)

    todos, total = service.get_todos(
        user_id=user_id,
        page=page,
        page_size=page_size,
        status=status,
        priority=priority,
        due_date_from=due_date_from,
        due_date_to=due_date_to,
    )

    items = [
        TodoResponse(
            id=todo.id,
            title=todo.title,
            description=todo.description,
            due_date=todo.due_date,
            priority=todo.priority,
            status=todo.status,
            note_id=todo.note_id,
            created_at=todo.created_at,
            updated_at=todo.updated_at,
            completed_at=todo.completed_at,
        )
        for todo in todos
    ]

    return TodoListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.get("/{todo_id}", response_model=TodoResponse)
async def get_todo(
    todo_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific todo by ID."""
    user_id = get_or_create_default_user(db)
    service = TodoService(db)

    todo = service.get_todo(todo_id, user_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")

    return TodoResponse(
        id=todo.id,
        title=todo.title,
        description=todo.description,
        due_date=todo.due_date,
        priority=todo.priority,
        status=todo.status,
        note_id=todo.note_id,
        created_at=todo.created_at,
        updated_at=todo.updated_at,
        completed_at=todo.completed_at,
    )


@router.put("/{todo_id}", response_model=TodoResponse)
async def update_todo(
    todo_id: int,
    todo_data: TodoUpdate,
    db: Session = Depends(get_db),
):
    """Update a todo item."""
    user_id = get_or_create_default_user(db)
    service = TodoService(db)

    todo = service.update_todo(todo_id, user_id, todo_data)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")

    return TodoResponse(
        id=todo.id,
        title=todo.title,
        description=todo.description,
        due_date=todo.due_date,
        priority=todo.priority,
        status=todo.status,
        note_id=todo.note_id,
        created_at=todo.created_at,
        updated_at=todo.updated_at,
        completed_at=todo.completed_at,
    )


@router.patch("/{todo_id}/status", response_model=TodoResponse)
async def update_todo_status(
    todo_id: int,
    status_data: TodoStatusUpdate,
    db: Session = Depends(get_db),
):
    """
    Update todo status.

    Valid statuses: pending, in_progress, completed, cancelled
    """
    user_id = get_or_create_default_user(db)
    service = TodoService(db)

    todo = service.update_status(todo_id, user_id, status_data.status)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")

    return TodoResponse(
        id=todo.id,
        title=todo.title,
        description=todo.description,
        due_date=todo.due_date,
        priority=todo.priority,
        status=todo.status,
        note_id=todo.note_id,
        created_at=todo.created_at,
        updated_at=todo.updated_at,
        completed_at=todo.completed_at,
    )


@router.delete("/{todo_id}")
async def delete_todo(
    todo_id: int,
    db: Session = Depends(get_db),
):
    """Delete a todo item."""
    user_id = get_or_create_default_user(db)
    service = TodoService(db)

    deleted = service.delete_todo(todo_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Todo not found")

    return {"message": "Todo deleted successfully"}


@router.post("/from-note", response_model=List[TodoResponse])
async def create_todos_from_note(
    data: TodoFromNoteCreate,
    db: Session = Depends(get_db),
):
    """
    Create todos from a note using AI extraction.

    AI will analyze the note content and extract actionable tasks,
    including due dates and priorities if mentioned.
    """
    user_id = get_or_create_default_user(db)
    service = TodoService(db)

    todos = await service.create_todos_from_note(
        data.note_id, user_id, data.auto_extract
    )

    return [
        TodoResponse(
            id=todo.id,
            title=todo.title,
            description=todo.description,
            due_date=todo.due_date,
            priority=todo.priority,
            status=todo.status,
            note_id=todo.note_id,
            created_at=todo.created_at,
            updated_at=todo.updated_at,
            completed_at=todo.completed_at,
        )
        for todo in todos
    ]
