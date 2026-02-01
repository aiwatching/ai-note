"""
Memory Index with Hybrid Search

Inspired by OpenClaw's memory system:
- SQLite FTS5 for keyword search
- Vector similarity search
- Hybrid search combining both
- Embedding cache
"""
import hashlib
import json
import logging
import sqlite3
import struct
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import asyncio

from .embeddings import EmbeddingService, EmbeddingConfig, cosine_similarity

logger = logging.getLogger(__name__)


@dataclass
class MemoryChunk:
    """A chunk of memory content"""
    id: str
    source: str  # "conversation", "note", "document"
    source_id: str  # Original source ID
    text: str
    start_pos: int = 0
    end_pos: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SearchResult:
    """Search result with score"""
    chunk_id: str
    source: str
    source_id: str
    text: str
    score: float
    snippet: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    vector_score: float = 0.0
    text_score: float = 0.0


@dataclass
class MemoryIndexConfig:
    """Memory index configuration"""
    db_path: str = "./data/memory_index.db"
    embedding_config: EmbeddingConfig = field(default_factory=EmbeddingConfig)

    # Chunking
    chunk_size: int = 500  # Characters per chunk
    chunk_overlap: int = 50  # Overlap between chunks

    # Search
    max_results: int = 10
    min_score: float = 0.3
    hybrid_enabled: bool = True
    vector_weight: float = 0.7
    text_weight: float = 0.3
    candidate_multiplier: int = 3


class MemoryIndex:
    """
    Memory Index with Hybrid Search.

    Combines FTS5 keyword search with vector similarity search
    for improved retrieval quality.

    Usage:
        index = MemoryIndex(config)
        await index.initialize()
        await index.add_memory(chunk)
        results = await index.search("query")
    """

    def __init__(self, config: MemoryIndexConfig):
        self.config = config
        self.db_path = config.db_path
        self.embedding_service = EmbeddingService(config.embedding_config)
        self._initialized = False

        # Ensure data directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> bool:
        """Initialize the memory index"""
        if self._initialized:
            return True

        # Initialize database
        self._init_db()

        # Initialize embedding service
        await self.embedding_service.initialize()

        self._initialized = True
        logger.info(f"Memory index initialized: {self.db_path}")
        return True

    def _init_db(self):
        """Initialize SQLite database with FTS5"""
        with sqlite3.connect(self.db_path) as conn:
            # Chunks table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    text_hash TEXT NOT NULL,
                    start_pos INTEGER DEFAULT 0,
                    end_pos INTEGER DEFAULT 0,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Vector embeddings table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    chunk_id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    dimensions INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
                )
            """)

            # Embedding cache table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embedding_cache (
                    hash TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            # FTS5 full-text search table
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    text,
                    chunk_id UNINDEXED,
                    source UNINDEXED,
                    source_id UNINDEXED,
                    content='chunks',
                    content_rowid='rowid'
                )
            """)

            # Triggers to keep FTS in sync
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
                    INSERT INTO chunks_fts(rowid, text, chunk_id, source, source_id)
                    VALUES (NEW.rowid, NEW.text, NEW.id, NEW.source, NEW.source_id);
                END
            """)

            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
                    INSERT INTO chunks_fts(chunks_fts, rowid, text, chunk_id, source, source_id)
                    VALUES ('delete', OLD.rowid, OLD.text, OLD.id, OLD.source, OLD.source_id);
                END
            """)

            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
                    INSERT INTO chunks_fts(chunks_fts, rowid, text, chunk_id, source, source_id)
                    VALUES ('delete', OLD.rowid, OLD.text, OLD.id, OLD.source, OLD.source_id);
                    INSERT INTO chunks_fts(rowid, text, chunk_id, source, source_id)
                    VALUES (NEW.rowid, NEW.text, NEW.id, NEW.source, NEW.source_id);
                END
            """)

            # Indexes
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source, source_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_chunks_hash ON chunks(text_hash)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_embeddings_model ON embeddings(provider, model)"
            )

            conn.commit()

    def _hash_text(self, text: str) -> str:
        """Generate hash for text"""
        return hashlib.sha256(text.encode()).hexdigest()

    def _vector_to_blob(self, vector: List[float]) -> bytes:
        """Convert vector to SQLite blob"""
        return struct.pack(f'{len(vector)}f', *vector)

    def _blob_to_vector(self, blob: bytes) -> List[float]:
        """Convert SQLite blob to vector"""
        count = len(blob) // 4  # 4 bytes per float
        return list(struct.unpack(f'{count}f', blob))

    def _chunk_text(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Split text into chunks with overlap.

        Returns list of (chunk_text, start_pos, end_pos)
        """
        chunks = []
        text_len = len(text)

        if text_len <= self.config.chunk_size:
            return [(text, 0, text_len)]

        start = 0
        while start < text_len:
            end = min(start + self.config.chunk_size, text_len)

            # Try to break at sentence boundary
            if end < text_len:
                # Look for sentence endings
                for delim in ['. ', '。', '\n\n', '\n', ' ']:
                    last_delim = text.rfind(delim, start, end)
                    if last_delim > start + self.config.chunk_size // 2:
                        end = last_delim + len(delim)
                        break

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append((chunk_text, start, end))

            # Move start with overlap
            start = end - self.config.chunk_overlap
            if start >= text_len - self.config.chunk_overlap:
                break

        return chunks

    async def add_memory(
        self,
        text: str,
        source: str,
        source_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        chunk: bool = True,
    ) -> List[str]:
        """
        Add memory to index.

        Args:
            text: Text content
            source: Source type (conversation, note, document)
            source_id: Source identifier
            metadata: Optional metadata
            chunk: Whether to chunk the text

        Returns:
            List of chunk IDs
        """
        if not self._initialized:
            await self.initialize()

        now = datetime.now().isoformat()
        chunk_ids = []
        metadata = metadata or {}

        # Chunk text if needed
        if chunk:
            text_chunks = self._chunk_text(text)
        else:
            text_chunks = [(text, 0, len(text))]

        # Generate embeddings for all chunks
        chunk_texts = [c[0] for c in text_chunks]
        embeddings = await self.embedding_service.embed_batch(chunk_texts)

        with sqlite3.connect(self.db_path) as conn:
            for i, (chunk_text, start_pos, end_pos) in enumerate(text_chunks):
                text_hash = self._hash_text(chunk_text)
                chunk_id = f"{source}:{source_id}:{text_hash[:16]}"

                # Check if chunk already exists
                existing = conn.execute(
                    "SELECT id FROM chunks WHERE id = ?",
                    (chunk_id,)
                ).fetchone()

                if existing:
                    # Update existing chunk
                    conn.execute("""
                        UPDATE chunks SET
                            text = ?, text_hash = ?, start_pos = ?, end_pos = ?,
                            metadata = ?, updated_at = ?
                        WHERE id = ?
                    """, (
                        chunk_text, text_hash, start_pos, end_pos,
                        json.dumps(metadata), now, chunk_id
                    ))
                else:
                    # Insert new chunk
                    conn.execute("""
                        INSERT INTO chunks (id, source, source_id, text, text_hash,
                                          start_pos, end_pos, metadata, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        chunk_id, source, source_id, chunk_text, text_hash,
                        start_pos, end_pos, json.dumps(metadata), now, now
                    ))

                # Store embedding
                embedding = embeddings[i]
                embedding_blob = self._vector_to_blob(embedding.vector)

                conn.execute("""
                    INSERT OR REPLACE INTO embeddings
                        (chunk_id, provider, model, embedding, dimensions, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    chunk_id, self.embedding_service.provider_id,
                    self.embedding_service.model_name,
                    embedding_blob, embedding.dimensions, now
                ))

                chunk_ids.append(chunk_id)

            conn.commit()

        logger.debug(f"Added {len(chunk_ids)} chunks for {source}:{source_id}")
        return chunk_ids

    async def remove_memory(self, source: str, source_id: str):
        """Remove all chunks for a source"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM embeddings WHERE chunk_id IN "
                "(SELECT id FROM chunks WHERE source = ? AND source_id = ?)",
                (source, source_id)
            )
            conn.execute(
                "DELETE FROM chunks WHERE source = ? AND source_id = ?",
                (source, source_id)
            )
            conn.commit()

        logger.debug(f"Removed memory for {source}:{source_id}")

    async def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        min_score: Optional[float] = None,
        source_filter: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        Search memory with hybrid search.

        Args:
            query: Search query
            max_results: Max results to return
            min_score: Minimum score threshold
            source_filter: Filter by source type

        Returns:
            List of SearchResult sorted by score
        """
        if not self._initialized:
            await self.initialize()

        query = query.strip()
        if not query:
            return []

        max_results = max_results or self.config.max_results
        min_score = min_score or self.config.min_score
        candidates = max_results * self.config.candidate_multiplier

        # Perform both searches
        if self.config.hybrid_enabled:
            keyword_results = await self._search_keyword(query, candidates, source_filter)
            vector_results = await self._search_vector(query, candidates, source_filter)
            results = self._merge_hybrid_results(keyword_results, vector_results)
        else:
            results = await self._search_vector(query, candidates, source_filter)

        # Filter by min score and limit
        results = [r for r in results if r.score >= min_score]
        results = results[:max_results]

        return results

    async def _search_keyword(
        self,
        query: str,
        limit: int,
        source_filter: Optional[str] = None,
    ) -> List[SearchResult]:
        """FTS5 keyword search"""
        # Build FTS query
        tokens = [t.strip() for t in query.split() if t.strip()]
        if not tokens:
            return []

        fts_query = " AND ".join(f'"{t}"' for t in tokens)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            sql = """
                SELECT
                    c.id, c.source, c.source_id, c.text, c.metadata,
                    bm25(chunks_fts) as rank
                FROM chunks_fts f
                JOIN chunks c ON c.id = f.chunk_id
                WHERE chunks_fts MATCH ?
            """
            params = [fts_query]

            if source_filter:
                sql += " AND c.source = ?"
                params.append(source_filter)

            sql += " ORDER BY rank LIMIT ?"
            params.append(limit)

            try:
                rows = conn.execute(sql, params).fetchall()
            except sqlite3.OperationalError:
                # FTS query syntax error
                return []

        results = []
        for row in rows:
            # BM25 rank is negative, lower is better
            # Convert to 0-1 score
            text_score = 1 / (1 + abs(row["rank"]))

            results.append(SearchResult(
                chunk_id=row["id"],
                source=row["source"],
                source_id=row["source_id"],
                text=row["text"],
                score=text_score,
                snippet=row["text"][:200] + "..." if len(row["text"]) > 200 else row["text"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                text_score=text_score,
            ))

        return results

    async def _search_vector(
        self,
        query: str,
        limit: int,
        source_filter: Optional[str] = None,
    ) -> List[SearchResult]:
        """Vector similarity search"""
        # Get query embedding
        query_embedding = await self.embedding_service.embed(query)
        query_vector = query_embedding.vector

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            sql = """
                SELECT
                    c.id, c.source, c.source_id, c.text, c.metadata,
                    e.embedding
                FROM chunks c
                JOIN embeddings e ON e.chunk_id = c.id
                WHERE e.model = ?
            """
            params = [self.embedding_service.model_name]

            if source_filter:
                sql += " AND c.source = ?"
                params.append(source_filter)

            rows = conn.execute(sql, params).fetchall()

        # Calculate similarities
        results = []
        for row in rows:
            embedding = self._blob_to_vector(row["embedding"])
            similarity = cosine_similarity(query_vector, embedding)

            # Skip low similarity results early
            if similarity < self.config.min_score / 2:
                continue

            results.append(SearchResult(
                chunk_id=row["id"],
                source=row["source"],
                source_id=row["source_id"],
                text=row["text"],
                score=similarity,
                snippet=row["text"][:200] + "..." if len(row["text"]) > 200 else row["text"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                vector_score=similarity,
            ))

        # Sort by similarity and limit
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    def _merge_hybrid_results(
        self,
        keyword_results: List[SearchResult],
        vector_results: List[SearchResult],
    ) -> List[SearchResult]:
        """
        Merge keyword and vector results with weighted scoring.

        Uses the formula: score = vector_weight * vector_score + text_weight * text_score
        """
        merged: Dict[str, SearchResult] = {}

        # Add vector results
        for r in vector_results:
            merged[r.chunk_id] = SearchResult(
                chunk_id=r.chunk_id,
                source=r.source,
                source_id=r.source_id,
                text=r.text,
                score=0,
                snippet=r.snippet,
                metadata=r.metadata,
                vector_score=r.vector_score,
                text_score=0,
            )

        # Merge keyword results
        for r in keyword_results:
            if r.chunk_id in merged:
                merged[r.chunk_id].text_score = r.text_score
                # Prefer keyword snippet as it may have highlights
                if r.snippet:
                    merged[r.chunk_id].snippet = r.snippet
            else:
                merged[r.chunk_id] = SearchResult(
                    chunk_id=r.chunk_id,
                    source=r.source,
                    source_id=r.source_id,
                    text=r.text,
                    score=0,
                    snippet=r.snippet,
                    metadata=r.metadata,
                    vector_score=0,
                    text_score=r.text_score,
                )

        # Calculate final scores
        results = list(merged.values())
        for r in results:
            r.score = (
                self.config.vector_weight * r.vector_score +
                self.config.text_weight * r.text_score
            )

        # Sort by final score
        results.sort(key=lambda x: x.score, reverse=True)
        return results

    async def index_conversation(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]],
        title: Optional[str] = None,
    ):
        """
        Index a conversation into memory.

        Args:
            conversation_id: Conversation ID
            messages: List of message dicts with 'role' and 'content'
            title: Optional conversation title
        """
        # Combine messages into text
        text_parts = []
        if title:
            text_parts.append(f"# {title}\n")

        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if content:
                text_parts.append(f"[{role}]: {content}")

        full_text = "\n\n".join(text_parts)

        # Index with metadata
        await self.add_memory(
            text=full_text,
            source="conversation",
            source_id=conversation_id,
            metadata={"title": title, "message_count": len(messages)},
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        with sqlite3.connect(self.db_path) as conn:
            chunks_count = conn.execute(
                "SELECT COUNT(*) FROM chunks"
            ).fetchone()[0]

            embeddings_count = conn.execute(
                "SELECT COUNT(*) FROM embeddings"
            ).fetchone()[0]

            sources = conn.execute(
                "SELECT source, COUNT(*) as count FROM chunks GROUP BY source"
            ).fetchall()

        return {
            "chunks": chunks_count,
            "embeddings": embeddings_count,
            "sources": {s[0]: s[1] for s in sources},
            "embedding_provider": self.embedding_service.provider_id,
            "embedding_model": self.embedding_service.model_name,
            "embedding_dimensions": self.embedding_service.dimensions,
            "cache_stats": self.embedding_service.cache_stats(),
        }

    async def rebuild_index(self):
        """Rebuild FTS index (for maintenance)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
            conn.commit()
        logger.info("FTS index rebuilt")

    async def clear(self):
        """Clear all indexed data"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM embeddings")
            conn.execute("DELETE FROM chunks")
            conn.execute("DELETE FROM embedding_cache")
            conn.commit()
        logger.info("Memory index cleared")
