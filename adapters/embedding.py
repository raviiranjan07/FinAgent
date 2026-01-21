"""EmbeddingAdapter - Generates vector embeddings for events using adapter pattern."""

from typing import List, Optional

from adapters.base import BaseAdapter
from adapters.context import ExecutionContext
from utils.embeddings import EmbeddingService


class EmbeddingAdapter(BaseAdapter):
    """
    Generates vector embeddings for semantic operations.

    Uses the existing EmbeddingService (sentence-transformers).
    Runs early in pipeline to provide embeddings for:
    - Deduplication (semantic similarity)
    - Database storage (pgvector)
    - Future: topic clustering, related content
    """

    name = "embedding_adapter"
    version = "1.1.0"
    input_keys = ["event.title", "event.summary"]
    output_keys = ["event_embedding"]

    def __init__(self):
        """Initialize with lazy-loaded embedding service."""
        self._service: Optional[EmbeddingService] = None

    def _get_service(self) -> EmbeddingService:
        """Lazy load embedding service."""
        if self._service is None:
            self._service = EmbeddingService()
        return self._service

    def run(self, context: ExecutionContext) -> ExecutionContext:
        """
        Generate embedding for event.

        Combines title + summary for richer semantic representation.
        Stores embedding in context for downstream adapters.
        """
        service = self._get_service()

        # Combine title and summary for embedding
        text = f"{context.event.title} {context.event.summary or ''}"

        # Generate embedding
        embedding = service.encode(text)
        context.event_embedding = embedding

        return context
