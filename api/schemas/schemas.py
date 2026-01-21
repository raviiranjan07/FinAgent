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


# ============================================================================
# Evaluation Schemas
# ============================================================================

class EvaluationCreate(BaseModel):
    """Schema for creating an evaluation."""
    output_id: str
    verdict: str  # "PASS" or "FAIL"
    failure_reason: Optional[str] = None
    comment: Optional[str] = None
    evaluator: Optional[str] = "default"


class EvaluationResponse(BaseModel):
    """Evaluation response schema."""
    id: str
    event_id: str
    output_id: str
    verdict: str
    failure_reason: Optional[str] = None
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


# Update forward references
OutputDetailResponse.model_rebuild()
