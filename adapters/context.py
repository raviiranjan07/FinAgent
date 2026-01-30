"""Execution context and HITL decision models for adapter pipeline."""

from pydantic import BaseModel
from typing import Optional, List, Any, Dict
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
    suggested_verdict: Optional[str] = None  # PASS or FAIL
    suggested_verdict_reason: Optional[str] = None  # Reason for FAIL verdict


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
    event_type_confidence: Optional[float] = None  # ML classifier confidence (0-1)
    secondary_event_type: Optional[str] = None  # Secondary category if multi-label
    secondary_event_type_confidence: Optional[float] = None  # Secondary label confidence
    intent: Optional[str] = None
    intent_confidence: Optional[float] = None  # ML classifier confidence (0-1)
    llm_output: Optional[str] = None
    llm_model: Optional[str] = None  # LLM model name that generated the output
    clarity_issues: List[str] = []
    hitl: Optional[HITLDecision] = None
    log_record: Optional[dict] = None
    dedup: Optional[DedupResult] = None  # Deduplication result

    # Embeddings (Pre-MVP)
    embedding: Optional[List[float]] = None  # 384-dim vector for event (used by ML classifier)
    event_embedding: Optional[List[float]] = None  # Alias for embedding (legacy)
    output_embedding: Optional[List[float]] = None  # 384-dim vector for output

    # Database IDs (Pre-MVP)
    db_event_id: Optional[str] = None  # PostgreSQL event UUID
    db_output_id: Optional[str] = None  # PostgreSQL output UUID

    # Generation Metadata (Pre-MVP)
    generation_metadata: Optional[dict] = None  # LLM generation metadata (model, prompt version, etc.)

    # Plugin Namespace (NEW - v2.0 Architecture)
    # Each plugin stores its data in plugins[plugin_name] instead of polluting the root context
    # Example: plugins["twitter"] = {"format": "THREAD", "content": {...}, "clarity_passed": True}
    plugins: Dict[str, Any] = {}

    # Twitter Plugin Fields (DEPRECATED - kept for backward compatibility)
    # TODO: Remove after migration to plugins["twitter"] namespace
    impact_framing: Optional[dict] = None  # Impact framing analysis (angle, what_this_is_not, etc.)
    twitter_format: Optional[dict] = None  # Format decision (SINGLE or THREAD)
    twitter_content: Optional[dict] = None  # Generated Twitter content
    twitter_clarity_issues: List[str] = []  # Twitter-specific clarity issues
    twitter_clarity_passed: bool = True  # Twitter clarity validation result
    twitter_hitl: Optional[HITLDecision] = None  # Twitter HITL decision

    def get_plugin_data(self, plugin_name: str, default: Any = None) -> Any:
        """
        Get plugin data from namespace with fallback to legacy fields.

        Args:
            plugin_name: Plugin identifier (e.g., "twitter")
            default: Default value if not found

        Returns:
            Plugin data dict or default value
        """
        return self.plugins.get(plugin_name, default)

    def set_plugin_data(self, plugin_name: str, data: Dict[str, Any]) -> None:
        """
        Set plugin data in namespace.

        Args:
            plugin_name: Plugin identifier (e.g., "twitter")
            data: Plugin data to store
        """
        self.plugins[plugin_name] = data

    def update_plugin_data(self, plugin_name: str, updates: Dict[str, Any]) -> None:
        """
        Update specific fields in plugin data.

        Args:
            plugin_name: Plugin identifier (e.g., "twitter")
            updates: Fields to update
        """
        if plugin_name not in self.plugins:
            self.plugins[plugin_name] = {}
        self.plugins[plugin_name].update(updates)

    class Config:
        arbitrary_types_allowed = True
