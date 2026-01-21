"""Aggregated document model for storing intelligently combined notes."""
import json
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Table
from sqlalchemy.orm import relationship

from ..database import Base


# Many-to-many relationship between aggregated documents and notes
aggregated_note_association = Table(
    'aggregated_note_associations',
    Base.metadata,
    Column('document_id', Integer, ForeignKey('aggregated_documents.id'), primary_key=True),
    Column('note_id', Integer, ForeignKey('notes.id'), primary_key=True),
    Column('order_index', Integer, default=0),  # Order of note in the document
    Column('created_at', DateTime, default=datetime.utcnow)
)


class AggregatedDocument(Base):
    """
    Aggregated document combining multiple related notes.

    Types:
    - project: Notes grouped by project
    - topic: Notes grouped by topic/theme
    - timeline: Chronological view of entity activity
    - entity_report: Report about a specific entity
    """

    __tablename__ = "aggregated_documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Document identification
    doc_type = Column(String(50), nullable=False, index=True)  # project, topic, timeline, entity_report
    title = Column(String(500), nullable=False)
    identifier = Column(String(200), nullable=True, index=True)  # Project name, topic name, entity name

    # Content
    summary = Column(Text, nullable=True)  # AI-generated summary
    content = Column(Text, nullable=True)  # Full markdown content
    file_path = Column(String(500), nullable=True)  # Path to markdown file

    # Metadata (stored as JSON)
    _metadata = Column("metadata", Text, nullable=True)
    # {
    #   "note_count": 10,
    #   "key_points": [...],
    #   "todos": [...],
    #   "questions": [...],
    #   "decisions": [...],
    #   "next_actions": [...]
    # }

    # Related entity (for timeline and entity_report types)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=True)

    # Statistics
    note_count = Column(Integer, default=0)
    last_note_at = Column(DateTime, nullable=True)

    # Status
    status = Column(String(20), default="active", index=True)  # active, archived, stale

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    notes = relationship("Note", secondary=aggregated_note_association, backref="aggregated_documents")
    entity = relationship("Entity", backref="aggregated_documents")

    @property
    def metadata_dict(self) -> dict:
        """Get metadata as dict."""
        if self._metadata:
            return json.loads(self._metadata)
        return {}

    @metadata_dict.setter
    def metadata_dict(self, value: dict):
        """Set metadata from dict."""
        self._metadata = json.dumps(value, ensure_ascii=False) if value else None

    def __repr__(self):
        return f"<AggregatedDocument(id={self.id}, type={self.doc_type}, title={self.title})>"
