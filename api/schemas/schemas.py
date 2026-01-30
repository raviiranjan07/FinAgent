"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


# ============================================================================
# Event Schemas
# ============================================================================

class EventBase(BaseModel):
    """Base event schema."""
    title: str
    summary: Optional[str] = None
    link: Optional[str] = None
    source: str
    published_at: Optional[datetime] = None


class EventResponse(EventBase):
    """Event response schema."""
    id: str
    event_id: str
    created_at: datetime
    has_output: bool = False
    has_evaluation: bool = False

    class Config:
        from_attributes = True


class EventListResponse(BaseModel):
    """Paginated event list response."""
    items: List[EventResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# Output Schemas
# ============================================================================

class OutputBase(BaseModel):
    """Base output schema."""
    llm_output: str
    event_type: str
    intent: str
    clarity_issues: List[str] = []
    hitl_required: bool = False
    hitl_risk_level: Optional[str] = None


class OutputResponse(OutputBase):
    """Output response schema."""
    id: str
    event_id: str
    created_at: datetime
    # Include event info for context
    event_title: Optional[str] = None
    event_source: Optional[str] = None
    event_published_at: Optional[datetime] = None
    has_evaluation: bool = False
    evaluation_verdict: Optional[str] = None
    # HITL AI suggestion fields
    suggested_verdict: Optional[str] = None
    suggested_verdict_reason: Optional[str] = None
    # Agreement field (computed: suggested == actual)
    ai_human_agreement: Optional[bool] = None
    # Generation metadata (audit trail)
    generation_metadata: Optional[dict] = None

    class Config:
        from_attributes = True


class OutputListResponse(BaseModel):
    """Paginated output list response."""
    items: List[OutputResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class OutputDetailResponse(OutputResponse):
    """Detailed output response with full event data."""
    event: Optional[EventResponse] = None
    evaluation: Optional["EvaluationResponse"] = None
    # Agreement details (full comparison)
    agreement_details: Optional[dict] = None


# ============================================================================
# Evaluation Schemas
# ============================================================================

class EvaluationCreate(BaseModel):
    """Schema for creating an evaluation."""
    output_id: str
    verdict: str  # "PASS", "FAIL", or "ACCEPT"
    failure_reason: Optional[str] = None  # Legacy field, kept for backwards compatibility
    corrected_event_type: Optional[str] = None  # Required for FAIL/ACCEPT
    corrected_intent: Optional[str] = None  # Required for FAIL/ACCEPT
    comment: Optional[str] = None
    evaluator: Optional[str] = "default"


class EvaluationResponse(BaseModel):
    """Evaluation response schema."""
    id: str
    event_id: str
    output_id: str
    verdict: str
    failure_reason: Optional[str] = None  # Legacy field, kept for backwards compatibility
    corrected_event_type: Optional[str] = None
    corrected_intent: Optional[str] = None
    comment: Optional[str] = None
    evaluator: Optional[str] = None
    evaluated_at: datetime

    class Config:
        from_attributes = True


class EvaluationListResponse(BaseModel):
    """Paginated evaluation list response."""
    items: List[EvaluationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# Statistics Schemas
# ============================================================================

class EvaluationStats(BaseModel):
    """Evaluation statistics."""
    total: int
    pass_count: int
    fail_count: int
    pass_rate: float
    fail_rate: float
    pending_count: int  # Outputs without evaluation


class EventTypeStats(BaseModel):
    """Event type distribution."""
    event_type: str
    count: int
    percentage: float


class SourceStats(BaseModel):
    """Source distribution."""
    source: str
    count: int
    percentage: float


class FailureReasonStats(BaseModel):
    """Failure reason distribution."""
    reason: str
    count: int
    percentage: float


class DashboardStats(BaseModel):
    """Complete dashboard statistics."""
    evaluation: EvaluationStats
    event_types: List[EventTypeStats]
    sources: List[SourceStats]
    failure_reasons: List[FailureReasonStats]
    recent_activity: dict


# ============================================================================
# HITL Agreement Metrics Schemas
# ============================================================================

class AgreementMetrics(BaseModel):
    """HITL agreement metrics between AI and human."""
    total: int
    agreements: int
    disagreements: int
    agreement_rate: float  # Percentage
    false_positive_rate: float  # AI says PASS, human says FAIL
    confusion_matrix: dict  # {"PP": int, "PF": int, "FP": int, "FF": int}


class DisagreementExample(BaseModel):
    """Example where AI and human disagreed."""
    output_id: str
    event_type: str
    intent: str
    suggested_verdict: str
    actual_verdict: str
    suggested_reason: Optional[str] = None
    actual_failure_reason: Optional[str] = None
    llm_output_preview: str
    evaluated_at: datetime


class HITLMetrics(BaseModel):
    """Complete HITL metrics for exit criteria tracking."""
    overall_metrics: AgreementMetrics
    recent_metrics: AgreementMetrics  # Last 30 evaluations
    target_rate: float  # 90.0
    status: str  # "on_track" | "needs_improvement" | "achieved"
    progress_percentage: float  # (current / target) * 100
    remaining_to_target: float  # Percentage points
    disagreement_examples: List[DisagreementExample]


# Update forward references
OutputDetailResponse.model_rebuild()
