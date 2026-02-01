"""
Memory Sync Module

Syncs conversations and other content to the memory index.
Inspired by OpenClaw's memory flush mechanism.
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from .store import SQLiteMemory
from .index import MemoryIndex

logger = logging.getLogger(__name__)


class MemorySync:
    """
    Syncs content between conversation memory and the memory index.

    Features:
    - Auto-index new conversations
    - Incremental sync (only changed content)
    - Memory flush before context compaction
    """

    def __init__(
        self,
        memory: SQLiteMemory,
        memory_index: MemoryIndex,
    ):
        self.memory = memory
        self.memory_index = memory_index
        self._synced_conversations: Dict[str, str] = {}  # id -> last_updated

    async def sync_conversation(
        self,
        conversation_id: str,
        force: bool = False,
    ) -> bool:
        """
        Sync a single conversation to the memory index.

        Args:
            conversation_id: Conversation ID to sync
            force: Force re-index even if unchanged

        Returns:
            True if synced, False if skipped
        """
        conversation = self.memory.get_conversation(conversation_id)
        if not conversation:
            logger.warning(f"Conversation not found: {conversation_id}")
            return False

        # Check if already synced and unchanged
        last_synced = self._synced_conversations.get(conversation_id)
        updated_at = conversation.updated_at.isoformat()

        if not force and last_synced == updated_at:
            logger.debug(f"Conversation unchanged, skipping: {conversation_id}")
            return False

        # Convert messages to dict format
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in conversation.messages
            if msg.content
        ]

        # Index the conversation
        await self.memory_index.index_conversation(
            conversation_id=conversation_id,
            messages=messages,
            title=conversation.title,
        )

        # Mark as synced
        self._synced_conversations[conversation_id] = updated_at
        logger.info(f"Synced conversation: {conversation_id}")
        return True

    async def sync_all_conversations(
        self,
        limit: int = 100,
        force: bool = False,
    ) -> int:
        """
        Sync all recent conversations to the memory index.

        Args:
            limit: Max number of conversations to sync
            force: Force re-index all

        Returns:
            Number of conversations synced
        """
        conversations = self.memory.list_conversations(limit=limit)
        synced_count = 0

        for conv in conversations:
            try:
                if await self.sync_conversation(conv.id, force=force):
                    synced_count += 1
            except Exception as e:
                logger.error(f"Failed to sync conversation {conv.id}: {e}")

        logger.info(f"Synced {synced_count}/{len(conversations)} conversations")
        return synced_count

    async def memory_flush(
        self,
        conversation_id: str,
        important_content: Optional[str] = None,
    ) -> bool:
        """
        Flush important content to memory before context compaction.

        This is similar to OpenClaw's pre-compaction memory flush.
        Call this before truncating conversation history.

        Args:
            conversation_id: Current conversation ID
            important_content: Optional explicit content to save

        Returns:
            True if flushed successfully
        """
        try:
            # Always sync current conversation
            await self.sync_conversation(conversation_id, force=True)

            # If explicit content provided, save as a separate memory
            if important_content:
                import uuid
                source_id = f"flush-{uuid.uuid4().hex[:8]}"
                await self.memory_index.add_memory(
                    text=important_content,
                    source="flush",
                    source_id=source_id,
                    metadata={
                        "conversation_id": conversation_id,
                        "flushed_at": datetime.now().isoformat(),
                    },
                )
                logger.info(f"Memory flush saved: {source_id}")

            return True
        except Exception as e:
            logger.error(f"Memory flush failed: {e}")
            return False


async def auto_index_conversation(
    memory: SQLiteMemory,
    memory_index: Optional[MemoryIndex],
    conversation_id: str,
):
    """
    Helper to auto-index a conversation after it's saved.

    Call this after saving a conversation to keep the index up to date.
    """
    if memory_index is None:
        return

    try:
        sync = MemorySync(memory, memory_index)
        await sync.sync_conversation(conversation_id)
    except Exception as e:
        logger.warning(f"Auto-index failed (non-fatal): {e}")
