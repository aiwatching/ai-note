"""Note business logic service with simplified title-based analysis."""
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from loguru import logger
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from ..ai.factory import AIServiceFactory
from ..ai.prompts import DEFAULT_CATEGORIES, DEFAULT_DOMAINS
from ..config import get_settings
from ..models.note import Note
from ..models.note_relation import NoteRelation
from ..schemas.note_schema import AIAnalysisResult, NoteCreate, NoteUpdate
from .entity_service import EntityService
from .relation_service import RelationService


class NoteService:
    """Service for note-related operations with title-based analysis."""

    # Maximum number of related notes per note
    MAX_RELATED_NOTES = 2

    def __init__(self, db: Session):
        """Initialize note service."""
        self.db = db
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
        Create a new note with simple title extraction.

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

        # Run simple title extraction (always enabled for save)
        analysis_result = None
        if self.ai_service:
            try:
                logger.info(f"=== Extracting title for Note {note.id} ===")
                logger.info(f"Content length: {len(note_data.content)} chars")
                logger.info(f"Content preview: {note_data.content[:200]}...")

                # Simple title extraction
                title_result = await self.ai_service.extract_title(
                    content=note_data.content,
                    categories=DEFAULT_CATEGORIES,
                )

                logger.info(f"Title extracted: {title_result.get('title')}")
                logger.info(f"Category: {title_result.get('category')}")
                logger.info(f"Summary: {title_result.get('summary')}")

                # Apply title extraction result to note
                note.title = title_result.get("title")
                note.category = title_result.get("category", "个人杂记")
                note.summary = title_result.get("summary")

                analysis_result = {
                    "title": note.title,
                    "category": note.category,
                    "summary": note.summary,
                }

            except Exception as e:
                logger.error(f"Title extraction failed: {e}")
                # Continue without title extraction

        note.status = "active"
        self.db.commit()
        self.db.refresh(note)

        # Build title-based relationships (limit to MAX_RELATED_NOTES)
        try:
            self._build_title_based_relations(note, user_id)
            logger.debug(f"Built title-based relations for note {note.id}")
        except Exception as rel_error:
            logger.error(f"Title-based relation building failed: {rel_error}")

        return note, analysis_result

    def _build_title_based_relations(self, note: Note, user_id: int) -> List[NoteRelation]:
        """
        Build relationships based on title similarity.

        Find notes with similar titles and create relations (max 2 per note).
        """
        if not note.title:
            return []

        # Find notes with the same or similar title
        similar_notes = (
            self.db.query(Note)
            .filter(
                Note.user_id == user_id,
                Note.id != note.id,
                Note.status == "active",
                Note.title.isnot(None),
            )
            .all()
        )

        created_relations = []

        for other_note in similar_notes:
            if len(created_relations) >= self.MAX_RELATED_NOTES:
                break

            # Calculate title similarity
            similarity = self._calculate_title_similarity(note.title, other_note.title)

            if similarity >= 0.5:  # At least 50% similar
                # Create or update relation
                existing = (
                    self.db.query(NoteRelation)
                    .filter(
                        NoteRelation.source_note_id == note.id,
                        NoteRelation.target_note_id == other_note.id,
                    )
                    .first()
                )

                if existing:
                    existing.relation_type = "same_topic"
                    existing.relation_score = similarity
                    existing.updated_at = datetime.utcnow()
                else:
                    relation = NoteRelation(
                        user_id=user_id,
                        source_note_id=note.id,
                        target_note_id=other_note.id,
                        relation_type="same_topic",
                        relation_score=similarity,
                    )
                    self.db.add(relation)
                    created_relations.append(relation)

        self.db.commit()
        return created_relations

    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles (supports Chinese)."""
        import re

        if not title1 or not title2:
            return 0.0

        # Normalize titles
        t1 = title1.lower().strip()
        t2 = title2.lower().strip()

        # Exact match
        if t1 == t2:
            return 1.0

        # Extract key phrases (2-4 character combinations that appear in both)
        def extract_key_phrases(text: str) -> set:
            """Extract meaningful phrases from text."""
            cleaned = ''.join(c for c in text if c.isalnum())
            phrases = set()
            # Extract 2, 3, 4 character phrases
            for n in [2, 3, 4]:
                if len(cleaned) >= n:
                    for i in range(len(cleaned) - n + 1):
                        phrases.add(cleaned[i:i+n])
            return phrases

        phrases1 = extract_key_phrases(t1)
        phrases2 = extract_key_phrases(t2)

        if not phrases1 or not phrases2:
            return 0.0

        # Find common phrases
        common_phrases = phrases1 & phrases2

        # Check for significant common phrases (3+ characters)
        significant_common = [p for p in common_phrases if len(p) >= 3]

        # If they share significant phrases, boost the similarity
        if significant_common:
            # Calculate coverage: how much of the shorter title is covered by common phrases
            shorter_len = min(len(t1), len(t2))
            # Remove duplicates by using the longest common phrase
            max_common_len = max(len(p) for p in significant_common) if significant_common else 0

            # If they share a phrase of 3+ chars, consider them related
            # Similarity based on the length of shared content relative to title length
            coverage = max_common_len / shorter_len if shorter_len > 0 else 0

            # Boost: if they share "AI笔记" (4 chars) in titles of ~10 chars, that's significant
            if coverage >= 0.3:  # At least 30% overlap
                return 0.6 + (coverage * 0.4)  # 0.6 to 1.0 based on coverage

        # Fallback to n-gram Jaccard similarity
        ngrams1 = {t1[i:i+2] for i in range(len(t1) - 1)} if len(t1) >= 2 else {t1}
        ngrams2 = {t2[i:i+2] for i in range(len(t2) - 1)} if len(t2) >= 2 else {t2}

        intersection = len(ngrams1 & ngrams2)
        union = len(ngrams1 | ngrams2)

        if union == 0:
            return 0.0

        return intersection / union

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

            if note_data.reanalyze and self.ai_service:
                # Deep analysis requested (from "Analyze" button)
                try:
                    current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
                    logger.info(f"Deep re-analyzing note {note_id}...")
                    analysis = await self.ai_service.deep_analyze_note(
                        content=note_data.content,
                        current_date=current_date,
                        categories=DEFAULT_CATEGORIES,
                        domains=DEFAULT_DOMAINS,
                        custom_prompt=note_data.custom_prompt,
                    )
                    analysis_result = analysis

                    logger.info(f"=== AI Deep Re-Analysis Result for Note {note_id} ===")
                    logger.info(f"Title: {analysis.get('basic_info', {}).get('title')}")
                    logger.info(f"Category: {analysis.get('basic_info', {}).get('category')}")
                    logger.info(f"Summary: {analysis.get('basic_info', {}).get('summary')}")
                    logger.info(f"Keywords: {analysis.get('topic_analysis', {}).get('keywords')}")
                    logger.info(f"Key Points: {analysis.get('key_points', [])}")
                    logger.info("=== End Deep Re-Analysis Result ===")

                    # Apply deep analysis results
                    self._apply_deep_analysis_to_note(note, analysis)

                    # Process entities
                    try:
                        entities_data = analysis.get("entities", {})
                        if entities_data:
                            self.entity_service.process_note_entities(
                                note, entities_data, user_id
                            )
                    except Exception as entity_error:
                        logger.error(f"Entity processing failed: {entity_error}")

                except Exception as e:
                    logger.error(f"AI deep re-analysis failed: {e}")

            elif self.ai_service:
                # Simple title extraction (from "Save" button)
                try:
                    logger.info(f"Re-extracting title for note {note_id}...")
                    title_result = await self.ai_service.extract_title(
                        content=note_data.content,
                        categories=DEFAULT_CATEGORIES,
                    )

                    logger.info(f"Title re-extracted: {title_result.get('title')}")

                    note.title = title_result.get("title")
                    note.category = title_result.get("category", note.category or "个人杂记")
                    note.summary = title_result.get("summary")

                    analysis_result = {
                        "title": note.title,
                        "category": note.category,
                        "summary": note.summary,
                    }

                except Exception as e:
                    logger.error(f"Title re-extraction failed: {e}")

        note.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(note)

        # Rebuild title-based relations if content changed
        if note_data.content:
            try:
                # Clear old relations and rebuild
                self.db.query(NoteRelation).filter(
                    NoteRelation.source_note_id == note_id
                ).delete(synchronize_session=False)
                self.db.commit()

                self._build_title_based_relations(note, user_id)
            except Exception as rel_error:
                logger.error(f"Title-based relation rebuild failed: {rel_error}")

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

    def delete_relation(self, source_note_id: int, target_note_id: int) -> bool:
        """Delete a relation between two notes."""
        # Delete both directions
        deleted_count = (
            self.db.query(NoteRelation)
            .filter(
                or_(
                    (NoteRelation.source_note_id == source_note_id) &
                    (NoteRelation.target_note_id == target_note_id),
                    (NoteRelation.source_note_id == target_note_id) &
                    (NoteRelation.target_note_id == source_note_id),
                )
            )
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return deleted_count > 0

    def recalculate_all_relations(self, user_id: int) -> int:
        """
        Recalculate title-based relations for all notes.

        Returns the number of relations created.
        """
        # Clear existing title-based relations
        self.db.query(NoteRelation).filter(
            NoteRelation.user_id == user_id,
            NoteRelation.relation_type == "same_topic"
        ).delete(synchronize_session=False)
        self.db.commit()

        # Get all active notes
        notes = (
            self.db.query(Note)
            .filter(Note.user_id == user_id, Note.status == "active")
            .all()
        )

        total_relations = 0
        for note in notes:
            relations = self._build_title_based_relations(note, user_id)
            total_relations += len(relations)
            logger.info(f"Built {len(relations)} relations for note {note.id} ({note.title})")

        return total_relations

    def get_suggested_relations(
        self, note_id: int, user_id: int, min_similarity: float = 0.2
    ) -> List[Dict]:
        """
        Get suggested notes that might be related to the given note.

        Returns notes with similarity score for user to decide whether to link.
        """
        note = self.get_note(note_id, user_id)
        if not note or not note.title:
            return []

        # Get all other notes
        other_notes = (
            self.db.query(Note)
            .filter(
                Note.user_id == user_id,
                Note.id != note_id,
                Note.status == "active",
                Note.title.isnot(None),
            )
            .all()
        )

        suggestions = []
        for other in other_notes:
            similarity = self._calculate_title_similarity(note.title, other.title)

            if similarity >= min_similarity:
                # Check if already linked
                existing = (
                    self.db.query(NoteRelation)
                    .filter(
                        or_(
                            (NoteRelation.source_note_id == note_id) &
                            (NoteRelation.target_note_id == other.id),
                            (NoteRelation.source_note_id == other.id) &
                            (NoteRelation.target_note_id == note_id),
                        )
                    )
                    .first()
                )

                suggestions.append({
                    "note_id": other.id,
                    "title": other.title,
                    "category": other.category,
                    "summary": other.summary,
                    "created_at": other.created_at.isoformat() if other.created_at else None,
                    "similarity": round(similarity, 3),
                    "is_linked": existing is not None,
                })

        # Sort by similarity (highest first)
        suggestions.sort(key=lambda x: x["similarity"], reverse=True)

        return suggestions

    def create_manual_relation(
        self, source_note_id: int, target_note_id: int, user_id: int
    ) -> bool:
        """
        Manually create a relation between two notes.

        Returns True if created, False if already exists.
        """
        # Check if already exists
        existing = (
            self.db.query(NoteRelation)
            .filter(
                NoteRelation.source_note_id == source_note_id,
                NoteRelation.target_note_id == target_note_id,
            )
            .first()
        )

        if existing:
            return False

        relation = NoteRelation(
            user_id=user_id,
            source_note_id=source_note_id,
            target_note_id=target_note_id,
            relation_type="manual",  # User-created relation
            relation_score=1.0,  # Max score for manual links
        )
        self.db.add(relation)
        self.db.commit()

        return True

    def get_notes_grouped_by_title(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        category: Optional[str] = None,
    ) -> Tuple[List[Dict], int]:
        """
        Get notes grouped by title for the notes list view.

        Returns list of groups, each containing notes with the same title.
        """
        query = self.db.query(Note).filter(
            Note.user_id == user_id,
            Note.status == "active",
        )

        if category:
            query = query.filter(Note.category == category)

        # Get all notes ordered by title then by created_at
        notes = query.order_by(Note.title, desc(Note.created_at)).all()

        # Group notes by title
        groups = {}
        for note in notes:
            title = note.title or "无标题"
            if title not in groups:
                groups[title] = {
                    "title": title,
                    "notes": [],
                    "latest_updated_at": note.updated_at,
                }
            groups[title]["notes"].append(note)
            # Update latest timestamp
            if note.updated_at > groups[title]["latest_updated_at"]:
                groups[title]["latest_updated_at"] = note.updated_at

        # Convert to list and sort by latest update
        grouped_list = sorted(
            groups.values(),
            key=lambda g: g["latest_updated_at"],
            reverse=True
        )

        total = len(grouped_list)

        # Paginate
        offset = (page - 1) * page_size
        paginated = grouped_list[offset:offset + page_size]

        return paginated, total
