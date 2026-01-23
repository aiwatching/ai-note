"""Chat service for multi-provider AI conversations."""
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any

from loguru import logger
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..ai.claude_service import ClaudeService
from ..ai.deepseek_service import DeepSeekService
from ..ai.gemini_service import GeminiService
from ..ai.grok_service import GrokService
from ..config import get_settings
from ..models.note import Note
from ..models.chat import ChatSession, ChatMessage


class ChatService:
    """Service for multi-provider AI chat."""

    def __init__(self, db: Session):
        """Initialize chat service."""
        self.db = db
        self._providers: Dict[str, Any] = {}
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize available AI providers."""
        settings = get_settings()

        if settings.claude_api_key:
            self._providers["claude"] = ClaudeService(
                api_key=settings.claude_api_key,
                model=settings.claude_model,
            )
            logger.info("Claude provider initialized")

        if settings.deepseek_api_key:
            self._providers["deepseek"] = DeepSeekService(
                api_key=settings.deepseek_api_key,
                model=settings.deepseek_model,
                base_url=settings.deepseek_base_url,
            )
            logger.info("DeepSeek provider initialized")

        if settings.gemini_api_key:
            self._providers["gemini"] = GeminiService(
                api_key=settings.gemini_api_key,
                model=settings.gemini_model,
            )
            logger.info("Gemini provider initialized")

        if settings.grok_api_key:
            self._providers["grok"] = GrokService(
                api_key=settings.grok_api_key,
                model=settings.grok_model,
                base_url=settings.grok_base_url,
            )
            logger.info("Grok provider initialized")

    def get_available_providers(self) -> List[str]:
        """Get list of available providers."""
        return list(self._providers.keys())

    def _build_note_context(self, note_ids: List[int], user_id: int) -> str:
        """Build context string from notes."""
        notes = (
            self.db.query(Note)
            .filter(Note.id.in_(note_ids), Note.user_id == user_id)
            .all()
        )

        if not notes:
            return ""

        context_parts = ["以下是相关的笔记内容，请参考：\n"]
        for note in notes:
            context_parts.append(f"---\n【笔记 #{note.id}】{note.title or '无标题'}\n")
            context_parts.append(f"{note.raw_content}\n")

        context_parts.append("---\n")
        return "\n".join(context_parts)

    async def _chat_with_provider(
        self,
        provider_name: str,
        messages: List[Dict],
        max_tokens: int = 2048,
    ) -> Dict:
        """Chat with a single provider."""
        if provider_name not in self._providers:
            return {
                "provider": provider_name,
                "content": "",
                "error": f"Provider '{provider_name}' not configured"
            }

        provider = self._providers[provider_name]
        try:
            response = await provider.chat(messages, max_tokens)
            return {
                "provider": provider_name,
                "content": response,
                "error": None
            }
        except Exception as e:
            logger.error(f"Chat error with {provider_name}: {e}")
            return {
                "provider": provider_name,
                "content": "",
                "error": str(e)
            }

    async def chat(
        self,
        message: str,
        providers: List[str],
        user_id: int,
        note_ids: Optional[List[int]] = None,
        conversation_history: Optional[List[Dict]] = None,
        max_tokens: int = 2048,
    ) -> Dict:
        """
        Send a message to multiple AI providers.

        Args:
            message: User message
            providers: List of provider names to use
            user_id: Current user ID
            note_ids: Optional list of note IDs to include as context
            conversation_history: Previous messages in the conversation
            max_tokens: Maximum tokens for response

        Returns:
            Dict with responses from each provider
        """
        # Build messages list
        messages = []

        # Add system message
        system_content = "你是一个智能助手，可以帮助用户回答问题、分析内容、提供建议。请用中文回答。"

        # Add note context if provided
        note_context = ""
        if note_ids:
            note_context = self._build_note_context(note_ids, user_id)
            if note_context:
                system_content += f"\n\n{note_context}"

        messages.append({"role": "system", "content": system_content})

        # Add conversation history
        if conversation_history:
            for hist_msg in conversation_history:
                messages.append({
                    "role": hist_msg.get("role", "user"),
                    "content": hist_msg.get("content", "")
                })

        # Add current message
        messages.append({"role": "user", "content": message})

        # Filter to available providers
        available = self.get_available_providers()
        valid_providers = [p for p in providers if p in available]

        if not valid_providers:
            return {
                "responses": [{
                    "provider": "system",
                    "content": "",
                    "error": f"No valid providers. Available: {available}"
                }],
                "note_context": note_context if note_ids else None
            }

        # Send to all providers in parallel
        tasks = [
            self._chat_with_provider(provider, messages, max_tokens)
            for provider in valid_providers
        ]
        responses = await asyncio.gather(*tasks)

        return {
            "responses": list(responses),
            "note_context": note_context if note_ids else None
        }

    # ===== Session Management Methods =====

    def create_session(
        self,
        user_id: int,
        providers: List[str],
        title: Optional[str] = None,
        note_ids: Optional[List[int]] = None,
    ) -> ChatSession:
        """Create a new chat session."""
        session = ChatSession(
            user_id=user_id,
            title=title,
            providers=providers,
        )

        # Link notes if provided
        if note_ids:
            notes = self.db.query(Note).filter(
                Note.id.in_(note_ids),
                Note.user_id == user_id
            ).all()
            session.linked_notes = notes

        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_session(self, session_id: int, user_id: int) -> Optional[ChatSession]:
        """Get a chat session by ID."""
        return self.db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id
        ).first()

    def list_sessions(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> Dict:
        """List chat sessions for a user."""
        query = self.db.query(ChatSession).filter(
            ChatSession.user_id == user_id
        )

        if status:
            query = query.filter(ChatSession.status == status)

        total = query.count()
        sessions = (
            query
            .order_by(desc(ChatSession.updated_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return {
            "items": sessions,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_sessions_by_note(self, note_id: int, user_id: int) -> List[ChatSession]:
        """Get all chat sessions linked to a specific note."""
        note = self.db.query(Note).filter(
            Note.id == note_id,
            Note.user_id == user_id
        ).first()

        if not note:
            return []

        # Get sessions through the relationship
        return (
            self.db.query(ChatSession)
            .filter(ChatSession.user_id == user_id)
            .filter(ChatSession.linked_notes.any(Note.id == note_id))
            .order_by(desc(ChatSession.updated_at))
            .all()
        )

    def update_session(
        self,
        session_id: int,
        user_id: int,
        title: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[ChatSession]:
        """Update a chat session."""
        session = self.get_session(session_id, user_id)
        if not session:
            return None

        if title is not None:
            session.title = title
        if status is not None:
            session.status = status

        session.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(session)
        return session

    def delete_session(self, session_id: int, user_id: int) -> bool:
        """Delete a chat session."""
        session = self.get_session(session_id, user_id)
        if not session:
            return False

        self.db.delete(session)
        self.db.commit()
        return True

    def add_message(
        self,
        session_id: int,
        role: str,
        content: str,
        provider: Optional[str] = None,
        all_responses: Optional[List[Dict]] = None,
    ) -> ChatMessage:
        """Add a message to a session."""
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            provider=provider,
        )
        if all_responses:
            message.all_responses = all_responses

        self.db.add(message)

        # Update session timestamp
        session = self.db.query(ChatSession).filter(
            ChatSession.id == session_id
        ).first()
        if session:
            session.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(message)
        return message

    def get_session_messages(self, session_id: int, user_id: int) -> List[ChatMessage]:
        """Get all messages in a session."""
        session = self.get_session(session_id, user_id)
        if not session:
            return []
        return list(session.messages)

    def link_notes_to_session(
        self,
        session_id: int,
        user_id: int,
        note_ids: List[int],
    ) -> Optional[ChatSession]:
        """Link notes to a chat session."""
        session = self.get_session(session_id, user_id)
        if not session:
            return None

        notes = self.db.query(Note).filter(
            Note.id.in_(note_ids),
            Note.user_id == user_id
        ).all()

        # Add new notes (avoid duplicates)
        existing_ids = {n.id for n in session.linked_notes}
        for note in notes:
            if note.id not in existing_ids:
                session.linked_notes.append(note)

        session.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(session)
        return session

    def export_to_note(
        self,
        session_id: int,
        user_id: int,
        title: Optional[str] = None,
        include_all_providers: bool = True,
    ) -> Optional[Note]:
        """Export chat session to a new note."""
        session = self.get_session(session_id, user_id)
        if not session:
            return None

        messages = self.get_session_messages(session_id, user_id)
        if not messages:
            return None

        # Build note content
        content_parts = []
        content_parts.append(f"# {title or session.title or 'AI 对话记录'}\n")
        content_parts.append(f"*导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")
        content_parts.append(f"*使用的 AI 模型: {', '.join(session.providers)}*\n")
        content_parts.append("---\n")

        for msg in messages:
            if msg.role == "user":
                content_parts.append(f"## 👤 用户\n\n{msg.content}\n")
            else:
                if include_all_providers and msg.all_responses:
                    for resp in msg.all_responses:
                        provider_name = resp.get("provider", "AI")
                        resp_content = resp.get("content", "")
                        error = resp.get("error")
                        content_parts.append(f"## 🤖 {provider_name.upper()}\n")
                        if error:
                            content_parts.append(f"*错误: {error}*\n")
                        else:
                            content_parts.append(f"\n{resp_content}\n")
                else:
                    provider_name = msg.provider or "AI"
                    content_parts.append(f"## 🤖 {provider_name.upper()}\n\n{msg.content}\n")

        # Create note
        note = Note(
            user_id=user_id,
            title=title or session.title or "AI 对话记录",
            raw_content="\n".join(content_parts),
            category="AI对话",
            content_type="chat_export",
        )

        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)

        # Link the note to the session
        session.linked_notes.append(note)
        self.db.commit()

        return note

    async def chat_with_session(
        self,
        message: str,
        providers: List[str],
        user_id: int,
        session_id: Optional[int] = None,
        note_ids: Optional[List[int]] = None,
        max_tokens: int = 2048,
    ) -> Dict:
        """
        Send a message with session management.

        If session_id is provided, continues the conversation.
        Otherwise creates a new session.
        """
        # Get or create session
        session = None
        if session_id:
            session = self.get_session(session_id, user_id)

        if not session:
            # Create new session
            session = self.create_session(
                user_id=user_id,
                providers=providers,
                note_ids=note_ids,
            )

        # Get conversation history from session
        history = []
        for msg in session.messages:
            history.append({
                "role": msg.role,
                "content": msg.content,
            })

        # Add note context from linked notes if no specific note_ids provided
        if not note_ids and session.linked_notes:
            note_ids = [n.id for n in session.linked_notes]

        # Send message using existing chat method
        result = await self.chat(
            message=message,
            providers=providers,
            user_id=user_id,
            note_ids=note_ids,
            conversation_history=history,
            max_tokens=max_tokens,
        )

        # Save user message
        self.add_message(
            session_id=session.id,
            role="user",
            content=message,
        )

        # Save assistant response(s)
        responses = result.get("responses", [])
        if responses:
            # Use first successful response as main content
            main_content = ""
            main_provider = None
            for resp in responses:
                if not resp.get("error"):
                    main_content = resp.get("content", "")
                    main_provider = resp.get("provider")
                    break

            if not main_content and responses:
                main_content = responses[0].get("content", "") or responses[0].get("error", "")
                main_provider = responses[0].get("provider")

            self.add_message(
                session_id=session.id,
                role="assistant",
                content=main_content,
                provider=main_provider,
                all_responses=responses,
            )

        # Auto-generate title from first message if not set
        if not session.title and message:
            session.title = message[:50] + ("..." if len(message) > 50 else "")
            self.db.commit()

        result["session_id"] = session.id
        return result
