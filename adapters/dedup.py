"""DeduplicationAdapter - Detects duplicate events using URL and semantic similarity."""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from adapters.base import BaseAdapter
from adapters.context import ExecutionContext, DedupResult
from config.settings import (
    EVENTS_LOG_FILE,
    SIMILARITY_THRESHOLD,
    DEDUP_LOOKBACK_HOURS
)
from utils.embeddings import EmbeddingService
from utils.timezone import get_ist_now


class DeduplicationAdapter(BaseAdapter):
    """
    Detects duplicate events using two-layer approach:
    1. URL-based: Exact match (fast)
    2. Semantic: Embedding similarity (cross-source)

    Expects EmbeddingAdapter to run BEFORE this adapter to set context.event_embedding.
    Falls back to generating embedding if not provided.
    """

    name = "dedup_adapter"
    version = "1.2.0"  # Fixed: Load from database when DATABASE_ENABLED=true
    input_keys = ["event.url", "event.title", "event_embedding"]
    output_keys = ["dedup"]

    def __init__(self):
        """Initialize with cached data from logs."""
        self._processed_urls: Set[str] = set()
        self._recent_events: List[Dict] = []
        self._embedding_service: Optional[EmbeddingService] = None
        self._loaded = False

    def _load_processed_data(self):
        """Load URLs and recent events from database (if enabled) or log file."""
        if self._loaded:
            return

        self._processed_urls = set()
        self._recent_events = []

        cutoff_time = get_ist_now() - timedelta(hours=DEDUP_LOOKBACK_HOURS)

        # Try database first if enabled
        db_enabled = os.getenv("DATABASE_ENABLED", "false").lower() == "true"

        if db_enabled:
            try:
                self._load_from_database(cutoff_time)
                self._loaded = True
                return
            except Exception as e:
                print(f"  [Dedup] Database loading failed: {e}, falling back to log file")

        # Fallback to log file
        self._load_from_log_file(cutoff_time)
        self._loaded = True

    def _load_from_database(self, cutoff_time: datetime):
        """Load URLs and recent events from PostgreSQL database."""
        from database.connection import SessionLocal
        from database.models import Event as DBEvent

        session = SessionLocal()
        try:
            # Load all URLs
            urls = session.query(DBEvent.link).filter(DBEvent.link.isnot(None)).all()
            self._processed_urls = {url[0] for url in urls if url[0]}

            # Convert to naive datetime for database comparison
            # PostgreSQL stores naive UTC timestamps by default
            cutoff_naive = cutoff_time.replace(tzinfo=None) if cutoff_time.tzinfo else cutoff_time

            # Load recent events with embeddings for semantic comparison
            recent_events = (
                session.query(DBEvent)
                .filter(
                    DBEvent.created_at >= cutoff_naive,
                    DBEvent.embedding.isnot(None)
                )
                .all()
            )

            for event in recent_events:
                # Convert pgvector to list if needed
                embedding = event.embedding
                if embedding is not None:
                    if hasattr(embedding, 'tolist'):
                        embedding = embedding.tolist()
                    elif not isinstance(embedding, list):
                        embedding = list(embedding)

                self._recent_events.append({
                    "event_id": event.event_id,
                    "title": event.title,
                    "embedding": embedding,
                    "timestamp": event.created_at
                })

            print(f"  Dedup loaded from DB: {len(self._processed_urls)} URLs, {len(self._recent_events)} recent events")

        finally:
            session.close()

    def _load_from_log_file(self, cutoff_time: datetime):
        """Load URLs and recent events from JSONL log file."""
        if not os.path.exists(EVENTS_LOG_FILE):
            print(f"  Dedup: No log file found, starting fresh")
            return

        # Convert to naive datetime for comparison with log file timestamps
        # Log files use UTC naive timestamps historically
        cutoff_naive = cutoff_time.replace(tzinfo=None) if cutoff_time.tzinfo else cutoff_time

        with open(EVENTS_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)

                    # Add URL to set
                    if record.get("url"):
                        self._processed_urls.add(record["url"])

                    # Add to recent events if within lookback window and has embedding
                    timestamp_str = record.get("timestamp", "")
                    if timestamp_str:
                        try:
                            timestamp = datetime.fromisoformat(timestamp_str)
                            # Strip timezone for comparison if present
                            timestamp_naive = timestamp.replace(tzinfo=None) if timestamp.tzinfo else timestamp
                            if timestamp_naive > cutoff_naive:
                                self._recent_events.append({
                                    "event_id": record.get("event_id"),
                                    "title": record.get("title", ""),
                                    "embedding": record.get("embedding"),
                                    "timestamp": timestamp
                                })
                        except ValueError:
                            pass

                except json.JSONDecodeError:
                    continue

        print(f"  Dedup loaded from log: {len(self._processed_urls)} URLs, {len(self._recent_events)} recent events")

    def _get_embedding_service(self) -> EmbeddingService:
        """Lazy load embedding service (fallback if EmbeddingAdapter not used)."""
        if self._embedding_service is None:
            self._embedding_service = EmbeddingService()
        return self._embedding_service

    def _check_url_duplicate(self, url: str) -> Optional[str]:
        """Check if URL already processed."""
        if url and url in self._processed_urls:
            return "URL_MATCH"
        return None

    def _check_semantic_duplicate(self, embedding: List[float]) -> Optional[Dict]:
        """
        Check if embedding is semantically similar to recent events.

        Returns dict with event_id and similarity if duplicate found.
        """
        start_time = time.time()
        service = self._get_embedding_service()

        for event in self._recent_events:
            stored_embedding = event.get("embedding")
            if not stored_embedding:
                continue

            similarity = service.cosine_similarity(embedding, stored_embedding)

            if similarity >= SIMILARITY_THRESHOLD:
                check_time = time.time() - start_time
                print(f"    [Dedup] Semantic check completed in {check_time:.3f}s ({len(self._recent_events)} events checked)")
                return {
                    "event_id": event["event_id"],
                    "similarity": similarity,
                    "title": event["title"]
                }

        check_time = time.time() - start_time
        print(f"    [Dedup] Semantic check completed in {check_time:.3f}s (no match, {len(self._recent_events)} events checked)")
        return None

    def run(self, context: ExecutionContext) -> ExecutionContext:
        """
        Check for duplicates using URL and semantic similarity.

        Uses context.event_embedding from EmbeddingAdapter if available.
        Falls back to generating embedding if not set.
        """
        self._load_processed_data()

        url = context.event.url
        title = context.event.title

        # Layer 1: URL check (fast)
        url_match = self._check_url_duplicate(url)
        if url_match:
            context.dedup = DedupResult(
                is_duplicate=True,
                duplicate_type="URL_MATCH",
                duplicate_of=None,
                similarity_score=1.0
            )
            print(f"    [DEDUP] URL match - skipping")
            return context

        # Get embedding from context (set by EmbeddingAdapter) or generate
        embedding = context.event_embedding
        if embedding is None:
            # Fallback: generate embedding if EmbeddingAdapter not in pipeline
            service = self._get_embedding_service()
            embedding = service.encode(title)
            context.event_embedding = embedding

        # Layer 2: Semantic similarity check
        semantic_match = self._check_semantic_duplicate(embedding)
        if semantic_match:
            context.dedup = DedupResult(
                is_duplicate=True,
                duplicate_type="SEMANTIC_MATCH",
                duplicate_of=semantic_match["event_id"],
                similarity_score=semantic_match["similarity"],
                embedding=embedding
            )
            print(f"    [DEDUP] Semantic match ({semantic_match['similarity']:.2f}) with: {semantic_match['title'][:40]}...")
            return context

        # No duplicate - store embedding in dedup result for logging
        context.dedup = DedupResult(
            is_duplicate=False,
            embedding=embedding
        )
        return context
