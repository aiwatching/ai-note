"""
Memory Tools for Agents

Provides memory_search and memory_get tools for agents
to access the memory system.
"""
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from ..memory.index import MemoryIndex, SearchResult

logger = logging.getLogger(__name__)


@dataclass
class MemorySearchResult:
    """Memory search result for tool output"""
    source: str
    source_id: str
    snippet: str
    score: float
    metadata: Dict[str, Any]


async def memory_search(
    query: str,
    max_results: int = 5,
    min_score: float = 0.3,
    source_filter: Optional[str] = None,
    memory_index: Optional[MemoryIndex] = None,
) -> Dict[str, Any]:
    """
    Search memory for relevant information.

    This tool searches through indexed conversations and documents
    using hybrid search (semantic + keyword matching).

    Args:
        query: The search query describing what you're looking for
        max_results: Maximum number of results to return (default: 5)
        min_score: Minimum relevance score threshold (0-1, default: 0.3)
        source_filter: Filter by source type (conversation, note, document)
        memory_index: Memory index instance (injected)

    Returns:
        Dict with search results and metadata
    """
    if memory_index is None:
        return {
            "success": False,
            "error": "Memory index not available",
            "results": [],
        }

    try:
        results = await memory_index.search(
            query=query,
            max_results=max_results,
            min_score=min_score,
            source_filter=source_filter,
        )

        return {
            "success": True,
            "query": query,
            "count": len(results),
            "results": [
                {
                    "source": r.source,
                    "source_id": r.source_id,
                    "snippet": r.snippet,
                    "score": round(r.score, 3),
                    "vector_score": round(r.vector_score, 3),
                    "text_score": round(r.text_score, 3),
                    "metadata": r.metadata,
                }
                for r in results
            ],
        }
    except Exception as e:
        logger.error(f"Memory search error: {e}")
        return {
            "success": False,
            "error": str(e),
            "results": [],
        }


async def memory_add(
    text: str,
    source: str = "note",
    source_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    memory_index: Optional[MemoryIndex] = None,
) -> Dict[str, Any]:
    """
    Add content to memory.

    This tool adds new content to the memory index for future retrieval.

    Args:
        text: The text content to add to memory
        source: Source type (note, document, fact)
        source_id: Optional source identifier
        metadata: Optional metadata to store with the content
        memory_index: Memory index instance (injected)

    Returns:
        Dict with operation result
    """
    if memory_index is None:
        return {
            "success": False,
            "error": "Memory index not available",
        }

    if not text.strip():
        return {
            "success": False,
            "error": "Text content is required",
        }

    try:
        import uuid
        if not source_id:
            source_id = str(uuid.uuid4())[:8]

        chunk_ids = await memory_index.add_memory(
            text=text,
            source=source,
            source_id=source_id,
            metadata=metadata,
        )

        return {
            "success": True,
            "source": source,
            "source_id": source_id,
            "chunks_created": len(chunk_ids),
        }
    except Exception as e:
        logger.error(f"Memory add error: {e}")
        return {
            "success": False,
            "error": str(e),
        }


async def memory_get(
    source: str,
    source_id: str,
    memory_index: Optional[MemoryIndex] = None,
) -> Dict[str, Any]:
    """
    Get full content from memory by source.

    This tool retrieves the complete content for a specific source.

    Args:
        source: Source type (conversation, note, document)
        source_id: Source identifier
        memory_index: Memory index instance (injected)

    Returns:
        Dict with full content and metadata
    """
    if memory_index is None:
        return {
            "success": False,
            "error": "Memory index not available",
        }

    try:
        import sqlite3

        with sqlite3.connect(memory_index.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT text, metadata, created_at
                FROM chunks
                WHERE source = ? AND source_id = ?
                ORDER BY start_pos
            """, (source, source_id)).fetchall()

        if not rows:
            return {
                "success": False,
                "error": f"No content found for {source}:{source_id}",
            }

        # Combine chunks
        full_text = "\n".join(row["text"] for row in rows)
        metadata = {}
        if rows[0]["metadata"]:
            import json
            metadata = json.loads(rows[0]["metadata"])

        return {
            "success": True,
            "source": source,
            "source_id": source_id,
            "text": full_text,
            "chunks": len(rows),
            "metadata": metadata,
            "created_at": rows[0]["created_at"],
        }
    except Exception as e:
        logger.error(f"Memory get error: {e}")
        return {
            "success": False,
            "error": str(e),
        }


async def memory_delete(
    source: str,
    source_id: str,
    memory_index: Optional[MemoryIndex] = None,
) -> Dict[str, Any]:
    """
    Delete content from memory.

    This tool removes content from the memory index.

    Args:
        source: Source type (conversation, note, document)
        source_id: Source identifier
        memory_index: Memory index instance (injected)

    Returns:
        Dict with operation result
    """
    if memory_index is None:
        return {
            "success": False,
            "error": "Memory index not available",
        }

    try:
        await memory_index.remove_memory(source, source_id)
        return {
            "success": True,
            "source": source,
            "source_id": source_id,
            "message": "Content deleted from memory",
        }
    except Exception as e:
        logger.error(f"Memory delete error: {e}")
        return {
            "success": False,
            "error": str(e),
        }


async def memory_stats(
    memory_index: Optional[MemoryIndex] = None,
) -> Dict[str, Any]:
    """
    Get memory system statistics.

    This tool returns statistics about the memory index.

    Args:
        memory_index: Memory index instance (injected)

    Returns:
        Dict with memory statistics
    """
    if memory_index is None:
        return {
            "success": False,
            "error": "Memory index not available",
        }

    try:
        stats = memory_index.get_stats()
        return {
            "success": True,
            **stats,
        }
    except Exception as e:
        logger.error(f"Memory stats error: {e}")
        return {
            "success": False,
            "error": str(e),
        }


# Tool definitions for registration
MEMORY_TOOLS = [
    {
        "name": "memory_search",
        "description": "Search through memory (conversations, notes, documents) using semantic and keyword search. Use this to find relevant past information.",
        "function": memory_search,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query describing what you're looking for",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 5)",
                    "default": 5,
                },
                "min_score": {
                    "type": "number",
                    "description": "Minimum relevance score 0-1 (default: 0.3)",
                    "default": 0.3,
                },
                "source_filter": {
                    "type": "string",
                    "description": "Filter by source type (conversation, note, document)",
                    "enum": ["conversation", "note", "document"],
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "memory_add",
        "description": "Add new content to memory for future retrieval. Use this to remember important facts or information.",
        "function": memory_add,
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text content to remember",
                },
                "source": {
                    "type": "string",
                    "description": "Source type (note, document, fact)",
                    "default": "note",
                },
                "source_id": {
                    "type": "string",
                    "description": "Optional identifier for the content",
                },
                "metadata": {
                    "type": "object",
                    "description": "Optional metadata to store",
                },
            },
            "required": ["text"],
        },
    },
    {
        "name": "memory_get",
        "description": "Get full content from memory by source type and ID.",
        "function": memory_get,
        "parameters": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Source type (conversation, note, document)",
                },
                "source_id": {
                    "type": "string",
                    "description": "Source identifier",
                },
            },
            "required": ["source", "source_id"],
        },
    },
    {
        "name": "memory_stats",
        "description": "Get memory system statistics including total chunks, sources, and embedding info.",
        "function": memory_stats,
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
]
