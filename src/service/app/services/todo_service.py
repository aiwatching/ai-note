"""Todo business logic service."""
from datetime import datetime
from typing import List, Optional, Tuple

from loguru import logger
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..ai.factory import AIServiceFactory
from ..config import get_settings
from ..models.note import Note
from ..models.todo import Todo
from ..schemas.todo_schema import TodoCreate, TodoUpdate


class TodoService:
    """Service for todo-related operations."""

    def __init__(self, db: Session):
        """
        Initialize todo service.

        Args:
            db: Database session
        """
        self.db = db
        self._ai_service = None

    @property
    def ai_service(self):
        """Lazy load AI service based on configured provider."""
        if self._ai_service is None:
            settings = get_settings()
            service_type = settings.ai_service

            if service_type == "deepseek" and settings.deepseek_api_key:
                self._ai_service = AIServiceFactory.create(
                    "deepseek",
                    api_key=settings.deepseek_api_key,
                    model=settings.deepseek_model,
                    base_url=settings.deepseek_base_url,
                )
            elif service_type == "claude" and settings.claude_api_key:
                self._ai_service = AIServiceFactory.create(
                    "claude",
                    api_key=settings.claude_api_key,
                    model=settings.claude_model,
                )

        return self._ai_service

    def create_todo(self, user_id: int, todo_data: TodoCreate) -> Todo:
        """
        Create a new todo.

        Args:
            user_id: User ID
            todo_data: Todo creation data

        Returns:
            Created Todo
        """
        todo = Todo(
            user_id=user_id,
            title=todo_data.title,
            description=todo_data.description,
            due_date=todo_data.due_date,
            priority=todo_data.priority,
            note_id=todo_data.note_id,
        )
        self.db.add(todo)
        self.db.commit()
        self.db.refresh(todo)

        return todo

    def get_todo(self, todo_id: int, user_id: int) -> Optional[Todo]:
        """
        Get todo by ID.

        Args:
            todo_id: Todo ID
            user_id: User ID

        Returns:
            Todo or None
        """
        return (
            self.db.query(Todo)
            .filter(Todo.id == todo_id, Todo.user_id == user_id)
            .first()
        )

    def get_todos(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        due_date_from: Optional[datetime] = None,
        due_date_to: Optional[datetime] = None,
    ) -> Tuple[List[Todo], int]:
        """
        Get paginated list of todos.

        Args:
            user_id: User ID
            page: Page number
            page_size: Items per page
            status: Filter by status
            priority: Filter by priority
            due_date_from: Filter by due date start
            due_date_to: Filter by due date end

        Returns:
            Tuple of (todos list, total count)
        """
        query = self.db.query(Todo).filter(Todo.user_id == user_id)

        if status:
            query = query.filter(Todo.status == status)
        if priority:
            query = query.filter(Todo.priority == priority)
        if due_date_from:
            query = query.filter(Todo.due_date >= due_date_from)
        if due_date_to:
            query = query.filter(Todo.due_date <= due_date_to)

        total = query.count()

        # Sort by priority (high first), then by due date
        todos = (
            query.order_by(
                Todo.status,  # pending first
                desc(Todo.priority == "high"),
                desc(Todo.priority == "medium"),
                Todo.due_date,
                desc(Todo.created_at),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return todos, total

    def update_todo(
        self, todo_id: int, user_id: int, todo_data: TodoUpdate
    ) -> Optional[Todo]:
        """
        Update a todo.

        Args:
            todo_id: Todo ID
            user_id: User ID
            todo_data: Update data

        Returns:
            Updated Todo or None
        """
        todo = self.get_todo(todo_id, user_id)
        if not todo:
            return None

        if todo_data.title is not None:
            todo.title = todo_data.title
        if todo_data.description is not None:
            todo.description = todo_data.description
        if todo_data.due_date is not None:
            todo.due_date = todo_data.due_date
        if todo_data.priority is not None:
            todo.priority = todo_data.priority

        todo.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(todo)

        return todo

    def update_status(
        self, todo_id: int, user_id: int, status: str
    ) -> Optional[Todo]:
        """
        Update todo status.

        Args:
            todo_id: Todo ID
            user_id: User ID
            status: New status

        Returns:
            Updated Todo or None
        """
        todo = self.get_todo(todo_id, user_id)
        if not todo:
            return None

        todo.status = status
        todo.updated_at = datetime.now()

        if status == "completed":
            todo.completed_at = datetime.now()
        else:
            todo.completed_at = None

        self.db.commit()
        self.db.refresh(todo)

        return todo

    def delete_todo(self, todo_id: int, user_id: int) -> bool:
        """
        Delete a todo.

        Args:
            todo_id: Todo ID
            user_id: User ID

        Returns:
            True if deleted
        """
        todo = self.get_todo(todo_id, user_id)
        if not todo:
            return False

        self.db.delete(todo)
        self.db.commit()

        return True

    async def create_todos_from_note(
        self, note_id: int, user_id: int, auto_extract: bool = True
    ) -> List[Todo]:
        """
        Create todos from a note using AI extraction.

        Args:
            note_id: Note ID
            user_id: User ID
            auto_extract: Whether to use AI for extraction

        Returns:
            List of created Todos
        """
        # Get the note
        note = (
            self.db.query(Note)
            .filter(Note.id == note_id, Note.user_id == user_id)
            .first()
        )
        if not note:
            return []

        todos_data = []

        if auto_extract and self.ai_service:
            try:
                # Use AI to extract todos
                extracted = await self.ai_service.extract_todos(note.raw_content)
                todos_data = extracted
            except Exception as e:
                logger.error(f"AI extraction failed: {e}")

        # Create todos
        created_todos = []
        for todo_data in todos_data:
            todo = Todo(
                user_id=user_id,
                note_id=note_id,
                title=todo_data.get("title", "Untitled Task"),
                description=todo_data.get("description"),
                due_date=todo_data.get("due_date"),
                priority=todo_data.get("priority", "medium"),
            )
            self.db.add(todo)
            created_todos.append(todo)

        if created_todos:
            self.db.commit()
            for todo in created_todos:
                self.db.refresh(todo)

        return created_todos
