"""Execution context and HITL decision models for adapter pipeline."""

from pydantic import BaseModel
from typing import Optional, List, Any
from models.event import Event


class HITLDecision(BaseModel):
    """
    Human-in-the-Loop decision schema.

    As per documentation Section 4.6.2 HITL Decision Schema.
    """
    required: bool = False
    reasons: List[str] = []
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH
    auto_action: str = "PROCEED"  # PROCEED, FLAG, BLOCK


class DedupResult(BaseModel):
    """
    Deduplication result schema.

    Tracks whether an event is a duplicate and related info.
    """
    is_duplicate: bool = False
    duplicate_type: Optional[str] = None  # "URL_MATCH" or "SEMANTIC_MATCH"
    duplicate_of: Optional[str] = None  # event_id of original
    similarity_score: Optional[float] = None  # For semantic matches
    embedding: Optional[List[float]] = None  # 384-dim vector for storage


class ExecutionContext(BaseModel):
    """
    Shared context object passed across all adapters.

    Each adapter reads and writes only to its assigned section.
    As per documentation Section 4.3 ExecutionContext.
    """
    event: Event
    event_type: Optional[str] = None
    intent: Optional[str] = None
    llm_output: Optional[str] = None
    clarity_issues: List[str] = []
    hitl: Optional[HITLDecision] = None
    log_record: Optional[dict] = None
    dedup: Optional[DedupResult] = None  # Deduplication result

    # Embeddings (Pre-MVP)
    event_embedding: Optional[List[float]] = None  # 384-dim vector for event
    output_embedding: Optional[List[float]] = None  # 384-dim vector for output

    # Database IDs (Pre-MVP)
    db_event_id: Optional[str] = None  # PostgreSQL event UUID
    db_output_id: Optional[str] = None  # PostgreSQL output UUID

    class Config:
        arbitrary_types_allowed = True
