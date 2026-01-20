"""Schedule model."""
import json
from datetime import datetime
from typing import List

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..database import Base


class Schedule(Base):
    """Schedule/Calendar event model."""

    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    note_id = Column(Integer, ForeignKey("notes.id"), nullable=True)

    # Schedule information
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(200), nullable=True)
    _participants = Column("participants", Text, nullable=True)  # JSON array

    # Time information
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=True)
    is_all_day = Column(Boolean, default=False)
    recurrence = Column(String(50), nullable=True)  # daily/weekly/monthly

    # Reminder
    reminder_minutes = Column(Integer, nullable=True)

    # Status
    status = Column(
        String(20), default="scheduled", index=True
    )  # scheduled/completed/cancelled

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    note = relationship("Note", back_populates="schedules")

    @property
    def participants(self) -> List[str]:
        """Get participants as list."""
        if self._participants:
            return json.loads(self._participants)
        return []

    @participants.setter
    def participants(self, value: List[str]):
        """Set participants from list."""
        self._participants = json.dumps(value, ensure_ascii=False) if value else None

    def __repr__(self):
        return f"<Schedule(id={self.id}, title={self.title}, start_time={self.start_time})>"
