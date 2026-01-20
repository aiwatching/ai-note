"""Todo model."""
from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..database import Base


class Todo(Base):
    """Todo/Task model."""

    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    note_id = Column(Integer, ForeignKey("notes.id"), nullable=True)

    # Todo information
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(Date, nullable=True, index=True)
    priority = Column(String(20), default="medium")  # high/medium/low
    status = Column(
        String(20), default="pending", index=True
    )  # pending/in_progress/completed/cancelled

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    note = relationship("Note", back_populates="todos")

    def __repr__(self):
        return f"<Todo(id={self.id}, title={self.title}, status={self.status})>"
