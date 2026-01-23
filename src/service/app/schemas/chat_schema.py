"""Chat schema definitions."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class ChatMessage(BaseModel):
    """A single chat message."""
    role: str  # "user" or "assistant"
    content: str
    provider: Optional[str] = None  # Which AI provider responded
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """Request to send a chat message."""
    message: str
    providers: List[str]  # ["claude", "deepseek", "gemini", "grok"]
    note_ids: Optional[List[int]] = None  # Optional note IDs to include as context
    conversation_history: Optional[List[ChatMessage]] = None
    session_id: Optional[int] = None  # Optional session ID to continue


class ProviderResponse(BaseModel):
    """Response from a single AI provider."""
    provider: str
    content: str
    error: Optional[str] = None


class ChatResponse(BaseModel):
    """Response containing replies from multiple providers."""
    responses: List[ProviderResponse]
    note_context: Optional[str] = None  # Summary of included notes
    session_id: Optional[int] = None  # Session ID for continuing conversation


# ===== Session Management Schemas =====

class ChatSessionCreate(BaseModel):
    """Request to create a new chat session."""
    title: Optional[str] = None
    providers: List[str]
    note_ids: Optional[List[int]] = None


class ChatSessionUpdate(BaseModel):
    """Request to update a chat session."""
    title: Optional[str] = None
    status: Optional[str] = None  # active, archived


class ChatMessageOut(BaseModel):
    """Output schema for chat message."""
    id: int
    role: str
    content: str
    provider: Optional[str] = None
    all_responses: List[Dict[str, Any]] = []
    created_at: datetime

    class Config:
        from_attributes = True


class ChatSessionOut(BaseModel):
    """Output schema for chat session."""
    id: int
    title: Optional[str] = None
    summary: Optional[str] = None
    providers: List[str] = []
    status: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    linked_note_ids: List[int] = []

    class Config:
        from_attributes = True


class ChatSessionDetail(BaseModel):
    """Detailed chat session with messages."""
    id: int
    title: Optional[str] = None
    summary: Optional[str] = None
    providers: List[str] = []
    status: str
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageOut] = []
    linked_note_ids: List[int] = []

    class Config:
        from_attributes = True


class ChatSessionList(BaseModel):
    """Paginated list of chat sessions."""
    items: List[ChatSessionOut]
    total: int
    page: int
    page_size: int


class ExportToNoteRequest(BaseModel):
    """Request to export chat session to a note."""
    title: Optional[str] = None  # Override the default title
    include_all_providers: bool = True  # Include responses from all providers
