"""
Embedding Service

Supports multiple embedding providers:
- OpenAI (text-embedding-3-small)
- Local (sentence-transformers)
- Fallback mechanism
"""
import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Embedding result with metadata"""
    vector: List[float]
    model: str
    dimensions: int
    cached: bool = False


@dataclass
class EmbeddingConfig:
    """Embedding configuration"""
    provider: str = "auto"  # openai, local, auto
    model: str = "text-embedding-3-small"
    fallback: str = "local"
    cache_enabled: bool = True
    cache_max_entries: int = 10000
    local_model: str = "all-MiniLM-L6-v2"
    openai_api_key: Optional[str] = None


class EmbeddingProvider(ABC):
    """Base embedding provider"""

    @property
    @abstractmethod
    def id(self) -> str:
        pass

    @property
    @abstractmethod
    def model(self) -> str:
        pass

    @property
    @abstractmethod
    def dimensions(self) -> int:
        pass

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Embed single text"""
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed batch of texts"""
        pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider"""

    MODELS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self._model = model
        self._dimensions = self.MODELS.get(model, 1536)
        self._api_key = api_key
        self._client = None

    @property
    def id(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self._api_key)
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")
        return self._client

    async def embed_text(self, text: str) -> List[float]:
        client = self._get_client()
        response = await client.embeddings.create(
            model=self._model,
            input=text,
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        client = self._get_client()
        response = await client.embeddings.create(
            model=self._model,
            input=texts,
        )
        # Sort by index to maintain order
        sorted_data = sorted(response.data, key=lambda x: x.index)
        return [item.embedding for item in sorted_data]


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local embedding using sentence-transformers"""

    MODELS = {
        "all-MiniLM-L6-v2": 384,
        "all-mpnet-base-v2": 768,
        "paraphrase-multilingual-MiniLM-L12-v2": 384,
        "distiluse-base-multilingual-cased-v2": 512,
    }

    def __init__(self, model: str = "all-MiniLM-L6-v2"):
        self._model = model
        self._dimensions = self.MODELS.get(model, 384)
        self._encoder = None

    @property
    def id(self) -> str:
        return "local"

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def _get_encoder(self):
        if self._encoder is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._encoder = SentenceTransformer(self._model)
                logger.info(f"Loaded local embedding model: {self._model}")
            except ImportError:
                raise ImportError(
                    "sentence-transformers not installed. Run: pip install sentence-transformers"
                )
        return self._encoder

    async def embed_text(self, text: str) -> List[float]:
        encoder = self._get_encoder()
        embedding = encoder.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        encoder = self._get_encoder()
        embeddings = encoder.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()


class EmbeddingService:
    """
    Unified embedding service with caching and fallback.

    Usage:
        service = EmbeddingService(config)
        await service.initialize()
        vector = await service.embed("Hello world")
        vectors = await service.embed_batch(["Hello", "World"])
    """

    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.provider: Optional[EmbeddingProvider] = None
        self.fallback_provider: Optional[EmbeddingProvider] = None
        self._cache: Dict[str, List[float]] = {}
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize embedding providers"""
        if self._initialized:
            return True

        provider = self.config.provider

        # Auto-select provider
        if provider == "auto":
            # Try OpenAI first if API key available
            if self.config.openai_api_key:
                try:
                    self.provider = OpenAIEmbeddingProvider(
                        api_key=self.config.openai_api_key,
                        model=self.config.model,
                    )
                    # Test connection
                    await self.provider.embed_text("test")
                    logger.info("Using OpenAI embedding provider")
                    self._initialized = True
                    return True
                except Exception as e:
                    logger.warning(f"OpenAI embedding failed: {e}, trying local")

            # Fallback to local
            try:
                self.provider = LocalEmbeddingProvider(
                    model=self.config.local_model
                )
                await self.provider.embed_text("test")
                logger.info("Using local embedding provider")
                self._initialized = True
                return True
            except Exception as e:
                logger.error(f"Local embedding failed: {e}")
                raise RuntimeError("No embedding provider available")

        elif provider == "openai":
            if not self.config.openai_api_key:
                raise ValueError("OpenAI API key required for OpenAI provider")
            self.provider = OpenAIEmbeddingProvider(
                api_key=self.config.openai_api_key,
                model=self.config.model,
            )

        elif provider == "local":
            self.provider = LocalEmbeddingProvider(
                model=self.config.local_model
            )

        else:
            raise ValueError(f"Unknown provider: {provider}")

        # Setup fallback
        if self.config.fallback and self.config.fallback != provider:
            try:
                if self.config.fallback == "local":
                    self.fallback_provider = LocalEmbeddingProvider(
                        model=self.config.local_model
                    )
                elif self.config.fallback == "openai" and self.config.openai_api_key:
                    self.fallback_provider = OpenAIEmbeddingProvider(
                        api_key=self.config.openai_api_key,
                        model=self.config.model,
                    )
            except Exception as e:
                logger.warning(f"Failed to setup fallback provider: {e}")

        self._initialized = True
        return True

    def _cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        return hashlib.sha256(
            f"{self.provider.id}:{self.provider.model}:{text}".encode()
        ).hexdigest()

    def _get_cached(self, text: str) -> Optional[List[float]]:
        """Get cached embedding"""
        if not self.config.cache_enabled:
            return None
        key = self._cache_key(text)
        return self._cache.get(key)

    def _set_cached(self, text: str, embedding: List[float]):
        """Cache embedding"""
        if not self.config.cache_enabled:
            return

        # LRU eviction if cache full
        if len(self._cache) >= self.config.cache_max_entries:
            # Remove oldest 10% entries
            to_remove = len(self._cache) // 10
            keys = list(self._cache.keys())[:to_remove]
            for key in keys:
                del self._cache[key]

        key = self._cache_key(text)
        self._cache[key] = embedding

    async def embed(self, text: str) -> EmbeddingResult:
        """
        Embed single text with caching.

        Args:
            text: Text to embed

        Returns:
            EmbeddingResult with vector and metadata
        """
        if not self._initialized:
            await self.initialize()

        # Check cache
        cached = self._get_cached(text)
        if cached is not None:
            return EmbeddingResult(
                vector=cached,
                model=self.provider.model,
                dimensions=self.provider.dimensions,
                cached=True,
            )

        # Get embedding
        try:
            vector = await self.provider.embed_text(text)
        except Exception as e:
            if self.fallback_provider:
                logger.warning(f"Primary provider failed: {e}, using fallback")
                vector = await self.fallback_provider.embed_text(text)
            else:
                raise

        # Cache result
        self._set_cached(text, vector)

        return EmbeddingResult(
            vector=vector,
            model=self.provider.model,
            dimensions=self.provider.dimensions,
            cached=False,
        )

    async def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 100,
    ) -> List[EmbeddingResult]:
        """
        Embed batch of texts with caching.

        Args:
            texts: List of texts to embed
            batch_size: Max batch size for API calls

        Returns:
            List of EmbeddingResult
        """
        if not self._initialized:
            await self.initialize()

        results = []
        uncached_texts = []
        uncached_indices = []

        # Check cache for each text
        for i, text in enumerate(texts):
            cached = self._get_cached(text)
            if cached is not None:
                results.append((i, EmbeddingResult(
                    vector=cached,
                    model=self.provider.model,
                    dimensions=self.provider.dimensions,
                    cached=True,
                )))
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)

        # Batch embed uncached texts
        if uncached_texts:
            for batch_start in range(0, len(uncached_texts), batch_size):
                batch_end = min(batch_start + batch_size, len(uncached_texts))
                batch_texts = uncached_texts[batch_start:batch_end]
                batch_indices = uncached_indices[batch_start:batch_end]

                try:
                    vectors = await self.provider.embed_batch(batch_texts)
                except Exception as e:
                    if self.fallback_provider:
                        logger.warning(f"Primary batch failed: {e}, using fallback")
                        vectors = await self.fallback_provider.embed_batch(batch_texts)
                    else:
                        raise

                for text, idx, vector in zip(batch_texts, batch_indices, vectors):
                    self._set_cached(text, vector)
                    results.append((idx, EmbeddingResult(
                        vector=vector,
                        model=self.provider.model,
                        dimensions=self.provider.dimensions,
                        cached=False,
                    )))

        # Sort by original index and return
        results.sort(key=lambda x: x[0])
        return [r[1] for r in results]

    @property
    def dimensions(self) -> int:
        """Get embedding dimensions"""
        if self.provider:
            return self.provider.dimensions
        return 0

    @property
    def provider_id(self) -> str:
        """Get current provider ID"""
        if self.provider:
            return self.provider.id
        return "none"

    @property
    def model_name(self) -> str:
        """Get current model name"""
        if self.provider:
            return self.provider.model
        return "none"

    def clear_cache(self):
        """Clear embedding cache"""
        self._cache.clear()

    def cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "enabled": self.config.cache_enabled,
            "entries": len(self._cache),
            "max_entries": self.config.cache_max_entries,
        }


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    a = np.array(vec1)
    b = np.array(vec2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def normalize_vector(vec: List[float]) -> List[float]:
    """Normalize vector to unit length"""
    arr = np.array(vec)
    norm = np.linalg.norm(arr)
    if norm == 0:
        return vec
    return (arr / norm).tolist()
