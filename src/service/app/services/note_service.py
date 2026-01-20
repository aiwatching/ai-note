"""Note business logic service."""
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from loguru import logger
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from ..ai.factory import AIServiceFactory
from ..config import get_settings
from ..models.note import Note
from ..schemas.note_schema import AIAnalysisResult, NoteCreate, NoteUpdate
from ..storage.markdown_storage import MarkdownStorage


class NoteService:
    """Service for note-related operations."""

    def __init__(self, db: Session):
        """
        Initialize note service.

        Args:
            db: Database session
        """
        self.db = db
        self.markdown_storage = MarkdownStorage()
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
                logger.info("Using DeepSeek AI service")
            elif service_type == "claude" and settings.claude_api_key:
                self._ai_service = AIServiceFactory.create(
                    "claude",
                    api_key=settings.claude_api_key,
                    model=settings.claude_model,
                )
                logger.info("Using Claude AI service")
            else:
                logger.warning(f"No API key configured for {service_type}")

        return self._ai_service

    async def create_note(
        self, user_id: int, note_data: NoteCreate
    ) -> Tuple[Note, Optional[AIAnalysisResult]]:
        """
        Create a new note with AI analysis.

        Args:
            user_id: User ID
            note_data: Note creation data

        Returns:
            Tuple of (Note, AIAnalysisResult)
        """
        # Create note in database
        note = Note(
            user_id=user_id,
            raw_content=note_data.content,
            status="processing",
        )
        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)

        # Save raw markdown file
        raw_metadata = {
            "id": note.id,
            "user_id": user_id,
            "created_at": note.created_at.isoformat(),
        }
        raw_file_path = self.markdown_storage.save_raw(
            note.id, note_data.content, raw_metadata
        )
        note.raw_file_path = raw_file_path

        # Run AI analysis if service is available
        analysis_result = None
        if self.ai_service:
            try:
                analysis = await self.ai_service.analyze_note(note_data.content)
                analysis_result = AIAnalysisResult(**analysis)

                # Update note with analysis results
                note.title = analysis.get("title")
                note.category = analysis.get("category")
                note.subcategory = analysis.get("subcategory")
                note.tags = analysis.get("tags", [])
                note.summary = analysis.get("summary")
                note.is_todo = analysis.get("is_todo", False)
                note.is_schedule = analysis.get("is_schedule", False)
                note.priority = analysis.get("priority")

                # Extract entities
                entities = analysis.get("entities", {})
                note.related_persons = entities.get("persons", [])
                note.related_dates = entities.get("dates", [])

                # Generate and save organized content
                organized_content = self.markdown_storage.generate_organized_content(
                    note_data.content, analysis
                )
                organized_metadata = {
                    **raw_metadata,
                    **analysis,
                    "organized_at": datetime.now().isoformat(),
                }
                organized_file_path = self.markdown_storage.save_organized(
                    note.id, organized_content, organized_metadata
                )
                note.organized_file_path = organized_file_path

            except Exception as e:
                logger.error(f"AI analysis failed: {e}")
                # Continue without AI analysis

        note.status = "active"
        self.db.commit()
        self.db.refresh(note)

        return note, analysis_result

    def get_note(self, note_id: int, user_id: int) -> Optional[Note]:
        """
        Get note by ID.

        Args:
            note_id: Note ID
            user_id: User ID for authorization

        Returns:
            Note or None
        """
        return (
            self.db.query(Note)
            .filter(Note.id == note_id, Note.user_id == user_id, Note.status != "deleted")
            .first()
        )

    def get_notes(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        category: Optional[str] = None,
        status: str = "active",
        sort_by: str = "created_at",
        order: str = "desc",
    ) -> Tuple[List[Note], int]:
        """
        Get paginated list of notes.

        Args:
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Items per page
            category: Filter by category
            status: Filter by status
            sort_by: Sort field
            order: Sort order (asc/desc)

        Returns:
            Tuple of (notes list, total count)
        """
        query = self.db.query(Note).filter(
            Note.user_id == user_id,
            Note.status == status,
        )

        if category:
            query = query.filter(Note.category == category)

        # Get total count
        total = query.count()

        # Apply sorting
        sort_column = getattr(Note, sort_by, Note.created_at)
        if order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)

        # Apply pagination
        offset = (page - 1) * page_size
        notes = query.offset(offset).limit(page_size).all()

        return notes, total

    async def update_note(
        self, note_id: int, user_id: int, note_data: NoteUpdate
    ) -> Optional[Tuple[Note, Optional[AIAnalysisResult]]]:
        """
        Update a note.

        Args:
            note_id: Note ID
            user_id: User ID
            note_data: Update data

        Returns:
            Tuple of (updated Note, AIAnalysisResult) or None
        """
        note = self.get_note(note_id, user_id)
        if not note:
            return None

        analysis_result = None

        if note_data.content:
            note.raw_content = note_data.content

            # Update raw file
            if note.raw_file_path:
                self.markdown_storage.update(
                    note.raw_file_path,
                    note_data.content,
                    {"id": note.id, "user_id": user_id, "updated_at": datetime.now().isoformat()},
                )

            # Re-analyze if requested
            if note_data.reanalyze and self.ai_service:
                try:
                    analysis = await self.ai_service.analyze_note(note_data.content)
                    analysis_result = AIAnalysisResult(**analysis)

                    note.title = analysis.get("title")
                    note.category = analysis.get("category")
                    note.subcategory = analysis.get("subcategory")
                    note.tags = analysis.get("tags", [])
                    note.summary = analysis.get("summary")
                    note.is_todo = analysis.get("is_todo", False)
                    note.is_schedule = analysis.get("is_schedule", False)
                    note.priority = analysis.get("priority")

                    entities = analysis.get("entities", {})
                    note.related_persons = entities.get("persons", [])
                    note.related_dates = entities.get("dates", [])

                except Exception as e:
                    logger.error(f"AI re-analysis failed: {e}")

        note.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(note)

        return note, analysis_result

    def delete_note(self, note_id: int, user_id: int) -> bool:
        """
        Soft delete a note.

        Args:
            note_id: Note ID
            user_id: User ID

        Returns:
            True if deleted
        """
        note = self.get_note(note_id, user_id)
        if not note:
            return False

        note.status = "deleted"
        note.updated_at = datetime.now()
        self.db.commit()

        return True

    def delete_all_notes(self, user_id: int, hard_delete: bool = False) -> int:
        """
        Delete all notes for a user (for debugging).

        Args:
            user_id: User ID
            hard_delete: If True, permanently delete; otherwise soft delete

        Returns:
            Number of deleted notes
        """
        query = self.db.query(Note).filter(Note.user_id == user_id)

        if hard_delete:
            # Permanently delete all notes
            count = query.count()
            query.delete(synchronize_session=False)
        else:
            # Soft delete
            count = query.filter(Note.status != "deleted").count()
            query.filter(Note.status != "deleted").update(
                {"status": "deleted", "updated_at": datetime.now()},
                synchronize_session=False
            )

        self.db.commit()
        return count

    def search_notes(
        self,
        user_id: int,
        keywords: List[str],
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 20,
    ) -> List[Note]:
        """
        Search notes by keywords and filters.

        Args:
            user_id: User ID
            keywords: Search keywords
            category: Filter by category
            tags: Filter by tags
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum results

        Returns:
            List of matching notes
        """
        query = self.db.query(Note).filter(
            Note.user_id == user_id,
            Note.status == "active",
        )

        # Keyword search in title, content, and summary
        if keywords:
            keyword_filters = []
            for keyword in keywords:
                keyword_pattern = f"%{keyword}%"
                keyword_filters.append(Note.title.ilike(keyword_pattern))
                keyword_filters.append(Note.raw_content.ilike(keyword_pattern))
                keyword_filters.append(Note.summary.ilike(keyword_pattern))
            query = query.filter(or_(*keyword_filters))

        # Category filter
        if category:
            query = query.filter(Note.category == category)

        # Date range filter
        if start_date:
            query = query.filter(Note.created_at >= start_date)
        if end_date:
            query = query.filter(Note.created_at <= end_date)

        # Tags filter (JSON contains check for SQLite)
        if tags:
            for tag in tags:
                query = query.filter(Note._tags.contains(f'"{tag}"'))

        return query.order_by(desc(Note.created_at)).limit(limit).all()
