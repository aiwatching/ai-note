"""Entity model for standardized entity management."""
import json
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Table
from sqlalchemy.orm import relationship

from ..database import Base


# Many-to-many relationship between notes and entities
note_entity_association = Table(
    'note_entity_associations',
    Base.metadata,
    Column('note_id', Integer, ForeignKey('notes.id'), primary_key=True),
    Column('entity_id', Integer, ForeignKey('entities.id'), primary_key=True),
    Column('mention_context', Text, nullable=True),  # Context where entity was mentioned
    Column('created_at', DateTime, default=datetime.utcnow)
)


class Entity(Base):
    """
    Standardized entity model.

    Represents people, companies, projects, locations, and technical terms
    with alias management for name unification.
    """

    __tablename__ = "entities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Entity identification
    entity_type = Column(String(50), nullable=False, index=True)  # person, company, project, location, term
    canonical_name = Column(String(200), nullable=False, index=True)  # Standard name
    _aliases = Column("aliases", Text, nullable=True)  # JSON array of alternative names

    # Entity metadata
    description = Column(Text, nullable=True)
    _metadata = Column("metadata", Text, nullable=True)  # JSON object for extra info

    # Statistics
    mention_count = Column(Integer, default=0)
    first_note_id = Column(Integer, ForeignKey("notes.id"), nullable=True)
    last_note_id = Column(Integer, ForeignKey("notes.id"), nullable=True)
    first_seen_at = Column(DateTime, nullable=True)
    last_seen_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    # Note: Use 'linked_entities' to avoid conflict with Note.entities JSON property
    notes = relationship("Note", secondary=note_entity_association, backref="linked_entities")

    @property
    def aliases(self) -> List[str]:
        """Get aliases as list."""
        if self._aliases:
            return json.loads(self._aliases)
        return []

    @aliases.setter
    def aliases(self, value: List[str]):
        """Set aliases from list."""
        self._aliases = json.dumps(value, ensure_ascii=False) if value else None

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

    def add_alias(self, alias: str):
        """Add a new alias if not exists."""
        current = self.aliases
        if alias not in current and alias != self.canonical_name:
            current.append(alias)
            self.aliases = current

    def __repr__(self):
        return f"<Entity(id={self.id}, type={self.entity_type}, name={self.canonical_name})>"
