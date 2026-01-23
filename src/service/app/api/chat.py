"""Chat API routes."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.chat_schema import (
    ChatRequest,
    ChatResponse,
    ProviderResponse,
    ChatSessionCreate,
    ChatSessionUpdate,
    ChatSessionOut,
    ChatSessionDetail,
    ChatSessionList,
    ChatMessageOut,
    ExportToNoteRequest,
)
from ..services.chat_service import ChatService

router = APIRouter()

# Default user ID for MVP
DEFAULT_USER_ID = 1


@router.get("/providers")
async def get_available_providers(
    db: Session = Depends(get_db),
):
    """
    Get list of available AI providers.

    Returns providers that have API keys configured.
    """
    service = ChatService(db)
    providers = service.get_available_providers()

    return {
        "providers": providers,
        "descriptions": {
            "claude": "Anthropic Claude - 强大的推理和分析能力",
            "deepseek": "DeepSeek - 高性价比的中文对话",
            "gemini": "Google Gemini - 多模态理解能力",
            "grok": "xAI Grok - 实时信息和幽默风格",
        }
    }


@router.post("", response_model=ChatResponse)
async def send_chat_message(
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    """
    Send a message to one or more AI providers.

    Supports:
    - Multiple providers in parallel
    - Including note content as context
    - Session-based conversation (auto-saves history)
    """
    service = ChatService(db)

    # Use session-based chat if session_id provided or for new conversations
    result = await service.chat_with_session(
        message=request.message,
        providers=request.providers,
        user_id=DEFAULT_USER_ID,
        session_id=request.session_id,
        note_ids=request.note_ids,
    )

    return ChatResponse(
        responses=[
            ProviderResponse(
                provider=r["provider"],
                content=r["content"],
                error=r.get("error")
            )
            for r in result["responses"]
        ],
        note_context=result.get("note_context"),
        session_id=result.get("session_id"),
    )


# ===== Session Management Endpoints =====

@router.get("/sessions", response_model=ChatSessionList)
async def list_chat_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List all chat sessions for the current user."""
    service = ChatService(db)
    result = service.list_sessions(
        user_id=DEFAULT_USER_ID,
        page=page,
        page_size=page_size,
        status=status,
    )

    items = []
    for session in result["items"]:
        items.append(ChatSessionOut(
            id=session.id,
            title=session.title,
            summary=session.summary,
            providers=session.providers,
            status=session.status,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=len(list(session.messages)),
            linked_note_ids=[n.id for n in session.linked_notes],
        ))

    return ChatSessionList(
        items=items,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.post("/sessions", response_model=ChatSessionOut)
async def create_chat_session(
    request: ChatSessionCreate,
    db: Session = Depends(get_db),
):
    """Create a new chat session."""
    service = ChatService(db)
    session = service.create_session(
        user_id=DEFAULT_USER_ID,
        providers=request.providers,
        title=request.title,
        note_ids=request.note_ids,
    )

    return ChatSessionOut(
        id=session.id,
        title=session.title,
        summary=session.summary,
        providers=session.providers,
        status=session.status,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=0,
        linked_note_ids=[n.id for n in session.linked_notes],
    )


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
async def get_chat_session(
    session_id: int,
    db: Session = Depends(get_db),
):
    """Get a chat session with all messages."""
    service = ChatService(db)
    session = service.get_session(session_id, DEFAULT_USER_ID)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = [
        ChatMessageOut(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            provider=msg.provider,
            all_responses=msg.all_responses,
            created_at=msg.created_at,
        )
        for msg in session.messages
    ]

    return ChatSessionDetail(
        id=session.id,
        title=session.title,
        summary=session.summary,
        providers=session.providers,
        status=session.status,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=messages,
        linked_note_ids=[n.id for n in session.linked_notes],
    )


@router.patch("/sessions/{session_id}", response_model=ChatSessionOut)
async def update_chat_session(
    session_id: int,
    request: ChatSessionUpdate,
    db: Session = Depends(get_db),
):
    """Update a chat session (title, status)."""
    service = ChatService(db)
    session = service.update_session(
        session_id=session_id,
        user_id=DEFAULT_USER_ID,
        title=request.title,
        status=request.status,
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return ChatSessionOut(
        id=session.id,
        title=session.title,
        summary=session.summary,
        providers=session.providers,
        status=session.status,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=len(list(session.messages)),
        linked_note_ids=[n.id for n in session.linked_notes],
    )


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: int,
    db: Session = Depends(get_db),
):
    """Delete a chat session."""
    service = ChatService(db)
    success = service.delete_session(session_id, DEFAULT_USER_ID)

    if not success:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"success": True, "message": "Session deleted"}


@router.post("/sessions/{session_id}/link-notes")
async def link_notes_to_session(
    session_id: int,
    note_ids: list[int],
    db: Session = Depends(get_db),
):
    """Link notes to a chat session."""
    service = ChatService(db)
    session = service.link_notes_to_session(
        session_id=session_id,
        user_id=DEFAULT_USER_ID,
        note_ids=note_ids,
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "success": True,
        "linked_note_ids": [n.id for n in session.linked_notes],
    }


@router.post("/sessions/{session_id}/export-to-note")
async def export_session_to_note(
    session_id: int,
    request: ExportToNoteRequest,
    db: Session = Depends(get_db),
):
    """Export a chat session to a new note."""
    service = ChatService(db)
    note = service.export_to_note(
        session_id=session_id,
        user_id=DEFAULT_USER_ID,
        title=request.title,
        include_all_providers=request.include_all_providers,
    )

    if not note:
        raise HTTPException(status_code=404, detail="Session not found or empty")

    return {
        "success": True,
        "note_id": note.id,
        "note_title": note.title,
    }


@router.get("/by-note/{note_id}", response_model=list[ChatSessionOut])
async def get_sessions_by_note(
    note_id: int,
    db: Session = Depends(get_db),
):
    """Get all chat sessions linked to a specific note."""
    service = ChatService(db)
    sessions = service.get_sessions_by_note(note_id, DEFAULT_USER_ID)

    return [
        ChatSessionOut(
            id=session.id,
            title=session.title,
            summary=session.summary,
            providers=session.providers,
            status=session.status,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=len(list(session.messages)),
            linked_note_ids=[n.id for n in session.linked_notes],
        )
        for session in sessions
    ]
