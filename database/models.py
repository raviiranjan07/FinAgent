"""SQLAlchemy models for FinAgent Pre-MVP."""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, Integer, Float, ForeignKey, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base
from pgvector.sqlalchemy import Vector

from utils.timezone import get_ist_now

Base = declarative_base()


class Event(Base):
    """Raw RSS events with embeddings."""

    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(String(255), unique=True, nullable=False)
    title = Column(Text, nullable=False)
    summary = Column(Text)
    link = Column(Text)
    source = Column(String(100), nullable=False)
    published_at = Column(DateTime)
    fetched_at = Column(DateTime, default=get_ist_now)
    embedding = Column(Vector(384))  # all-minilm dimension
    created_at = Column(DateTime, default=get_ist_now)

    # Relationships
    outputs = relationship("Output", back_populates="event", cascade="all, delete-orphan")
    evaluations = relationship("Evaluation", back_populates="event", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_events_source", "source"),
        Index("idx_events_published_at", "published_at"),
        Index("idx_events_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<Event(id={self.id}, title='{self.title[:50]}...')>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": str(self.id),
            "event_id": self.event_id,
            "title": self.title,
            "summary": self.summary,
            "link": self.link,
            "source": self.source,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Output(Base):
    """LLM generated content."""

    __tablename__ = "outputs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"))
    llm_output = Column(Text, nullable=False)
    event_type = Column(String(50), nullable=False)
    intent = Column(String(50), nullable=False)
    clarity_issues = Column(JSONB, default=list)
    hitl_required = Column(Boolean, default=False)
    hitl_risk_level = Column(String(20))
    suggested_verdict = Column(String(10))  # PASS or FAIL
    suggested_verdict_reason = Column(String(100))  # Reason for FAIL
    output_embedding = Column(Vector(384))
    llm_model = Column(String(100))  # LLM model used (e.g., gemini-2.5-flash, qwen/qwen3-32b, llama3)
    generation_metadata = Column(JSONB, default=dict, nullable=False)  # Immutable snapshot of generation config
    created_at = Column(DateTime, default=get_ist_now)

    # Relationships
    event = relationship("Event", back_populates="outputs")
    evaluations = relationship("Evaluation", back_populates="output", cascade="all, delete-orphan")
    content_items = relationship("ContentQueue", back_populates="output", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_outputs_event_id", "event_id"),
        Index("idx_outputs_event_type", "event_type"),
    )

    def __repr__(self):
        return f"<Output(id={self.id}, event_type='{self.event_type}')>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": str(self.id),
            "event_id": str(self.event_id),
            "llm_output": self.llm_output,
            "event_type": self.event_type,
            "intent": self.intent,
            "clarity_issues": self.clarity_issues,
            "hitl_required": self.hitl_required,
            "hitl_risk_level": self.hitl_risk_level,
            "suggested_verdict": self.suggested_verdict,
            "suggested_verdict_reason": self.suggested_verdict_reason,
            "llm_model": self.llm_model,
            "generation_metadata": self.generation_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Evaluation(Base):
    """Human evaluation verdicts."""

    __tablename__ = "evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"))
    output_id = Column(UUID(as_uuid=True), ForeignKey("outputs.id", ondelete="CASCADE"))
    verdict = Column(String(10), nullable=False)
    failure_reason = Column(Text)
    comment = Column(Text)
    evaluator = Column(String(100))
    evaluated_at = Column(DateTime, default=get_ist_now)

    # Training data correction fields (added in migration 015)
    # For ACCEPT/FAIL verdicts: stores human-corrected classification
    corrected_event_type = Column(String(50))
    corrected_intent = Column(String(50))

    # Auto-approval tracking (added in migration 010)
    auto_approved = Column(Boolean, default=False)
    confidence_score = Column(Float)
    confidence_signals = Column(JSONB)
    similar_outputs_count = Column(Integer)

    # Relationships
    event = relationship("Event", back_populates="evaluations")
    output = relationship("Output", back_populates="evaluations")

    __table_args__ = (
        CheckConstraint("verdict IN ('PASS', 'FAIL', 'ACCEPT')", name="check_verdict"),
        Index("idx_evaluations_verdict", "verdict"),
        Index("idx_evaluations_auto_approved", "auto_approved"),
    )

    def __repr__(self):
        return f"<Evaluation(id={self.id}, verdict='{self.verdict}')>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": str(self.id),
            "event_id": str(self.event_id),
            "output_id": str(self.output_id),
            "verdict": self.verdict,
            "failure_reason": self.failure_reason,
            "comment": self.comment,
            "evaluator": self.evaluator,
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None,
            "corrected_event_type": self.corrected_event_type,
            "corrected_intent": self.corrected_intent,
            "auto_approved": self.auto_approved,
            "confidence_score": self.confidence_score,
            "confidence_signals": self.confidence_signals,
            "similar_outputs_count": self.similar_outputs_count,
        }


class ContentQueue(Base):
    """Content queue for Twitter plugin publishing workflow."""

    __tablename__ = "content_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    output_id = Column(UUID(as_uuid=True), ForeignKey("outputs.id", ondelete="CASCADE"))

    # Event reference (denormalized for quick access)
    event_title = Column(String(500), nullable=False)
    event_type = Column(String(50))
    event_url = Column(String(500))

    # Impact framing (JSON stored as TEXT)
    impact_framing = Column(Text)  # JSON: primary_angle, what_this_is_not, etc.

    # Format decision
    format = Column(String(20), nullable=False)  # SINGLE or THREAD
    thread_length = Column(Integer, default=1)

    # Twitter content
    content_text = Column(Text, nullable=False)  # For SINGLE: tweet. For THREAD: JSON array
    edited_content = Column(Text)  # User-edited version
    hashtags = Column(String(200))  # Comma-separated hashtags

    # HITL (Human-in-the-Loop) decision
    hitl_required = Column(Boolean, default=False)
    hitl_risk_level = Column(String(20))  # LOW, MEDIUM, HIGH
    suggested_verdict = Column(String(20))  # PASS, FAIL
    suggested_verdict_reason = Column(String(100))  # Reason code

    # Publishing metadata
    status = Column(String(50), nullable=False, default="pending_generation")
    error_message = Column(Text)  # Error details if generation fails
    scheduled_for = Column(DateTime)  # When to publish (NULL = immediate)
    twitter_post_id = Column(String(100))  # Twitter post ID after publishing
    published_at = Column(DateTime)
    orphaned_tweet_ids = Column(JSONB)  # Orphaned tweet IDs if thread fails mid-posting

    # Retry tracking (added in migration 011)
    publish_attempts = Column(Integer, default=0)  # Total attempts (never resets)
    retry_count = Column(Integer, default=0)  # Current retry cycle (resets on success, max 3)
    last_publish_attempt = Column(DateTime)  # For exponential backoff calculation
    rate_limit_reset = Column(DateTime)  # Twitter rate limit reset time (if 429 error)

    # Generation tracking (for version control and debugging)
    plugin_version = Column(String(50))  # e.g., "twitter-v1.6-notoken"
    prompt_version = Column(String(100))  # e.g., "TWITTER_GENERATION_THREAD_v1.6-notoken"
    model_used = Column(String(100))  # e.g., "qwen/qwen3-32b"
    generation_timestamp = Column(DateTime)  # When content was generated
    generation_context = Column(JSONB, default=dict)  # Full snapshot for debugging

    # Pipeline versioning (for parallel pipeline testing)
    pipeline_version = Column(String(10), default='v1')  # 'v1' (via outputs) or 'v2' (direct)
    source_event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"))  # Direct link to event (v2 pipeline)
    generation_intent = Column(String(50))  # Intent used for generation (enables regeneration)

    # Audit fields
    created_at = Column(DateTime, default=get_ist_now)
    updated_at = Column(DateTime, default=get_ist_now, onupdate=get_ist_now)

    # Relationships
    output = relationship("Output", back_populates="content_items")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending_generation', 'generating', 'ready_to_schedule', 'scheduled', 'published', 'failed')",
            name="check_status"
        ),
        Index("idx_content_queue_output_id", "output_id"),
        Index("idx_content_queue_status", "status"),
        Index("idx_content_queue_created_at", "created_at"),
        Index("idx_content_queue_format", "format"),
        Index("idx_content_queue_plugin_version", "plugin_version"),
        Index("idx_content_queue_model_used", "model_used"),
        Index("idx_content_queue_scheduled_for", "scheduled_for"),
        Index("idx_content_queue_pipeline_version", "pipeline_version"),
        Index("idx_content_queue_source_event_id", "source_event_id"),
    )

    def __repr__(self):
        return f"<ContentQueue(id={self.id}, format='{self.format}', status='{self.status}')>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": str(self.id),
            "output_id": str(self.output_id),
            "event_title": self.event_title,
            "event_type": self.event_type,
            "event_url": self.event_url,
            "format": self.format,
            "thread_length": self.thread_length,
            "content_text": self.content_text,
            "edited_content": self.edited_content,
            "hashtags": self.hashtags,
            "status": self.status,
            "scheduled_for": self.scheduled_for.isoformat() if self.scheduled_for else None,
            "twitter_post_id": self.twitter_post_id,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "orphaned_tweet_ids": self.orphaned_tweet_ids,
            "publish_attempts": self.publish_attempts,
            "retry_count": self.retry_count,
            "last_publish_attempt": self.last_publish_attempt.isoformat() if self.last_publish_attempt else None,
            "rate_limit_reset": self.rate_limit_reset.isoformat() if self.rate_limit_reset else None,
            "error_message": self.error_message,
            "plugin_version": self.plugin_version,
            "prompt_version": self.prompt_version,
            "model_used": self.model_used,
            "generation_timestamp": self.generation_timestamp.isoformat() if self.generation_timestamp else None,
            "generation_context": self.generation_context,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class GeneratedContent(Base):
    """Platform-specific formatted content (Twitter, LinkedIn, Newsletter)."""

    __tablename__ = "generated_content"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    output_id = Column(UUID(as_uuid=True), ForeignKey("outputs.id", ondelete="CASCADE"))
    content_queue_id = Column(UUID(as_uuid=True), ForeignKey("content_queue.id", ondelete="CASCADE"))

    # Platform Info
    platform = Column(String(50), nullable=False)

    # Generated Content
    content_text = Column(Text, nullable=False)
    hashtags = Column(JSONB, default=list)
    character_count = Column(Integer)

    # Format metadata (for analytics later)
    format_style = Column(String(50))

    # Metadata
    generated_at = Column(DateTime, default=get_ist_now)
    created_at = Column(DateTime, default=get_ist_now)

    # Relationships
    output = relationship("Output")
    # Note: ContentQueue no longer has generated_content relationship (Twitter plugin uses content_text directly)
    content_queue = relationship("ContentQueue")

    __table_args__ = (
        Index("idx_generated_content_platform", "platform"),
        Index("idx_generated_content_output_id", "output_id"),
        Index("idx_generated_content_queue_id", "content_queue_id"),
    )

    def __repr__(self):
        return f"<GeneratedContent(id={self.id}, platform='{self.platform}', chars={self.character_count})>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": str(self.id),
            "output_id": str(self.output_id),
            "content_queue_id": str(self.content_queue_id),
            "platform": self.platform,
            "content_text": self.content_text,
            "hashtags": self.hashtags,
            "character_count": self.character_count,
            "format_style": self.format_style,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
