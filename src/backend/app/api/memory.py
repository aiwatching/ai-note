"""
Memory API Endpoints

REST API for memory search, indexing, and management.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from ..core.deps import get_memory_index
from ..memory.index import MemoryIndex

router = APIRouter(prefix="/memory", tags=["memory"])


# ==================== Request/Response Models ====================

class SearchRequest(BaseModel):
    """Memory search request"""
    query: str = Field(..., description="Search query")
    max_results: int = Field(default=10, ge=1, le=50)
    min_score: float = Field(default=0.3, ge=0, le=1)
    source_filter: Optional[str] = Field(default=None)


class SearchResultItem(BaseModel):
    """Single search result"""
    source: str
    source_id: str
    snippet: str
    score: float
    vector_score: float
    text_score: float
    metadata: Dict[str, Any] = {}


class SearchResponse(BaseModel):
    """Search response"""
    query: str
    count: int
    results: List[SearchResultItem]


class AddMemoryRequest(BaseModel):
    """Add memory request"""
    text: str = Field(..., min_length=1)
    source: str = Field(default="note")
    source_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AddMemoryResponse(BaseModel):
    """Add memory response"""
    success: bool
    source: str
    source_id: str
    chunks_created: int


class IndexConversationRequest(BaseModel):
    """Index conversation request"""
    conversation_id: str
    messages: List[Dict[str, Any]]
    title: Optional[str] = None


class MemoryStatsResponse(BaseModel):
    """Memory statistics response"""
    chunks: int
    embeddings: int
    sources: Dict[str, int]
    embedding_provider: str
    embedding_model: str
    embedding_dimensions: int
    cache_stats: Dict[str, Any]


# ==================== API Endpoints ====================

@router.post("/search", response_model=SearchResponse)
async def search_memory(request: SearchRequest):
    """
    Search memory using hybrid search (semantic + keyword).

    Combines vector similarity search with FTS5 keyword matching
    for improved retrieval quality.
    """
    memory_index = await get_memory_index()
    if memory_index is None:
        raise HTTPException(status_code=503, detail="Memory index not available")

    try:
        results = await memory_index.search(
            query=request.query,
            max_results=request.max_results,
            min_score=request.min_score,
            source_filter=request.source_filter,
        )

        return SearchResponse(
            query=request.query,
            count=len(results),
            results=[
                SearchResultItem(
                    source=r.source,
                    source_id=r.source_id,
                    snippet=r.snippet,
                    score=round(r.score, 3),
                    vector_score=round(r.vector_score, 3),
                    text_score=round(r.text_score, 3),
                    metadata=r.metadata,
                )
                for r in results
            ],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_memory_get(
    q: str = Query(..., description="Search query"),
    max_results: int = Query(default=10, ge=1, le=50),
    min_score: float = Query(default=0.3, ge=0, le=1),
    source: Optional[str] = Query(default=None, description="Source filter"),
):
    """
    Search memory (GET version for simple queries).
    """
    request = SearchRequest(
        query=q,
        max_results=max_results,
        min_score=min_score,
        source_filter=source,
    )
    return await search_memory(request)


@router.post("/add", response_model=AddMemoryResponse)
async def add_memory(request: AddMemoryRequest):
    """
    Add content to memory index.

    Content will be chunked and embedded for future retrieval.
    """
    memory_index = await get_memory_index()
    if memory_index is None:
        raise HTTPException(status_code=503, detail="Memory index not available")

    try:
        import uuid
        source_id = request.source_id or str(uuid.uuid4())[:8]

        chunk_ids = await memory_index.add_memory(
            text=request.text,
            source=request.source,
            source_id=source_id,
            metadata=request.metadata,
        )

        return AddMemoryResponse(
            success=True,
            source=request.source,
            source_id=source_id,
            chunks_created=len(chunk_ids),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index/conversation")
async def index_conversation(request: IndexConversationRequest):
    """
    Index a conversation into memory.

    Extracts and indexes conversation content for future retrieval.
    """
    memory_index = await get_memory_index()
    if memory_index is None:
        raise HTTPException(status_code=503, detail="Memory index not available")

    try:
        await memory_index.index_conversation(
            conversation_id=request.conversation_id,
            messages=request.messages,
            title=request.title,
        )

        return {
            "success": True,
            "conversation_id": request.conversation_id,
            "message": "Conversation indexed successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{source}/{source_id}")
async def delete_memory(source: str, source_id: str):
    """
    Delete content from memory by source.
    """
    memory_index = await get_memory_index()
    if memory_index is None:
        raise HTTPException(status_code=503, detail="Memory index not available")

    try:
        await memory_index.remove_memory(source, source_id)
        return {
            "success": True,
            "source": source,
            "source_id": source_id,
            "message": "Memory deleted",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{source}/{source_id}")
async def get_memory(source: str, source_id: str):
    """
    Get full content from memory by source.
    """
    memory_index = await get_memory_index()
    if memory_index is None:
        raise HTTPException(status_code=503, detail="Memory index not available")

    try:
        import sqlite3
        import json

        with sqlite3.connect(memory_index.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT text, metadata, created_at
                FROM chunks
                WHERE source = ? AND source_id = ?
                ORDER BY start_pos
            """, (source, source_id)).fetchall()

        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"No content found for {source}:{source_id}"
            )

        full_text = "\n".join(row["text"] for row in rows)
        metadata = {}
        if rows[0]["metadata"]:
            metadata = json.loads(rows[0]["metadata"])

        return {
            "source": source,
            "source_id": source_id,
            "text": full_text,
            "chunks": len(rows),
            "metadata": metadata,
            "created_at": rows[0]["created_at"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=MemoryStatsResponse)
async def get_memory_stats():
    """
    Get memory index statistics.
    """
    memory_index = await get_memory_index()
    if memory_index is None:
        raise HTTPException(status_code=503, detail="Memory index not available")

    try:
        stats = memory_index.get_stats()
        return MemoryStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rebuild")
async def rebuild_index():
    """
    Rebuild FTS index (maintenance operation).
    """
    memory_index = await get_memory_index()
    if memory_index is None:
        raise HTTPException(status_code=503, detail="Memory index not available")

    try:
        await memory_index.rebuild_index()
        return {"success": True, "message": "Index rebuilt"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear")
async def clear_memory():
    """
    Clear all indexed memory (dangerous!).
    """
    memory_index = await get_memory_index()
    if memory_index is None:
        raise HTTPException(status_code=503, detail="Memory index not available")

    try:
        await memory_index.clear()
        return {"success": True, "message": "Memory cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources")
async def list_sources():
    """
    List all indexed sources.
    """
    memory_index = await get_memory_index()
    if memory_index is None:
        raise HTTPException(status_code=503, detail="Memory index not available")

    try:
        import sqlite3

        with sqlite3.connect(memory_index.db_path) as conn:
            rows = conn.execute("""
                SELECT source, source_id, COUNT(*) as chunks,
                       MIN(created_at) as created_at
                FROM chunks
                GROUP BY source, source_id
                ORDER BY created_at DESC
                LIMIT 100
            """).fetchall()

        return {
            "count": len(rows),
            "sources": [
                {
                    "source": row[0],
                    "source_id": row[1],
                    "chunks": row[2],
                    "created_at": row[3],
                }
                for row in rows
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
