"""Note business logic service with deep AI analysis."""
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from loguru import logger
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from ..ai.factory import AIServiceFactory
from ..ai.prompts import DEFAULT_CATEGORIES, DEFAULT_DOMAINS
from ..config import get_settings
from ..models.note import Note
from ..schemas.note_schema import AIAnalysisResult, NoteCreate, NoteUpdate
from ..storage.markdown_storage import MarkdownStorage
from .entity_service import EntityService
from .relation_service import RelationService


class NoteService:
    """Service for note-related operations with deep AI analysis."""

    def __init__(self, db: Session):
        """Initialize note service."""
        self.db = db
        self.markdown_storage = MarkdownStorage()
        self._ai_service = None
        self._entity_service = None
        self._relation_service = None

    @property
    def entity_service(self):
        """Lazy load entity service."""
        if self._entity_service is None:
            self._entity_service = EntityService(self.db)
        return self._entity_service

    @property
    def relation_service(self):
        """Lazy load relation service."""
        if self._relation_service is None:
            self._relation_service = RelationService(self.db)
        return self._relation_service

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

    def _apply_deep_analysis_to_note(self, note: Note, analysis: Dict) -> None:
        """Apply deep analysis results to note model."""
        # Basic info
        basic = analysis.get("basic_info", {})
        note.title = basic.get("title")
        note.category = basic.get("category")
        note.subcategory = basic.get("subcategory")
        note.summary = basic.get("summary")

        # Topic analysis
        topic = analysis.get("topic_analysis", {})
        note.core_topic = topic.get("core_topic")
        note.keywords = topic.get("keywords", [])
        note.domain = topic.get("domain")

        # Entities
        note.entities = analysis.get("entities", {})

        # Extract tags from keywords and technical terms
        keywords = topic.get("keywords", [])
        entities = analysis.get("entities", {})
        terms = entities.get("technical_terms", [])
        note.tags = list(set(keywords + terms))[:10]  # Combine and limit to 10

        # Time info
        note.time_info = analysis.get("time_info", {})

        # Relation signals
        relation = analysis.get("relation_signals", {})
        note.is_follow_up = relation.get("is_follow_up", False)
        note.is_summary_note = relation.get("is_summary", False)
        note.is_standalone = relation.get("is_standalone", True)
        note.reference_keywords = relation.get("reference_keywords", [])
        note.continuation_topic = relation.get("continuation_topic")

        # Content features
        features = analysis.get("content_features", {})
        note.intent = features.get("intent")
        note.content_type = features.get("content_type")
        note.is_todo = features.get("has_todos", False)
        note.is_schedule = bool(analysis.get("time_info", {}).get("event_times"))
        note.has_questions = features.get("has_questions", False)
        note.has_decisions = features.get("has_decisions", False)
        note.urgency = features.get("urgency", "normal")

        # Priority assessment
        priority = analysis.get("priority_assessment", {})
        note.priority = priority.get("priority", "medium")
        note.urgency_score = priority.get("urgency_score", 0.5)
        note.importance_score = priority.get("importance_score", 0.5)
        note.priority_reason = priority.get("reason")

        # Action suggestions and key points
        note.action_suggestions = analysis.get("action_suggestions", [])
        note.key_points = analysis.get("key_points", [])

        # Legacy fields for backward compatibility
        persons = note.entities.get("persons", [])
        note.related_persons = [
            p["name"] if isinstance(p, dict) else p for p in persons
        ]

        time_info = analysis.get("time_info", {})
        dates = []
        for event in time_info.get("event_times", []):
            if event.get("time"):
                dates.append(event["time"])
        for deadline in time_info.get("deadlines", []):
            if deadline.get("time"):
                dates.append(deadline["time"])
        note.related_dates = dates

    async def create_note(
        self, user_id: int, note_data: NoteCreate
    ) -> Tuple[Note, Optional[Dict]]:
        """
        Create a new note with deep AI analysis.

        Args:
            user_id: User ID
            note_data: Note creation data

        Returns:
            Tuple of (Note, analysis result dict)
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

        # Run deep AI analysis if service is available
        analysis_result = None
        if self.ai_service:
            try:
                current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
                analysis = await self.ai_service.deep_analyze_note(
                    content=note_data.content,
                    current_date=current_date,
                    categories=DEFAULT_CATEGORIES,
                    domains=DEFAULT_DOMAINS,
                    custom_prompt=note_data.custom_prompt,
                )
                analysis_result = analysis

                # Apply analysis results to note
                self._apply_deep_analysis_to_note(note, analysis)

                # Generate and save organized content
                organized_content = self._generate_organized_content(
                    note_data.content, analysis
                )
                organized_metadata = {
                    **raw_metadata,
                    "analysis": analysis,
                    "organized_at": datetime.now().isoformat(),
                }
                organized_file_path = self.markdown_storage.save_organized(
                    note.id, organized_content, organized_metadata
                )
                note.organized_file_path = organized_file_path

                # Process entities from analysis
                try:
                    entities_data = analysis.get("entities", {})
                    if entities_data:
                        self.entity_service.process_note_entities(
                            note, entities_data, user_id
                        )
                        logger.debug(f"Processed entities for note {note.id}")
                except Exception as entity_error:
                    logger.error(f"Entity processing failed: {entity_error}")

            except Exception as e:
                logger.error(f"Deep AI analysis failed: {e}")
                # Continue without AI analysis

        note.status = "active"
        self.db.commit()
        self.db.refresh(note)

        # Calculate relations with other notes (async-friendly)
        try:
            self.relation_service.calculate_note_relations(note)
            logger.debug(f"Calculated relations for note {note.id}")
        except Exception as rel_error:
            logger.error(f"Relation calculation failed: {rel_error}")

        return note, analysis_result

    def _generate_organized_content(self, raw_content: str, analysis: Dict) -> str:
        """Generate organized markdown content from analysis."""
        basic = analysis.get("basic_info", {})
        topic = analysis.get("topic_analysis", {})
        key_points = analysis.get("key_points", [])
        actions = analysis.get("action_suggestions", [])

        lines = []

        # Title
        title = basic.get("title") or "无标题笔记"
        lines.append(f"# {title}")
        lines.append("")

        # Metadata
        lines.append("## 元信息")
        lines.append(f"- **分类**: {basic.get('category', '未分类')}")
        if basic.get("subcategory"):
            lines.append(f"- **子分类**: {basic['subcategory']}")
        if topic.get("domain"):
            lines.append(f"- **领域**: {topic['domain']}")
        if topic.get("keywords"):
            lines.append(f"- **关键词**: {', '.join(topic['keywords'])}")
        lines.append("")

        # Summary
        if basic.get("summary"):
            lines.append("## 摘要")
            lines.append(basic["summary"])
            lines.append("")

        # Key points
        if key_points:
            lines.append("## 关键要点")
            for point in key_points:
                lines.append(f"- {point}")
            lines.append("")

        # Original content
        lines.append("## 原始内容")
        lines.append(raw_content)
        lines.append("")

        # Action suggestions
        if actions:
            lines.append("## 建议操作")
            for action in actions:
                action_type = action.get("type", "")
                title = action.get("title", "")
                reason = action.get("reason", "")
                lines.append(f"- **{action_type}**: {title}")
                if reason:
                    lines.append(f"  - 理由: {reason}")
            lines.append("")

        return "\n".join(lines)

    def get_note(self, note_id: int, user_id: int) -> Optional[Note]:
        """Get note by ID."""
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
        """Get paginated list of notes."""
        query = self.db.query(Note).filter(
            Note.user_id == user_id,
            Note.status == status,
        )

        if category:
            query = query.filter(Note.category == category)

        total = query.count()

        sort_column = getattr(Note, sort_by, Note.created_at)
        if order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)

        offset = (page - 1) * page_size
        notes = query.offset(offset).limit(page_size).all()

        return notes, total

    async def update_note(
        self, note_id: int, user_id: int, note_data: NoteUpdate
    ) -> Optional[Tuple[Note, Optional[Dict]]]:
        """Update a note with optional re-analysis."""
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
                    current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
                    analysis = await self.ai_service.deep_analyze_note(
                        content=note_data.content,
                        current_date=current_date,
                        categories=DEFAULT_CATEGORIES,
                        domains=DEFAULT_DOMAINS,
                        custom_prompt=note_data.custom_prompt,
                    )
                    analysis_result = analysis

                    # Apply analysis results
                    self._apply_deep_analysis_to_note(note, analysis)

                    # Re-process entities
                    try:
                        entities_data = analysis.get("entities", {})
                        if entities_data:
                            self.entity_service.process_note_entities(
                                note, entities_data, user_id
                            )
                    except Exception as entity_error:
                        logger.error(f"Entity re-processing failed: {entity_error}")

                except Exception as e:
                    logger.error(f"AI re-analysis failed: {e}")

        note.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(note)

        # Recalculate relations if content changed
        if note_data.content:
            try:
                self.relation_service.calculate_note_relations(note)
            except Exception as rel_error:
                logger.error(f"Relation recalculation failed: {rel_error}")

        return note, analysis_result

    def delete_note(self, note_id: int, user_id: int) -> bool:
        """Soft delete a note."""
        note = self.get_note(note_id, user_id)
        if not note:
            return False

        note.status = "deleted"
        note.updated_at = datetime.now()
        self.db.commit()

        return True

    def delete_all_notes(self, user_id: int, hard_delete: bool = False) -> int:
        """Delete all notes for a user (for debugging)."""
        query = self.db.query(Note).filter(Note.user_id == user_id)

        if hard_delete:
            count = query.count()
            query.delete(synchronize_session=False)
        else:
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
        """Search notes by keywords and filters."""
        query = self.db.query(Note).filter(
            Note.user_id == user_id,
            Note.status == "active",
        )

        if keywords:
            keyword_filters = []
            for keyword in keywords:
                keyword_pattern = f"%{keyword}%"
                keyword_filters.append(Note.title.ilike(keyword_pattern))
                keyword_filters.append(Note.raw_content.ilike(keyword_pattern))
                keyword_filters.append(Note.summary.ilike(keyword_pattern))
                keyword_filters.append(Note.core_topic.ilike(keyword_pattern))
            query = query.filter(or_(*keyword_filters))

        if category:
            query = query.filter(Note.category == category)

        if start_date:
            query = query.filter(Note.created_at >= start_date)
        if end_date:
            query = query.filter(Note.created_at <= end_date)

        if tags:
            for tag in tags:
                query = query.filter(Note._tags.contains(f'"{tag}"'))

        return query.order_by(desc(Note.created_at)).limit(limit).all()

    def get_recent_notes(self, user_id: int, limit: int = 100) -> List[Note]:
        """Get recent notes for relation calculation."""
        return (
            self.db.query(Note)
            .filter(Note.user_id == user_id, Note.status == "active")
            .order_by(desc(Note.created_at))
            .limit(limit)
            .all()
        )

    def get_related_notes(
        self,
        note_id: int,
        user_id: int,
        min_score: float = 0.2,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Get notes related to a given note.

        Returns list of dicts with note info and relation details.
        """
        related = self.relation_service.get_related_notes(
            note_id, user_id, min_score, limit
        )

        results = []
        for note, relation in related:
            results.append({
                "note": {
                    "id": note.id,
                    "title": note.title,
                    "summary": note.summary,
                    "category": note.category,
                    "created_at": note.created_at.isoformat() if note.created_at else None,
                },
                "relation": {
                    "type": relation.relation_type,
                    "score": relation.relation_score,
                    "shared_entities": relation.shared_entities,
                    "shared_keywords": relation.shared_keywords,
                },
            })

        return results

    def get_note_entities(self, note_id: int) -> List[Dict]:
        """Get entities associated with a note."""
        entities = self.entity_service.get_entities_for_note(note_id)

        return [
            {
                "id": e.id,
                "type": e.entity_type,
                "name": e.canonical_name,
                "aliases": e.aliases,
                "mention_count": e.mention_count,
            }
            for e in entities
        ]

    def get_note_with_relations(self, note_id: int, user_id: int) -> Optional[Dict]:
        """Get note with its entities and related notes."""
        note = self.get_note(note_id, user_id)
        if not note:
            return None

        return {
            "note": note,
            "entities": self.get_note_entities(note_id),
            "related_notes": self.get_related_notes(note_id, user_id),
        }
