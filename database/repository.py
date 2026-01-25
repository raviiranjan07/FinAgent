"""Repository layer for database CRUD operations."""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import desc, func, text
from sqlalchemy.orm import Session

from database.models import Event, Output, Evaluation, ContentQueue
from database.connection import get_db_session


class EventRepository:
    """CRUD operations for events."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, event_data: Dict[str, Any]) -> Event:
        """Create a new event."""
        event = Event(**event_data)
        self.db.add(event)
        self.db.flush()  # Get ID without committing
        return event

    def get_by_id(self, event_id: UUID) -> Optional[Event]:
        """Get event by primary key ID."""
        return self.db.query(Event).filter(Event.id == event_id).first()

    def get_by_event_id(self, event_id: str) -> Optional[Event]:
        """Get event by external event_id (UUID string from RSS)."""
        return self.db.query(Event).filter(Event.event_id == event_id).first()

    def get_by_link(self, link: str) -> Optional[Event]:
        """Get event by URL link (for deduplication)."""
        return self.db.query(Event).filter(Event.link == link).first()

    def get_recent(self, hours: int = 72, limit: int = 1000) -> List[Event]:
        """Get events from last N hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return (
            self.db.query(Event)
            .filter(Event.created_at >= cutoff)
            .order_by(desc(Event.created_at))
            .limit(limit)
            .all()
        )

    def get_by_source(self, source: str, limit: int = 100) -> List[Event]:
        """Get events by source."""
        return (
            self.db.query(Event)
            .filter(Event.source == source)
            .order_by(desc(Event.created_at))
            .limit(limit)
            .all()
        )

    def get_all_links(self) -> set:
        """Get all event links (for fast deduplication)."""
        results = self.db.query(Event.link).filter(Event.link.isnot(None)).all()
        return {r[0] for r in results}

    def find_similar(self, embedding: List[float], threshold: float = 0.85, limit: int = 5) -> List[Dict]:
        """Find events with similar embeddings using pgvector."""
        # Using cosine distance (1 - similarity)
        # Lower distance = more similar
        distance_threshold = 1 - threshold

        query = text("""
            SELECT id, event_id, title, embedding <=> :embedding AS distance
            FROM events
            WHERE embedding IS NOT NULL
            AND embedding <=> :embedding < :threshold
            ORDER BY distance
            LIMIT :limit
        """)

        results = self.db.execute(
            query,
            {"embedding": str(embedding), "threshold": distance_threshold, "limit": limit}
        ).fetchall()

        return [
            {
                "id": str(r[0]),
                "event_id": r[1],
                "title": r[2],
                "similarity": 1 - r[3]  # Convert distance back to similarity
            }
            for r in results
        ]

    def update(self, event_id: UUID, data: Dict[str, Any]) -> Optional[Event]:
        """Update event."""
        event = self.get_by_id(event_id)
        if event:
            for key, value in data.items():
                setattr(event, key, value)
            self.db.flush()
        return event

    def delete(self, event_id: UUID) -> bool:
        """Delete event."""
        event = self.get_by_id(event_id)
        if event:
            self.db.delete(event)
            return True
        return False

    def count(self) -> int:
        """Count total events."""
        return self.db.query(func.count(Event.id)).scalar()

    def count_by_source(self) -> Dict[str, int]:
        """Count events grouped by source."""
        results = (
            self.db.query(Event.source, func.count(Event.id))
            .group_by(Event.source)
            .all()
        )
        return {source: count for source, count in results}


class OutputRepository:
    """CRUD operations for LLM outputs."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, output_data: Dict[str, Any]) -> Output:
        """Create a new output."""
        output = Output(**output_data)
        self.db.add(output)
        self.db.flush()
        return output

    def get_by_id(self, output_id: UUID) -> Optional[Output]:
        """Get output by ID."""
        return self.db.query(Output).filter(Output.id == output_id).first()

    def get_by_event_id(self, event_id: UUID) -> List[Output]:
        """Get all outputs for an event."""
        return (
            self.db.query(Output)
            .filter(Output.event_id == event_id)
            .order_by(desc(Output.created_at))
            .all()
        )

    def get_pending_review(self, limit: int = 50) -> List[Output]:
        """Get outputs that need HITL review (not yet evaluated)."""
        # Outputs with hitl_required=True that don't have evaluations yet
        return (
            self.db.query(Output)
            .outerjoin(Evaluation)
            .filter(Output.hitl_required == True)
            .filter(Evaluation.id.is_(None))
            .order_by(desc(Output.created_at))
            .limit(limit)
            .all()
        )

    def get_unevaluated(self, limit: int = 50) -> List[Output]:
        """Get outputs without any evaluation."""
        return (
            self.db.query(Output)
            .outerjoin(Evaluation)
            .filter(Evaluation.id.is_(None))
            .order_by(desc(Output.created_at))
            .limit(limit)
            .all()
        )

    def get_by_event_type(self, event_type: str, limit: int = 100) -> List[Output]:
        """Get outputs by event type."""
        return (
            self.db.query(Output)
            .filter(Output.event_type == event_type)
            .order_by(desc(Output.created_at))
            .limit(limit)
            .all()
        )

    def update(self, output_id: UUID, data: Dict[str, Any]) -> Optional[Output]:
        """Update output."""
        output = self.get_by_id(output_id)
        if output:
            for key, value in data.items():
                setattr(output, key, value)
            self.db.flush()
        return output

    def delete(self, output_id: UUID) -> bool:
        """Delete output."""
        output = self.get_by_id(output_id)
        if output:
            self.db.delete(output)
            return True
        return False

    def count(self) -> int:
        """Count total outputs."""
        return self.db.query(func.count(Output.id)).scalar()

    def count_by_event_type(self) -> Dict[str, int]:
        """Count outputs grouped by event type."""
        results = (
            self.db.query(Output.event_type, func.count(Output.id))
            .group_by(Output.event_type)
            .all()
        )
        return {event_type: count for event_type, count in results}


class EvaluationRepository:
    """CRUD operations for evaluations."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, evaluation_data: Dict[str, Any]) -> Evaluation:
        """Create a new evaluation."""
        evaluation = Evaluation(**evaluation_data)
        self.db.add(evaluation)
        self.db.flush()
        return evaluation

    def get_by_id(self, evaluation_id: UUID) -> Optional[Evaluation]:
        """Get evaluation by ID."""
        return self.db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()

    def get_by_output_id(self, output_id: UUID) -> Optional[Evaluation]:
        """Get evaluation for an output."""
        return self.db.query(Evaluation).filter(Evaluation.output_id == output_id).first()

    def get_recent(self, limit: int = 100) -> List[Evaluation]:
        """Get recent evaluations."""
        return (
            self.db.query(Evaluation)
            .order_by(desc(Evaluation.evaluated_at))
            .limit(limit)
            .all()
        )

    def get_by_verdict(self, verdict: str, limit: int = 100) -> List[Evaluation]:
        """Get evaluations by verdict (PASS/FAIL)."""
        return (
            self.db.query(Evaluation)
            .filter(Evaluation.verdict == verdict)
            .order_by(desc(Evaluation.evaluated_at))
            .limit(limit)
            .all()
        )

    def update(self, evaluation_id: UUID, data: Dict[str, Any]) -> Optional[Evaluation]:
        """Update evaluation."""
        evaluation = self.get_by_id(evaluation_id)
        if evaluation:
            for key, value in data.items():
                setattr(evaluation, key, value)
            self.db.flush()
        return evaluation

    def delete(self, evaluation_id: UUID) -> bool:
        """Delete evaluation."""
        evaluation = self.get_by_id(evaluation_id)
        if evaluation:
            self.db.delete(evaluation)
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get evaluation statistics."""
        total = self.db.query(func.count(Evaluation.id)).scalar()
        pass_count = (
            self.db.query(func.count(Evaluation.id))
            .filter(Evaluation.verdict == "PASS")
            .scalar()
        )
        fail_count = (
            self.db.query(func.count(Evaluation.id))
            .filter(Evaluation.verdict == "FAIL")
            .scalar()
        )

        return {
            "total": total,
            "pass_count": pass_count,
            "fail_count": fail_count,
            "pass_rate": (pass_count / total * 100) if total > 0 else 0,
            "fail_rate": (fail_count / total * 100) if total > 0 else 0,
        }

    def get_failure_reasons(self) -> Dict[str, int]:
        """Get failure reasons grouped by count."""
        results = (
            self.db.query(Evaluation.failure_reason, func.count(Evaluation.id))
            .filter(Evaluation.verdict == "FAIL")
            .filter(Evaluation.failure_reason.isnot(None))
            .group_by(Evaluation.failure_reason)
            .all()
        )
        return {reason: count for reason, count in results}

    def get_agreement_metrics(self) -> Dict[str, Any]:
        """
        Calculate agreement between AI (suggested_verdict) and human (verdict).

        Returns confusion matrix:
        - PP (Predicted PASS, Actual PASS): True Negative
        - PF (Predicted PASS, Actual FAIL): False Negative
        - FP (Predicted FAIL, Actual PASS): False Positive
        - FF (Predicted FAIL, Actual FAIL): True Positive

        Also returns:
        - agreement_rate: % where suggested_verdict == verdict
        - false_positive_rate: % where AI suggests PASS but human marks FAIL
        - total_agreements: count where AI and human agree
        - total_disagreements: count where AI and human disagree
        """
        # Query to join outputs and evaluations, compare verdicts
        results = (
            self.db.query(
                Output.suggested_verdict,
                Evaluation.verdict
            )
            .join(Evaluation, Output.id == Evaluation.output_id)
            .filter(Output.suggested_verdict.isnot(None))
            .filter(Evaluation.verdict.isnot(None))
            .all()
        )

        total = len(results)
        if total == 0:
            return {
                "total": 0,
                "agreements": 0,
                "disagreements": 0,
                "agreement_rate": 0.0,
                "false_positive_rate": 0.0,
                "confusion_matrix": {"PP": 0, "PF": 0, "FP": 0, "FF": 0},
            }

        # Build confusion matrix
        confusion = {"PP": 0, "PF": 0, "FP": 0, "FF": 0}
        agreements = 0
        false_positives = 0

        for ai_verdict, human_verdict in results:
            # Agreement
            if ai_verdict == human_verdict:
                agreements += 1

            # Confusion matrix
            if ai_verdict == "PASS" and human_verdict == "PASS":
                confusion["PP"] += 1
            elif ai_verdict == "PASS" and human_verdict == "FAIL":
                confusion["PF"] += 1
                false_positives += 1  # AI says PASS, human says FAIL
            elif ai_verdict == "FAIL" and human_verdict == "PASS":
                confusion["FP"] += 1
            elif ai_verdict == "FAIL" and human_verdict == "FAIL":
                confusion["FF"] += 1

        disagreements = total - agreements
        agreement_rate = (agreements / total) * 100
        false_positive_rate = (false_positives / total) * 100

        return {
            "total": total,
            "agreements": agreements,
            "disagreements": disagreements,
            "agreement_rate": round(agreement_rate, 2),
            "false_positive_rate": round(false_positive_rate, 2),
            "confusion_matrix": confusion,
        }

    def get_disagreement_examples(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get examples where AI and human disagreed, for pattern analysis.

        Returns list of dicts with:
        - output_id
        - event_type
        - intent
        - suggested_verdict
        - actual_verdict
        - suggested_reason
        - actual_failure_reason
        - llm_output (truncated)
        """
        results = (
            self.db.query(Output, Evaluation)
            .join(Evaluation, Output.id == Evaluation.output_id)
            .filter(Output.suggested_verdict.isnot(None))
            .filter(Output.suggested_verdict != Evaluation.verdict)
            .order_by(desc(Evaluation.evaluated_at))
            .limit(limit)
            .all()
        )

        examples = []
        for output, evaluation in results:
            examples.append({
                "output_id": str(output.id),
                "event_type": output.event_type,
                "intent": output.intent,
                "suggested_verdict": output.suggested_verdict,
                "actual_verdict": evaluation.verdict,
                "suggested_reason": output.suggested_verdict_reason,
                "actual_failure_reason": evaluation.failure_reason,
                "llm_output_preview": output.llm_output[:200] + "..." if len(output.llm_output) > 200 else output.llm_output,
                "evaluated_at": evaluation.evaluated_at,
            })

        return examples

    def get_recent_agreement_rate(self, last_n: int = 30) -> Dict[str, Any]:
        """
        Get agreement rate for the most recent N evaluations.
        Useful for tracking improvement over time.
        """
        results = (
            self.db.query(
                Output.suggested_verdict,
                Evaluation.verdict
            )
            .join(Evaluation, Output.id == Evaluation.output_id)
            .filter(Output.suggested_verdict.isnot(None))
            .order_by(desc(Evaluation.evaluated_at))
            .limit(last_n)
            .all()
        )

        total = len(results)
        if total == 0:
            return {"total": 0, "agreements": 0, "agreement_rate": 0.0}

        agreements = sum(1 for ai, human in results if ai == human)
        rate = (agreements / total) * 100

        return {
            "total": total,
            "agreements": agreements,
            "agreement_rate": round(rate, 2),
        }


class ContentQueueRepository:
    """CRUD operations for content queue."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, content_data: Dict[str, Any]) -> ContentQueue:
        """Create a new content queue item."""
        content = ContentQueue(**content_data)
        self.db.add(content)
        self.db.flush()
        return content

    def get_by_id(self, content_id: UUID) -> Optional[ContentQueue]:
        """Get content by ID."""
        return self.db.query(ContentQueue).filter(ContentQueue.id == content_id).first()

    def get_by_status(self, status: str, limit: int = 50) -> List[ContentQueue]:
        """Get content by status."""
        return (
            self.db.query(ContentQueue)
            .filter(ContentQueue.status == status)
            .order_by(desc(ContentQueue.created_at))
            .limit(limit)
            .all()
        )

    def get_pending(self, limit: int = 50) -> List[ContentQueue]:
        """Get pending content for review."""
        return self.get_by_status("pending", limit)

    def get_approved(self, limit: int = 50) -> List[ContentQueue]:
        """Get approved content ready for scheduling."""
        return self.get_by_status("approved", limit)

    def get_scheduled(self, limit: int = 50) -> List[ContentQueue]:
        """Get scheduled content."""
        return (
            self.db.query(ContentQueue)
            .filter(ContentQueue.status == "scheduled")
            .filter(ContentQueue.scheduled_for.isnot(None))
            .order_by(ContentQueue.scheduled_for)
            .limit(limit)
            .all()
        )

    def get_ready_to_publish(self) -> List[ContentQueue]:
        """Get content scheduled for now or past."""
        now = datetime.utcnow()
        return (
            self.db.query(ContentQueue)
            .filter(ContentQueue.status == "scheduled")
            .filter(ContentQueue.scheduled_for <= now)
            .order_by(ContentQueue.scheduled_for)
            .all()
        )

    def update_status(self, content_id: UUID, status: str) -> Optional[ContentQueue]:
        """Update content status."""
        content = self.get_by_id(content_id)
        if content:
            content.status = status
            content.updated_at = datetime.utcnow()
            self.db.flush()
        return content

    def approve(self, content_id: UUID, edited_content: str = None) -> Optional[ContentQueue]:
        """Approve content."""
        content = self.get_by_id(content_id)
        if content:
            content.status = "approved"
            if edited_content:
                content.edited_content = edited_content
            content.updated_at = datetime.utcnow()
            self.db.flush()
        return content

    def reject(self, content_id: UUID) -> Optional[ContentQueue]:
        """Reject content."""
        return self.update_status(content_id, "rejected")

    def schedule(self, content_id: UUID, scheduled_for: datetime, platform: str) -> Optional[ContentQueue]:
        """Schedule content for publishing."""
        content = self.get_by_id(content_id)
        if content:
            content.status = "scheduled"
            content.scheduled_for = scheduled_for
            content.platform = platform
            content.updated_at = datetime.utcnow()
            self.db.flush()
        return content

    def mark_published(self, content_id: UUID, platform_post_id: str = None) -> Optional[ContentQueue]:
        """Mark content as published."""
        content = self.get_by_id(content_id)
        if content:
            content.status = "published"
            content.published_at = datetime.utcnow()
            if platform_post_id:
                content.platform_post_id = platform_post_id
            content.updated_at = datetime.utcnow()
            self.db.flush()
        return content

    def delete(self, content_id: UUID) -> bool:
        """Delete content."""
        content = self.get_by_id(content_id)
        if content:
            self.db.delete(content)
            return True
        return False

    def count_by_status(self) -> Dict[str, int]:
        """Count content grouped by status."""
        results = (
            self.db.query(ContentQueue.status, func.count(ContentQueue.id))
            .group_by(ContentQueue.status)
            .all()
        )
        return {status: count for status, count in results}


# Convenience function for getting all repositories
class RepositoryManager:
    """Manager for accessing all repositories with a single session."""

    def __init__(self, db: Session):
        self.db = db
        self.events = EventRepository(db)
        self.outputs = OutputRepository(db)
        self.evaluations = EvaluationRepository(db)
        self.content_queue = ContentQueueRepository(db)

    def commit(self):
        """Commit all changes."""
        self.db.commit()

    def rollback(self):
        """Rollback all changes."""
        self.db.rollback()
