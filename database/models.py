"""SQLAlchemy models for FinAgent Pre-MVP."""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, ForeignKey, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base
from pgvector.sqlalchemy import Vector

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
    fetched_at = Column(DateTime, default=datetime.utcnow)
    embedding = Column(Vector(384))  # all-minilm dimension
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    outputs = relationship("Output", back_populates="event", cascade="all, delete-orphan")
    evaluations = relationship("Evaluation", back_populates="event", cascade="all, delete-orphan")
    content_items = relationship("ContentQueue", back_populates="event", cascade="all, delete-orphan")

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
    output_embedding = Column(Vector(384))
    created_at = Column(DateTime, default=datetime.utcnow)

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
    evaluated_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    event = relationship("Event", back_populates="evaluations")
    output = relationship("Output", back_populates="evaluations")

    __table_args__ = (
        CheckConstraint("verdict IN ('PASS', 'FAIL')", name="check_verdict"),
        Index("idx_evaluations_verdict", "verdict"),
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
        }


class ContentQueue(Base):
    """Content queue for publishing workflow."""

    __tablename__ = "content_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"))
    output_id = Column(UUID(as_uuid=True), ForeignKey("outputs.id", ondelete="CASCADE"))
    status = Column(String(20), nullable=False, default="pending")
    edited_content = Column(Text)
    scheduled_for = Column(DateTime)
    published_at = Column(DateTime)
    platform = Column(String(50))
    platform_post_id = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    event = relationship("Event", back_populates="content_items")
    output = relationship("Output", back_populates="content_items")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'scheduled', 'published')",
            name="check_status"
        ),
        Index("idx_content_queue_status", "status"),
    )

    def __repr__(self):
        return f"<ContentQueue(id={self.id}, status='{self.status}')>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": str(self.id),
            "event_id": str(self.event_id),
            "output_id": str(self.output_id),
            "status": self.status,
            "edited_content": self.edited_content,
            "scheduled_for": self.scheduled_for.isoformat() if self.scheduled_for else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "platform": self.platform,
            "platform_post_id": self.platform_post_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
