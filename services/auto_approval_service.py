"""Auto-Approval Service for HITL Workflow.

This service implements intelligent auto-approval of high-confidence outputs
to reduce manual review burden by ~80% while maintaining safety.

Decision Criteria:
- Confidence score >= 95% (weighted multi-signal)
- 10+ similar outputs with PASS verdicts
- AI suggested_verdict = PASS
- Risk level != HIGH

Confidence Calculation:
    Confidence = (
        35% × Clarity Score +
        25% × Similarity Score +
        20% × Event Type Pass Rate +
        10% × Intent Pass Rate +
        10% × Source Reliability
    )
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, text
from pgvector.sqlalchemy import Vector

from database.models import Output, Evaluation, Event
from database.connection import get_db_session
from utils.timezone import get_ist_now

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceSignals:
    """Breakdown of confidence signals for transparency."""
    clarity_score: float  # 0-100
    similarity_score: float  # 0-100
    event_type_pass_rate: float  # 0-100
    intent_pass_rate: float  # 0-100
    source_reliability: float  # 0-100
    similar_outputs_count: int
    similar_outputs: List[Dict]  # List of {output_id, similarity, verdict}


@dataclass
class AutoApprovalDecision:
    """Result of auto-approval evaluation."""
    should_auto_approve: bool
    confidence_score: float  # 0-100
    signals: ConfidenceSignals
    reason: str


class AutoApprovalService:
    """Service for auto-approving high-confidence outputs."""

    # Thresholds
    CONFIDENCE_THRESHOLD = 95.0  # Minimum confidence score for auto-approval
    SIMILARITY_THRESHOLD = 0.85  # Minimum cosine similarity for "similar" outputs
    MIN_SIMILAR_PASS = 10  # Minimum number of similar PASS items required

    # Signal weights (must sum to 100)
    WEIGHT_CLARITY = 35.0
    WEIGHT_SIMILARITY = 25.0
    WEIGHT_EVENT_TYPE = 20.0
    WEIGHT_INTENT = 10.0
    WEIGHT_SOURCE = 10.0

    # Source reliability scores
    SOURCE_SCORES = {
        "RBI_PRESS": 100.0,
        "SEBI": 100.0,
        "FED_ALL": 100.0,
        "FED_MONETARY": 100.0,
        "ECB": 100.0,
        "BOE": 100.0,
        "BOJ": 100.0,
        "BLOOMBERG": 95.0,
        "REUTERS_BUSINESS": 95.0,
        "REUTERS_MARKETS": 95.0,
        "FINANCIAL_TIMES": 95.0,
        "ET_MARKETS": 90.0,
        "ET_ECONOMY": 90.0,
        "MONEYCONTROL": 85.0,
        "LIVEMINT": 85.0,
        "BUSINESS_STANDARD": 85.0,
        "CNBC_TOP": 80.0,
        "MARKETWATCH": 80.0,
        "YAHOO_FINANCE": 75.0,
        "COINDESK": 70.0,
        "COINTELEGRAPH": 70.0,
    }
    DEFAULT_SOURCE_SCORE = 50.0  # For unknown sources

    def __init__(self, db: Session):
        self.db = db

    def calculate_confidence(self, output: Output) -> AutoApprovalDecision:
        """
        Calculate weighted confidence score from multiple signals.

        Args:
            output: Output object to evaluate

        Returns:
            AutoApprovalDecision with score, signals, and decision
        """
        # 1. Calculate Clarity Score (35%)
        clarity_score = self._calculate_clarity_score(output)

        # 2. Calculate Similarity Score (25%)
        similarity_score, similar_outputs = self._calculate_similarity_score(output)

        # 3. Calculate Event Type Pass Rate (20%)
        event_type_pass_rate = self._get_pass_rate("event_type", output.event_type)

        # 4. Calculate Intent Pass Rate (10%)
        intent_pass_rate = self._get_pass_rate("intent", output.intent)

        # 5. Calculate Source Reliability (10%)
        event = self.db.query(Event).filter(Event.id == output.event_id).first()
        source_score = self._get_source_score(event.source if event else None)

        # Calculate weighted confidence score
        confidence_score = (
            (self.WEIGHT_CLARITY * clarity_score / 100) +
            (self.WEIGHT_SIMILARITY * similarity_score / 100) +
            (self.WEIGHT_EVENT_TYPE * event_type_pass_rate / 100) +
            (self.WEIGHT_INTENT * intent_pass_rate / 100) +
            (self.WEIGHT_SOURCE * source_score / 100)
        )

        # Build signals object
        signals = ConfidenceSignals(
            clarity_score=clarity_score,
            similarity_score=similarity_score,
            event_type_pass_rate=event_type_pass_rate,
            intent_pass_rate=intent_pass_rate,
            source_reliability=source_score,
            similar_outputs_count=len(similar_outputs),
            similar_outputs=similar_outputs
        )

        # Determine if should auto-approve
        should_approve, reason = self._should_auto_approve(output, confidence_score, signals)

        return AutoApprovalDecision(
            should_auto_approve=should_approve,
            confidence_score=confidence_score,
            signals=signals,
            reason=reason
        )

    def _calculate_clarity_score(self, output: Output) -> float:
        """
        Calculate clarity score based on clarity_issues.

        Scoring:
        - 0 issues = 100%
        - 1 issue = 85%
        - 2 issues = 70%
        - 3+ issues = 55%
        """
        num_issues = len(output.clarity_issues) if output.clarity_issues else 0

        if num_issues == 0:
            return 100.0
        elif num_issues == 1:
            return 85.0
        elif num_issues == 2:
            return 70.0
        else:
            return 55.0

    def _calculate_similarity_score(self, output: Output) -> Tuple[float, List[Dict]]:
        """
        Calculate similarity score using pgvector cosine similarity.

        Find similar PASS outputs:
        - Same event_type
        - Cosine similarity >= 0.85
        - Has evaluation with verdict = PASS

        Score = min(100, (pass_count / 10) × 100)

        Returns:
            Tuple of (score, list of similar outputs with metadata)
        """
        if output.output_embedding is None:
            logger.warning(f"Output {output.id} has no embedding - similarity score = 0")
            return 0.0, []

        # Query similar outputs with PASS verdicts
        # Using pgvector cosine similarity operator <=>
        query = text("""
            SELECT
                o.id,
                o.event_type,
                o.llm_output,
                e.verdict,
                1 - (o.output_embedding <=> :embedding) AS similarity
            FROM outputs o
            INNER JOIN evaluations e ON e.output_id = o.id
            WHERE
                o.event_type = :event_type
                AND e.verdict = 'PASS'
                AND o.id != :output_id
                AND 1 - (o.output_embedding <=> :embedding) >= :threshold
            ORDER BY similarity DESC
            LIMIT 20
        """)

        results = self.db.execute(
            query,
            {
                "embedding": str(output.output_embedding),
                "event_type": output.event_type,
                "output_id": output.id,
                "threshold": self.SIMILARITY_THRESHOLD
            }
        ).fetchall()

        similar_outputs = [
            {
                "output_id": str(row[0]),
                "event_type": row[1],
                "similarity": float(row[4]),
                "verdict": row[3]
            }
            for row in results
        ]

        pass_count = len(similar_outputs)
        similarity_score = min(100.0, (pass_count / self.MIN_SIMILAR_PASS) * 100)

        logger.info(f"Found {pass_count} similar PASS outputs for output {output.id} - score: {similarity_score:.1f}%")

        return similarity_score, similar_outputs

    def _get_pass_rate(self, stat_type: str, stat_key: str) -> float:
        """
        Get cached pass rate from confidence_stats_cache table.

        If not cached, calculate and cache it.

        Args:
            stat_type: 'event_type', 'intent', or 'source'
            stat_key: The value (e.g., 'FINANCE_POLICY', 'EXPLANATORY')

        Returns:
            Pass rate as percentage (0-100)
        """
        # Check cache first
        cache_query = text("""
            SELECT pass_rate, last_updated
            FROM confidence_stats_cache
            WHERE stat_type = :stat_type AND stat_key = :stat_key
        """)

        cached = self.db.execute(
            cache_query,
            {"stat_type": stat_type, "stat_key": stat_key}
        ).fetchone()

        # Use cache if updated within last 24 hours
        if cached and (get_ist_now() - cached[1]) < timedelta(hours=24):
            return cached[0]

        # Calculate pass rate
        if stat_type == "event_type":
            filter_col = "event_type"
        elif stat_type == "intent":
            filter_col = "intent"
        elif stat_type == "source":
            # For source, join with events table
            query = text("""
                SELECT
                    COUNT(*) FILTER (WHERE e.verdict = 'PASS') AS pass_count,
                    COUNT(*) AS total_count
                FROM evaluations e
                INNER JOIN outputs o ON o.id = e.output_id
                INNER JOIN events ev ON ev.id = o.event_id
                WHERE ev.source = :stat_key
            """)

            result = self.db.execute(query, {"stat_key": stat_key}).fetchone()
            total_count = result[1] if result else 0
            pass_count = result[0] if result else 0

            pass_rate = (pass_count / total_count * 100) if total_count > 0 else 50.0

            # Update cache
            self._update_cache(stat_type, stat_key, pass_rate, total_count, pass_count)

            return pass_rate

        # For event_type and intent
        query = text(f"""
            SELECT
                COUNT(*) FILTER (WHERE e.verdict = 'PASS') AS pass_count,
                COUNT(*) AS total_count
            FROM evaluations e
            INNER JOIN outputs o ON o.id = e.output_id
            WHERE o.{filter_col} = :stat_key
        """)

        result = self.db.execute(query, {"stat_key": stat_key}).fetchone()
        total_count = result[1] if result else 0
        pass_count = result[0] if result else 0

        pass_rate = (pass_count / total_count * 100) if total_count > 0 else 50.0

        # Update cache
        self._update_cache(stat_type, stat_key, pass_rate, total_count, pass_count)

        return pass_rate

    def _update_cache(self, stat_type: str, stat_key: str, pass_rate: float,
                      total_count: int, pass_count: int):
        """Update confidence_stats_cache with new pass rate."""
        query = text("""
            INSERT INTO confidence_stats_cache (stat_type, stat_key, pass_rate, total_count, pass_count, last_updated)
            VALUES (:stat_type, :stat_key, :pass_rate, :total_count, :pass_count, :last_updated)
            ON CONFLICT (stat_type, stat_key)
            DO UPDATE SET
                pass_rate = :pass_rate,
                total_count = :total_count,
                pass_count = :pass_count,
                last_updated = :last_updated
        """)

        self.db.execute(query, {
            "stat_type": stat_type,
            "stat_key": stat_key,
            "pass_rate": pass_rate,
            "total_count": total_count,
            "pass_count": pass_count,
            "last_updated": get_ist_now()
        })
        self.db.commit()

    def _get_source_score(self, source: Optional[str]) -> float:
        """Get reliability score for source."""
        if source is None:
            return self.DEFAULT_SOURCE_SCORE

        return self.SOURCE_SCORES.get(source, self.DEFAULT_SOURCE_SCORE)

    def _should_auto_approve(self, output: Output, confidence_score: float,
                            signals: ConfidenceSignals) -> Tuple[bool, str]:
        """
        Determine if output should be auto-approved.

        Criteria:
        - Confidence >= 95%
        - Similar PASS count >= 10
        - Suggested verdict = PASS
        - Risk level != HIGH

        Returns:
            Tuple of (should_approve, reason)
        """
        # Check confidence threshold
        if confidence_score < self.CONFIDENCE_THRESHOLD:
            return False, f"Confidence {confidence_score:.1f}% below threshold {self.CONFIDENCE_THRESHOLD}%"

        # Check similar PASS count
        if signals.similar_outputs_count < self.MIN_SIMILAR_PASS:
            return False, f"Only {signals.similar_outputs_count} similar PASS items (need {self.MIN_SIMILAR_PASS})"

        # Check suggested verdict
        if output.suggested_verdict != "PASS":
            return False, f"Suggested verdict is {output.suggested_verdict}, not PASS"

        # Check risk level
        if output.hitl_risk_level == "HIGH":
            return False, "Risk level is HIGH"

        # All criteria met
        return True, f"Auto-approved: {confidence_score:.1f}% confidence, {signals.similar_outputs_count} similar PASS items"

    def auto_approve_if_eligible(self, output_id: uuid.UUID) -> Optional[Evaluation]:
        """
        Auto-approve output if eligible.

        Args:
            output_id: UUID of output to evaluate

        Returns:
            Evaluation object if auto-approved, None if manual review required
        """
        # Get output
        output = self.db.query(Output).filter(Output.id == output_id).first()
        if not output:
            logger.error(f"Output {output_id} not found")
            return None

        # Check if already evaluated
        existing = self.db.query(Evaluation).filter(Evaluation.output_id == output_id).first()
        if existing:
            logger.info(f"Output {output_id} already evaluated with verdict {existing.verdict}")
            return existing

        # Calculate confidence
        decision = self.calculate_confidence(output)

        # Log to auto_approval_history
        self._log_auto_approval_history(output, decision)

        # If should auto-approve, create evaluation
        if decision.should_auto_approve:
            evaluation = Evaluation(
                id=uuid.uuid4(),
                event_id=output.event_id,
                output_id=output.id,
                verdict="PASS",
                comment=f"Auto-approved: {decision.reason}",
                evaluator="auto_approval_service",
                evaluated_at=get_ist_now()
            )

            # Add auto-approval metadata (will be added after migration)
            # evaluation.auto_approved = True
            # evaluation.confidence_score = decision.confidence_score
            # evaluation.confidence_signals = decision.signals.__dict__
            # evaluation.similar_outputs_count = decision.signals.similar_outputs_count

            self.db.add(evaluation)
            self.db.commit()
            self.db.refresh(evaluation)

            logger.info(f"[OK] Auto-approved output {output_id} - {decision.reason}")
            return evaluation

        logger.info(f"⏸ Manual review required for output {output_id} - {decision.reason}")
        return None

    def _log_auto_approval_history(self, output: Output, decision: AutoApprovalDecision):
        """Log auto-approval decision to audit history."""
        query = text("""
            INSERT INTO auto_approval_history
            (id, output_id, confidence_score, confidence_signals, similar_outputs, auto_approved, reason, created_at)
            VALUES (:id, :output_id, :confidence_score, :confidence_signals, :similar_outputs, :auto_approved, :reason, :created_at)
        """)

        self.db.execute(query, {
            "id": uuid.uuid4(),
            "output_id": output.id,
            "confidence_score": decision.confidence_score,
            "confidence_signals": {
                "clarity": decision.signals.clarity_score,
                "similarity": decision.signals.similarity_score,
                "event_type": decision.signals.event_type_pass_rate,
                "intent": decision.signals.intent_pass_rate,
                "source": decision.signals.source_reliability
            },
            "similar_outputs": decision.signals.similar_outputs,
            "auto_approved": decision.should_auto_approve,
            "reason": decision.reason,
            "created_at": get_ist_now()
        })
        self.db.commit()

    def get_auto_approval_metrics(self, days: int = 7) -> Dict:
        """
        Get auto-approval performance metrics.

        Args:
            days: Number of days to look back

        Returns:
            Dict with metrics: auto_approval_rate, avg_confidence, false_positive_rate
        """
        since_date = get_ist_now() - timedelta(days=days)

        # Query auto_approval_history
        query = text("""
            SELECT
                COUNT(*) FILTER (WHERE auto_approved = TRUE) AS auto_approved_count,
                COUNT(*) AS total_count,
                AVG(confidence_score) FILTER (WHERE auto_approved = TRUE) AS avg_confidence
            FROM auto_approval_history
            WHERE created_at >= :since_date
        """)

        result = self.db.execute(query, {"since_date": since_date}).fetchone()

        auto_approved_count = result[0] if result else 0
        total_count = result[1] if result else 0
        avg_confidence = result[2] if result else 0

        auto_approval_rate = (auto_approved_count / total_count * 100) if total_count > 0 else 0

        # TODO: Calculate false positive rate
        # (requires tracking when auto-approved items are later flagged as problematic)
        false_positive_rate = 0.0

        return {
            "auto_approval_rate": round(auto_approval_rate, 2),
            "auto_approved_count": auto_approved_count,
            "manual_review_count": total_count - auto_approved_count,
            "total_count": total_count,
            "avg_confidence": round(avg_confidence, 2) if avg_confidence else 0,
            "false_positive_rate": false_positive_rate,
            "days": days
        }

    def batch_auto_evaluate(self, limit: int = 50) -> Dict:
        """
        Batch process all pending outputs for auto-evaluation.

        Args:
            limit: Maximum number of outputs to process

        Returns:
            Dict with counts: total_evaluated, auto_approved, manual_required
        """
        # Find outputs without evaluations
        query = text("""
            SELECT o.id
            FROM outputs o
            LEFT JOIN evaluations e ON e.output_id = o.id
            WHERE e.id IS NULL
            ORDER BY o.created_at DESC
            LIMIT :limit
        """)

        results = self.db.execute(query, {"limit": limit}).fetchall()
        output_ids = [row[0] for row in results]

        auto_approved = 0
        manual_required = 0

        for output_id in output_ids:
            evaluation = self.auto_approve_if_eligible(output_id)
            if evaluation:
                auto_approved += 1
            else:
                manual_required += 1

        return {
            "total_evaluated": len(output_ids),
            "auto_approved": auto_approved,
            "manual_required": manual_required
        }
