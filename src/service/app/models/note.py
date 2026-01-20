"""Note model."""
import json
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..database import Base


class Note(Base):
    """Note model with AI analysis metadata."""

    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Basic information
    title = Column(String(200), nullable=True)
    raw_content = Column(Text, nullable=False)  # Original markdown content
    raw_file_path = Column(String(500), nullable=True)  # Path to raw markdown file
    organized_file_path = Column(String(500), nullable=True)  # Path to organized file

    # AI analysis results (stored as JSON strings)
    category = Column(String(50), nullable=True, index=True)
    subcategory = Column(String(50), nullable=True)
    _tags = Column("tags", Text, nullable=True)  # JSON array
    summary = Column(Text, nullable=True)

    # Special markers
    is_todo = Column(Boolean, default=False)
    is_schedule = Column(Boolean, default=False)
    priority = Column(String(20), nullable=True)  # high/medium/low
    status = Column(String(20), default="active", index=True)  # active/archived/deleted

    # Related information (stored as JSON)
    _related_persons = Column("related_persons", Text, nullable=True)
    _related_dates = Column("related_dates", Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    todos = relationship("Todo", back_populates="note", lazy="dynamic")
    schedules = relationship("Schedule", back_populates="note", lazy="dynamic")

    @property
    def tags(self) -> List[str]:
        """Get tags as list."""
        if self._tags:
            return json.loads(self._tags)
        return []

    @tags.setter
    def tags(self, value: List[str]):
        """Set tags from list."""
        self._tags = json.dumps(value, ensure_ascii=False) if value else None

    @property
    def related_persons(self) -> List[str]:
        """Get related persons as list."""
        if self._related_persons:
            return json.loads(self._related_persons)
        return []

    @related_persons.setter
    def related_persons(self, value: List[str]):
        """Set related persons from list."""
        self._related_persons = json.dumps(value, ensure_ascii=False) if value else None

    @property
    def related_dates(self) -> List[str]:
        """Get related dates as list."""
        if self._related_dates:
            return json.loads(self._related_dates)
        return []

    @related_dates.setter
    def related_dates(self, value: List[str]):
        """Set related dates from list."""
        self._related_dates = json.dumps(value, ensure_ascii=False) if value else None

    def __repr__(self):
        return f"<Note(id={self.id}, title={self.title}, category={self.category})>"
