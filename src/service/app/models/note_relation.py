"""Note relation model for tracking relationships between notes."""
import json
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..database import Base


class NoteRelation(Base):
    """
    Represents relationship between two notes.

    Stores relationship type, strength, and detailed scoring breakdown.
    """

    __tablename__ = "note_relations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Related notes (source -> target)
    source_note_id = Column(Integer, ForeignKey("notes.id"), nullable=False, index=True)
    target_note_id = Column(Integer, ForeignKey("notes.id"), nullable=False, index=True)

    # Relationship type
    relation_type = Column(String(50), nullable=False, index=True)
    # Types: follow_up, same_project, same_topic, temporal, related

    # Overall relation score (0-1)
    relation_score = Column(Float, nullable=False, index=True)

    # Score breakdown (stored as JSON)
    _score_details = Column("score_details", Text, nullable=True)
    # {
    #   "entity_overlap": 0.4,      # 30% weight
    #   "topic_similarity": 0.3,    # 25% weight
    #   "temporal_proximity": 0.8,  # 15% weight
    #   "reference_relation": 0.6,  # 20% weight
    #   "project_match": 1.0        # 10% weight
    # }

    # Additional context
    _shared_entities = Column("shared_entities", Text, nullable=True)  # JSON array
    _shared_keywords = Column("shared_keywords", Text, nullable=True)  # JSON array

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    source_note = relationship("Note", foreign_keys=[source_note_id], backref="outgoing_relations")
    target_note = relationship("Note", foreign_keys=[target_note_id], backref="incoming_relations")

    @property
    def score_details(self) -> dict:
        """Get score details as dict."""
        if self._score_details:
            return json.loads(self._score_details)
        return {}

    @score_details.setter
    def score_details(self, value: dict):
        """Set score details from dict."""
        self._score_details = json.dumps(value, ensure_ascii=False) if value else None

    @property
    def shared_entities(self) -> list:
        """Get shared entities as list."""
        if self._shared_entities:
            return json.loads(self._shared_entities)
        return []

    @shared_entities.setter
    def shared_entities(self, value: list):
        """Set shared entities from list."""
        self._shared_entities = json.dumps(value, ensure_ascii=False) if value else None

    @property
    def shared_keywords(self) -> list:
        """Get shared keywords as list."""
        if self._shared_keywords:
            return json.loads(self._shared_keywords)
        return []

    @shared_keywords.setter
    def shared_keywords(self, value: list):
        """Set shared keywords from list."""
        self._shared_keywords = json.dumps(value, ensure_ascii=False) if value else None

    def __repr__(self):
        return f"<NoteRelation(source={self.source_note_id}, target={self.target_note_id}, type={self.relation_type}, score={self.relation_score})>"
