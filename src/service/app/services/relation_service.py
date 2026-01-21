"""Note relation service for calculating and managing relationships between notes."""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from loguru import logger
from sqlalchemy import and_, desc, or_
from sqlalchemy.orm import Session

from ..models.note import Note
from ..models.note_relation import NoteRelation
from .entity_service import EntityService


class RelationService:
    """Service for calculating and managing note relationships."""

    # Scoring weights for relation calculation
    WEIGHTS = {
        "entity_overlap": 0.30,  # 30% - Shared entities
        "topic_similarity": 0.25,  # 25% - Topic/keyword similarity
        "temporal_proximity": 0.15,  # 15% - Time proximity
        "reference_relation": 0.20,  # 20% - Follow-up signals
        "project_match": 0.10,  # 10% - Same project
    }

    # Thresholds
    MIN_RELATION_SCORE = 0.2  # Minimum score to create relation
    TEMPORAL_WINDOW_DAYS = 7  # Days for temporal proximity calculation
    MAX_RELATED_NOTES = 20  # Max related notes to store per note

    def __init__(self, db: Session):
        """Initialize relation service."""
        self.db = db
        self.entity_service = EntityService(db)

    def calculate_note_relations(
        self, note: Note, recent_notes: Optional[List[Note]] = None
    ) -> List[NoteRelation]:
        """
        Calculate relationships between a note and other notes.

        Args:
            note: The note to calculate relations for
            recent_notes: Optional list of notes to compare against.
                         If not provided, fetches recent notes for the user.

        Returns:
            List of created NoteRelation objects
        """
        if recent_notes is None:
            recent_notes = self._get_recent_notes(note.user_id, exclude_id=note.id)

        created_relations = []

        for other_note in recent_notes:
            if other_note.id == note.id:
                continue

            # Calculate multi-dimensional scores
            scores = self._calculate_scores(note, other_note)
            total_score = self._calculate_weighted_score(scores)

            if total_score >= self.MIN_RELATION_SCORE:
                relation = self._create_or_update_relation(
                    source_note=note,
                    target_note=other_note,
                    scores=scores,
                    total_score=total_score,
                )
                if relation:
                    created_relations.append(relation)

        self.db.commit()
        return created_relations

    def _calculate_scores(self, note1: Note, note2: Note) -> Dict[str, float]:
        """Calculate individual dimension scores between two notes."""
        scores = {
            "entity_overlap": self._calculate_entity_overlap(note1, note2),
            "topic_similarity": self._calculate_topic_similarity(note1, note2),
            "temporal_proximity": self._calculate_temporal_proximity(note1, note2),
            "reference_relation": self._calculate_reference_relation(note1, note2),
            "project_match": self._calculate_project_match(note1, note2),
        }
        return scores

    def _calculate_weighted_score(self, scores: Dict[str, float]) -> float:
        """Calculate weighted total score from individual scores."""
        total = 0.0
        for key, weight in self.WEIGHTS.items():
            total += scores.get(key, 0.0) * weight
        return total

    def _calculate_entity_overlap(self, note1: Note, note2: Note) -> float:
        """Calculate entity overlap score using Jaccard similarity."""
        return self.entity_service.calculate_entity_overlap_score(note1, note2)

    def _calculate_topic_similarity(self, note1: Note, note2: Note) -> float:
        """
        Calculate topic similarity based on keywords and domain.

        Uses Jaccard similarity on keywords plus domain bonus.
        """
        keywords1 = set(note1.keywords or [])
        keywords2 = set(note2.keywords or [])

        # Keyword similarity
        keyword_score = 0.0
        if keywords1 or keywords2:
            intersection = len(keywords1 & keywords2)
            union = len(keywords1 | keywords2)
            if union > 0:
                keyword_score = intersection / union

        # Domain match bonus
        domain_score = 0.0
        if note1.domain and note2.domain and note1.domain == note2.domain:
            domain_score = 0.3

        # Core topic similarity (simple check)
        topic_score = 0.0
        if note1.core_topic and note2.core_topic:
            # Check for keyword overlap in core topics
            words1 = set(note1.core_topic.lower().split())
            words2 = set(note2.core_topic.lower().split())
            common = words1 & words2
            if len(common) > 0:
                topic_score = min(len(common) / 3, 0.3)  # Max 0.3

        # Combine scores (weighted)
        return min(keyword_score * 0.5 + domain_score + topic_score, 1.0)

    def _calculate_temporal_proximity(self, note1: Note, note2: Note) -> float:
        """
        Calculate temporal proximity score.

        Notes created closer together get higher scores.
        """
        if not note1.created_at or not note2.created_at:
            return 0.0

        time_diff = abs((note1.created_at - note2.created_at).total_seconds())
        max_seconds = self.TEMPORAL_WINDOW_DAYS * 24 * 60 * 60

        if time_diff >= max_seconds:
            return 0.0

        # Linear decay
        return 1.0 - (time_diff / max_seconds)

    def _calculate_reference_relation(self, note1: Note, note2: Note) -> float:
        """
        Calculate reference relation score.

        Checks for follow-up indicators and reference keywords.
        """
        score = 0.0

        # Check if note1 is a follow-up that might reference note2
        if note1.is_follow_up:
            score += 0.3

            # Check reference keywords against note2's keywords
            ref_keywords = set(kw.lower() for kw in (note1.reference_keywords or []))
            note2_keywords = set(kw.lower() for kw in (note2.keywords or []))

            if ref_keywords & note2_keywords:
                score += 0.3

            # Check continuation topic
            if note1.continuation_topic:
                topic_lower = note1.continuation_topic.lower()
                if note2.core_topic and topic_lower in note2.core_topic.lower():
                    score += 0.4
                elif any(topic_lower in kw.lower() for kw in (note2.keywords or [])):
                    score += 0.2

        # Check the reverse direction too
        if note2.is_follow_up:
            ref_keywords = set(kw.lower() for kw in (note2.reference_keywords or []))
            note1_keywords = set(kw.lower() for kw in (note1.keywords or []))

            if ref_keywords & note1_keywords:
                score += 0.2

        return min(score, 1.0)

    def _calculate_project_match(self, note1: Note, note2: Note) -> float:
        """
        Calculate project match score.

        Checks if notes belong to the same project.
        """
        # Check entities for project match
        entities1 = note1.entities or {}
        entities2 = note2.entities or {}

        projects1 = set()
        projects2 = set()

        for p in entities1.get("projects", []):
            if isinstance(p, dict):
                projects1.add(p.get("name", "").lower())
            elif isinstance(p, str):
                projects1.add(p.lower())

        for p in entities2.get("projects", []):
            if isinstance(p, dict):
                projects2.add(p.get("name", "").lower())
            elif isinstance(p, str):
                projects2.add(p.lower())

        if projects1 and projects2:
            if projects1 & projects2:
                return 1.0

        # Check subcategory match as fallback
        if (
            note1.subcategory
            and note2.subcategory
            and note1.subcategory == note2.subcategory
        ):
            return 0.5

        return 0.0

    def _create_or_update_relation(
        self,
        source_note: Note,
        target_note: Note,
        scores: Dict[str, float],
        total_score: float,
    ) -> Optional[NoteRelation]:
        """Create or update a relation between two notes."""
        # Determine relation type based on highest score
        relation_type = self._determine_relation_type(scores)

        # Check for existing relation
        existing = (
            self.db.query(NoteRelation)
            .filter(
                NoteRelation.source_note_id == source_note.id,
                NoteRelation.target_note_id == target_note.id,
            )
            .first()
        )

        # Get shared entities and keywords for context
        shared_entities = self._get_shared_entity_names(source_note, target_note)
        shared_keywords = self._get_shared_keywords(source_note, target_note)

        if existing:
            # Update existing relation
            existing.relation_type = relation_type
            existing.relation_score = total_score
            existing.score_details = scores
            existing.shared_entities = shared_entities
            existing.shared_keywords = shared_keywords
            existing.updated_at = datetime.utcnow()
            return existing
        else:
            # Create new relation
            relation = NoteRelation(
                user_id=source_note.user_id,
                source_note_id=source_note.id,
                target_note_id=target_note.id,
                relation_type=relation_type,
                relation_score=total_score,
            )
            relation.score_details = scores
            relation.shared_entities = shared_entities
            relation.shared_keywords = shared_keywords

            self.db.add(relation)
            return relation

    def _determine_relation_type(self, scores: Dict[str, float]) -> str:
        """Determine primary relation type based on scores."""
        type_mapping = {
            "reference_relation": "follow_up",
            "project_match": "same_project",
            "topic_similarity": "same_topic",
            "temporal_proximity": "temporal",
            "entity_overlap": "related",
        }

        # Find highest scoring dimension
        max_key = max(scores, key=lambda k: scores[k])
        return type_mapping.get(max_key, "related")

    def _get_shared_entity_names(self, note1: Note, note2: Note) -> List[str]:
        """Get names of shared entities between two notes."""
        shared = self.entity_service.get_shared_entities(note1, note2)
        return [e.canonical_name for e in shared]

    def _get_shared_keywords(self, note1: Note, note2: Note) -> List[str]:
        """Get shared keywords between two notes."""
        keywords1 = set(kw.lower() for kw in (note1.keywords or []))
        keywords2 = set(kw.lower() for kw in (note2.keywords or []))
        return list(keywords1 & keywords2)

    def _get_recent_notes(
        self, user_id: int, exclude_id: Optional[int] = None, limit: int = 100
    ) -> List[Note]:
        """Get recent notes for a user."""
        query = self.db.query(Note).filter(
            Note.user_id == user_id,
            Note.status == "active",
        )

        if exclude_id:
            query = query.filter(Note.id != exclude_id)

        return query.order_by(desc(Note.created_at)).limit(limit).all()

    def get_related_notes(
        self,
        note_id: int,
        user_id: int,
        min_score: float = 0.2,
        limit: int = 10,
    ) -> List[Tuple[Note, NoteRelation]]:
        """
        Get notes related to a given note.

        Returns list of (Note, NoteRelation) tuples sorted by score.
        """
        # Get outgoing relations
        relations = (
            self.db.query(NoteRelation)
            .filter(
                NoteRelation.source_note_id == note_id,
                NoteRelation.user_id == user_id,
                NoteRelation.relation_score >= min_score,
            )
            .order_by(desc(NoteRelation.relation_score))
            .limit(limit)
            .all()
        )

        results = []
        for rel in relations:
            target_note = (
                self.db.query(Note)
                .filter(Note.id == rel.target_note_id, Note.status == "active")
                .first()
            )
            if target_note:
                results.append((target_note, rel))

        return results

    def get_relation_graph(
        self, user_id: int, note_ids: List[int], min_score: float = 0.3
    ) -> Dict:
        """
        Get relation graph for a set of notes.

        Returns nodes and edges for visualization.
        """
        relations = (
            self.db.query(NoteRelation)
            .filter(
                NoteRelation.user_id == user_id,
                NoteRelation.source_note_id.in_(note_ids),
                NoteRelation.target_note_id.in_(note_ids),
                NoteRelation.relation_score >= min_score,
            )
            .all()
        )

        nodes = []
        edges = []
        seen_nodes = set()

        for rel in relations:
            # Add source node
            if rel.source_note_id not in seen_nodes:
                source = (
                    self.db.query(Note)
                    .filter(Note.id == rel.source_note_id)
                    .first()
                )
                if source:
                    nodes.append(
                        {
                            "id": source.id,
                            "title": source.title or "Untitled",
                            "category": source.category,
                        }
                    )
                    seen_nodes.add(source.id)

            # Add target node
            if rel.target_note_id not in seen_nodes:
                target = (
                    self.db.query(Note)
                    .filter(Note.id == rel.target_note_id)
                    .first()
                )
                if target:
                    nodes.append(
                        {
                            "id": target.id,
                            "title": target.title or "Untitled",
                            "category": target.category,
                        }
                    )
                    seen_nodes.add(target.id)

            # Add edge
            edges.append(
                {
                    "source": rel.source_note_id,
                    "target": rel.target_note_id,
                    "type": rel.relation_type,
                    "score": rel.relation_score,
                }
            )

        return {"nodes": nodes, "edges": edges}

    def recalculate_all_relations(self, user_id: int) -> int:
        """
        Recalculate all relations for a user's notes.

        Returns count of relations created/updated.
        """
        notes = self._get_recent_notes(user_id, limit=500)
        count = 0

        for i, note in enumerate(notes):
            # Compare with notes that come after to avoid duplicates
            other_notes = notes[i + 1 :]
            relations = self.calculate_note_relations(note, other_notes)
            count += len(relations)

            if (i + 1) % 50 == 0:
                logger.info(f"Processed {i + 1}/{len(notes)} notes")
                self.db.commit()

        self.db.commit()
        logger.info(f"Created/updated {count} relations for user {user_id}")
        return count

    def cleanup_old_relations(
        self, user_id: int, days_old: int = 90
    ) -> int:
        """Remove relations older than specified days."""
        cutoff = datetime.utcnow() - timedelta(days=days_old)

        deleted = (
            self.db.query(NoteRelation)
            .filter(
                NoteRelation.user_id == user_id,
                NoteRelation.updated_at < cutoff,
            )
            .delete(synchronize_session=False)
        )

        self.db.commit()
        return deleted
