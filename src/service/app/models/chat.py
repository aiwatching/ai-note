"""Chat session and message models."""
import json
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Table
from sqlalchemy.orm import relationship

from ..database import Base


# Association table for chat sessions and notes
chat_note_association = Table(
    "chat_note_association",
    Base.metadata,
    Column("chat_session_id", Integer, ForeignKey("chat_sessions.id"), primary_key=True),
    Column("note_id", Integer, ForeignKey("notes.id"), primary_key=True),
)


class ChatSession(Base):
    """Chat session model to store conversation history."""

    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Session metadata
    title = Column(String(200), nullable=True)  # Auto-generated or user-set title
    summary = Column(Text, nullable=True)  # Brief summary of the conversation

    # Providers used in this session
    _providers = Column("providers", Text, nullable=True)  # JSON array

    # Status
    status = Column(String(20), default="active", index=True)  # active, archived

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    messages = relationship(
        "ChatMessage",
        back_populates="session",
        order_by="ChatMessage.created_at",
        cascade="all, delete-orphan",
    )
    linked_notes = relationship(
        "Note",
        secondary=chat_note_association,
        backref="chat_sessions",
    )

    @property
    def providers(self) -> List[str]:
        if self._providers:
            return json.loads(self._providers)
        return []

    @providers.setter
    def providers(self, value: List[str]):
        self._providers = json.dumps(value, ensure_ascii=False) if value else None

    def __repr__(self):
        return f"<ChatSession(id={self.id}, title={self.title})>"


class ChatMessage(Base):
    """Individual chat message within a session."""

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)

    # Message content
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)

    # Provider info (for assistant messages)
    provider = Column(String(50), nullable=True)  # claude, deepseek, gemini, grok

    # For multi-provider responses, store all responses
    _all_responses = Column("all_responses", Text, nullable=True)  # JSON array

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")

    @property
    def all_responses(self) -> List[Dict[str, Any]]:
        """Get all provider responses for this message."""
        if self._all_responses:
            return json.loads(self._all_responses)
        return []

    @all_responses.setter
    def all_responses(self, value: List[Dict[str, Any]]):
        self._all_responses = json.dumps(value, ensure_ascii=False) if value else None

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, role={self.role}, provider={self.provider})>"
