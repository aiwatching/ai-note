"""Content Organization Agent for managing note relationships and tags."""

from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from loguru import logger
from sqlalchemy import func
from sqlalchemy.orm import Session

from .base import BaseAgent
from .event_bus import Event, EventType
from ..database import SessionLocal
from ..models.note import Note


class ContentAgent(BaseAgent):
    """
    Content Organization Agent responsible for:
    - Analyzing note content similarity
    - Linking related notes
    - Optimizing and unifying tags
    - Building knowledge graph relationships
    - Generating content summaries
    """

    def __init__(
        self,
        interval_seconds: int = 300,  # Run every 5 minutes
        similarity_threshold: float = 0.3,  # Minimum similarity for linking
    ):
        """
        Initialize the Content Agent.

        Args:
            interval_seconds: How often to run analysis
            similarity_threshold: Threshold for considering notes related
        """
        super().__init__(
            name="content_agent",
            interval_seconds=interval_seconds,
        )
        self.similarity_threshold = similarity_threshold
        self._processed_notes: Set[int] = set()
        self._tag_cache: Dict[str, int] = {}

    async def setup(self) -> None:
        """Setup the agent - subscribe to relevant events."""
        if self.event_bus:
            self.event_bus.subscribe(EventType.NOTE_CREATED, self._on_note_created)
            self.event_bus.subscribe(EventType.NOTE_UPDATED, self._on_note_updated)

        logger.info(f"ContentAgent setup complete. Similarity threshold: {self.similarity_threshold}")

    async def cleanup(self) -> None:
        """Cleanup - unsubscribe from events."""
        if self.event_bus:
            self.event_bus.unsubscribe(EventType.NOTE_CREATED, self._on_note_created)
            self.event_bus.unsubscribe(EventType.NOTE_UPDATED, self._on_note_updated)

        self._processed_notes.clear()
        self._tag_cache.clear()
        logger.info("ContentAgent cleanup complete")

    async def run_cycle(self) -> None:
        """
        Main cycle - analyze notes and optimize organization.
        """
        db = SessionLocal()
        try:
            # Get notes that need processing
            unprocessed_notes = await self._get_unprocessed_notes(db)

            if unprocessed_notes:
                logger.info(f"Processing {len(unprocessed_notes)} notes")

                for note in unprocessed_notes:
                    await self._analyze_note(db, note)
                    self._processed_notes.add(note.id)

            # Periodically optimize tags (every 10 cycles)
            if self._run_count % 10 == 0:
                await self._optimize_tags(db)

            # Update metadata
            self.set_metadata("last_analysis", datetime.now().isoformat())
            self.set_metadata("notes_processed", len(self._processed_notes))

        except Exception as e:
            logger.error(f"Error in ContentAgent run cycle: {e}")
            raise
        finally:
            db.close()

    async def _get_unprocessed_notes(self, db: Session) -> List[Note]:
        """
        Get notes that haven't been processed for content analysis.

        Args:
            db: Database session

        Returns:
            List of notes to process
        """
        # Get recent notes not yet processed
        cutoff = datetime.now() - timedelta(hours=24)

        notes = (
            db.query(Note)
            .filter(
                Note.status == "active",
                Note.updated_at >= cutoff,
                ~Note.id.in_(self._processed_notes) if self._processed_notes else True,
            )
            .order_by(Note.updated_at.desc())
            .limit(50)
            .all()
        )

        return notes

    async def _analyze_note(self, db: Session, note: Note) -> None:
        """
        Analyze a single note for relationships and content.

        Args:
            db: Database session
            note: Note to analyze
        """
        logger.debug(f"Analyzing note: {note.id} - {note.title}")

        # Find related notes
        related = await self._find_related_notes(db, note)

        if related:
            logger.info(f"Found {len(related)} related notes for note {note.id}")
            await self._link_notes(note, related)

        # Update tag statistics
        if note.tags:
            for tag in note.tags:
                self._tag_cache[tag] = self._tag_cache.get(tag, 0) + 1

    async def _find_related_notes(
        self, db: Session, note: Note, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find notes related to the given note.

        Uses a simple keyword-based similarity:
        - Tags overlap
        - Category match
        - Keyword overlap in title/summary

        Args:
            db: Database session
            note: Note to find relations for
            limit: Maximum number of related notes

        Returns:
            List of related note info with similarity scores
        """
        related = []

        # Get other active notes
        other_notes = (
            db.query(Note)
            .filter(
                Note.id != note.id,
                Note.status == "active",
                Note.user_id == note.user_id,
            )
            .all()
        )

        for other in other_notes:
            similarity = self._calculate_similarity(note, other)
            if similarity >= self.similarity_threshold:
                related.append({
                    "note_id": other.id,
                    "title": other.title,
                    "similarity": similarity,
                    "common_tags": list(set(note.tags or []) & set(other.tags or [])),
                })

        # Sort by similarity and return top results
        related.sort(key=lambda x: x["similarity"], reverse=True)
        return related[:limit]

    def _calculate_similarity(self, note1: Note, note2: Note) -> float:
        """
        Calculate similarity between two notes.

        Uses a weighted combination of:
        - Tag overlap (40%)
        - Category match (30%)
        - Content keyword overlap (30%)

        Args:
            note1: First note
            note2: Second note

        Returns:
            Similarity score between 0 and 1
        """
        score = 0.0

        # Tag similarity (Jaccard index)
        tags1 = set(note1.tags or [])
        tags2 = set(note2.tags or [])
        if tags1 or tags2:
            tag_overlap = len(tags1 & tags2) / len(tags1 | tags2) if (tags1 | tags2) else 0
            score += 0.4 * tag_overlap

        # Category match
        if note1.category and note2.category:
            if note1.category == note2.category:
                score += 0.3
            elif note1.subcategory and note1.subcategory == note2.subcategory:
                score += 0.15

        # Content keyword overlap (simplified)
        keywords1 = self._extract_keywords(note1)
        keywords2 = self._extract_keywords(note2)
        if keywords1 or keywords2:
            keyword_overlap = len(keywords1 & keywords2) / len(keywords1 | keywords2) if (keywords1 | keywords2) else 0
            score += 0.3 * keyword_overlap

        return score

    def _extract_keywords(self, note: Note) -> Set[str]:
        """
        Extract keywords from a note.

        Args:
            note: Note to extract keywords from

        Returns:
            Set of keywords
        """
        keywords = set()

        # Add tags
        if note.tags:
            keywords.update(note.tags)

        # Add words from title
        if note.title:
            words = note.title.lower().split()
            keywords.update(w for w in words if len(w) > 2)

        # Add words from summary
        if note.summary:
            words = note.summary.lower().split()
            keywords.update(w for w in words if len(w) > 2)

        return keywords

    async def _link_notes(self, note: Note, related: List[Dict[str, Any]]) -> None:
        """
        Create links between related notes.

        Args:
            note: Source note
            related: List of related note info
        """
        if self.event_bus:
            await self.event_bus.emit(
                EventType.CONTENT_LINKED,
                {
                    "source_note_id": note.id,
                    "source_title": note.title,
                    "related_notes": related,
                },
                source=self.name,
            )

    async def _optimize_tags(self, db: Session) -> None:
        """
        Analyze and optimize tag usage across all notes.

        - Find similar/duplicate tags
        - Suggest tag consolidation
        - Report tag statistics
        """
        logger.info("Running tag optimization")

        # Get all tags from active notes
        notes = db.query(Note).filter(Note.status == "active").all()

        tag_counter = Counter()
        for note in notes:
            if note.tags:
                tag_counter.update(note.tags)

        # Find potential duplicate tags (similar spelling)
        suggestions = self._find_similar_tags(list(tag_counter.keys()))

        if suggestions:
            logger.info(f"Found {len(suggestions)} tag optimization suggestions")

            if self.event_bus:
                await self.event_bus.emit(
                    EventType.TAGS_OPTIMIZED,
                    {
                        "tag_statistics": dict(tag_counter.most_common(20)),
                        "suggestions": suggestions,
                        "total_unique_tags": len(tag_counter),
                    },
                    source=self.name,
                )

        # Update metadata
        self.set_metadata("tag_count", len(tag_counter))
        self.set_metadata("most_used_tags", dict(tag_counter.most_common(10)))

    def _find_similar_tags(self, tags: List[str]) -> List[Dict[str, Any]]:
        """
        Find tags that might be duplicates or variations.

        Args:
            tags: List of all tags

        Returns:
            List of suggestions for tag consolidation
        """
        suggestions = []
        processed = set()

        for i, tag1 in enumerate(tags):
            if tag1 in processed:
                continue

            similar = []
            for tag2 in tags[i + 1:]:
                if tag2 in processed:
                    continue

                # Check for similar tags (simple approach)
                if self._tags_similar(tag1, tag2):
                    similar.append(tag2)
                    processed.add(tag2)

            if similar:
                suggestions.append({
                    "primary": tag1,
                    "similar": similar,
                    "suggestion": f"Consider consolidating '{tag1}' with {similar}",
                })
                processed.add(tag1)

        return suggestions

    def _tags_similar(self, tag1: str, tag2: str) -> bool:
        """
        Check if two tags are similar (potential duplicates).

        Args:
            tag1: First tag
            tag2: Second tag

        Returns:
            True if tags are similar
        """
        t1 = tag1.lower().strip()
        t2 = tag2.lower().strip()

        # Exact match after normalization
        if t1 == t2:
            return True

        # One contains the other
        if t1 in t2 or t2 in t1:
            return True

        # Simple edit distance check (for short tags)
        if len(t1) < 10 and len(t2) < 10:
            if abs(len(t1) - len(t2)) <= 2:
                # Count character differences
                diff = sum(c1 != c2 for c1, c2 in zip(t1, t2))
                diff += abs(len(t1) - len(t2))
                if diff <= 2:
                    return True

        return False

    # Event handlers

    async def _on_note_created(self, event: Event) -> None:
        """Handle note created event."""
        note_id = event.data.get("note_id")
        if note_id:
            # Remove from processed set to trigger re-analysis
            self._processed_notes.discard(note_id)
            logger.debug(f"Note {note_id} created, will be analyzed in next cycle")

    async def _on_note_updated(self, event: Event) -> None:
        """Handle note updated event."""
        note_id = event.data.get("note_id")
        if note_id:
            # Remove from processed set to trigger re-analysis
            self._processed_notes.discard(note_id)
            logger.debug(f"Note {note_id} updated, will be re-analyzed in next cycle")

    # Public methods

    async def get_related_notes(self, note_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get related notes for a specific note.

        Args:
            note_id: ID of the note to find relations for
            limit: Maximum number of related notes

        Returns:
            List of related note info
        """
        db = SessionLocal()
        try:
            note = db.query(Note).filter(Note.id == note_id).first()
            if not note:
                return []

            return await self._find_related_notes(db, note, limit)
        finally:
            db.close()

    async def get_tag_statistics(self) -> Dict[str, Any]:
        """
        Get tag usage statistics.

        Returns:
            Tag statistics dictionary
        """
        db = SessionLocal()
        try:
            notes = db.query(Note).filter(Note.status == "active").all()

            tag_counter = Counter()
            category_counter = Counter()

            for note in notes:
                if note.tags:
                    tag_counter.update(note.tags)
                if note.category:
                    category_counter[note.category] += 1

            return {
                "total_notes": len(notes),
                "unique_tags": len(tag_counter),
                "top_tags": dict(tag_counter.most_common(20)),
                "categories": dict(category_counter),
            }
        finally:
            db.close()

    async def generate_daily_summary(self) -> Dict[str, Any]:
        """
        Generate a daily summary of note activity.

        Returns:
            Daily summary dictionary
        """
        db = SessionLocal()
        try:
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)

            # Notes created today
            notes_today = (
                db.query(Note)
                .filter(
                    Note.status == "active",
                    func.date(Note.created_at) == today,
                )
                .all()
            )

            # Notes from yesterday for comparison
            notes_yesterday = (
                db.query(Note)
                .filter(
                    Note.status == "active",
                    func.date(Note.created_at) == yesterday,
                )
                .count()
            )

            # Collect today's tags
            today_tags = Counter()
            today_categories = Counter()
            for note in notes_today:
                if note.tags:
                    today_tags.update(note.tags)
                if note.category:
                    today_categories[note.category] += 1

            return {
                "date": today.isoformat(),
                "notes_created": len(notes_today),
                "notes_yesterday": notes_yesterday,
                "change": len(notes_today) - notes_yesterday,
                "top_tags_today": dict(today_tags.most_common(5)),
                "categories_today": dict(today_categories),
                "titles": [n.title for n in notes_today if n.title],
            }
        finally:
            db.close()
