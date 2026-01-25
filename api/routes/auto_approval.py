"""Auto-Approval API endpoints for HITL workflow automation."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime
from uuid import UUID

from database.connection import get_db_session
from database.models import Output, Evaluation, Event
from services.auto_approval_service import AutoApprovalService
from api.websocket import manager

router = APIRouter()


# Request/Response Models
class AutoEvaluateResponse(BaseModel):
    """Response for auto-evaluation."""
    output_id: str
    auto_approved: bool
    confidence_score: float
    reason: str
    signals: Dict
    evaluation_id: Optional[str] = None


class BatchAutoEvaluateResponse(BaseModel):
    """Response for batch auto-evaluation."""
    total_evaluated: int
    auto_approved: int
    manual_required: int
    success: bool


class AutoApprovalMetricsResponse(BaseModel):
    """Response for auto-approval metrics."""
    auto_approval_rate: float
    auto_approved_count: int
    manual_review_count: int
    total_count: int
    avg_confidence: float
    false_positive_rate: float
    days: int


@router.post("/auto-evaluate/{output_id}", response_model=AutoEvaluateResponse)
async def auto_evaluate_output(output_id: str):
    """
    Trigger auto-evaluation for a specific output.

    This endpoint:
    1. Calculates confidence score from multiple signals
    2. Determines if output meets auto-approval criteria
    3. Creates evaluation if auto-approved
    4. Returns decision with detailed breakdown

    Args:
        output_id: UUID of output to evaluate

    Returns:
        AutoEvaluateResponse with decision and signals
    """
    with get_db_session() as db:
        try:
            # Parse UUID
            output_uuid = UUID(output_id)

            # Check if output exists
            output = db.query(Output).filter(Output.id == output_uuid).first()
            if not output:
                raise HTTPException(404, f"Output {output_id} not found")

            # Check if already evaluated
            existing = db.query(Evaluation).filter(Evaluation.output_id == output_uuid).first()
            if existing:
                raise HTTPException(
                    400,
                    f"Output already evaluated with verdict {existing.verdict}"
                )

            # Create auto-approval service
            service = AutoApprovalService(db)

            # Calculate confidence (this also creates evaluation if eligible)
            evaluation = service.auto_approve_if_eligible(output_uuid)

            # Get the decision for response
            decision = service.calculate_confidence(output)

            # Prepare response
            response = AutoEvaluateResponse(
                output_id=output_id,
                auto_approved=decision.should_auto_approve,
                confidence_score=decision.confidence_score,
                reason=decision.reason,
                signals={
                    "clarity": decision.signals.clarity_score,
                    "similarity": decision.signals.similarity_score,
                    "event_type": decision.signals.event_type_pass_rate,
                    "intent": decision.signals.intent_pass_rate,
                    "source": decision.signals.source_reliability,
                    "similar_outputs_count": decision.signals.similar_outputs_count,
                    "similar_outputs": decision.signals.similar_outputs[:5]  # First 5 for brevity
                },
                evaluation_id=str(evaluation.id) if evaluation else None
            )

            # Notify via WebSocket
            await manager.broadcast({
                "type": "AUTO_APPROVAL_UPDATE",
                "data": {
                    "output_id": output_id,
                    "auto_approved": decision.should_auto_approve,
                    "confidence_score": decision.confidence_score
                }
            })

            return response

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"Failed to auto-evaluate: {str(e)}")


@router.get("/stats", response_model=AutoApprovalMetricsResponse)
async def get_auto_approval_stats(days: int = 7):
    """
    Get auto-approval performance metrics for monitoring.

    Args:
        days: Number of days to look back (default: 7)

    Returns:
        AutoApprovalMetricsResponse with key metrics
    """
    with get_db_session() as db:
        try:
            service = AutoApprovalService(db)
            metrics = service.get_auto_approval_metrics(days)

            return AutoApprovalMetricsResponse(**metrics)

        except Exception as e:
            raise HTTPException(500, f"Failed to get metrics: {str(e)}")


@router.post("/batch-auto-evaluate", response_model=BatchAutoEvaluateResponse)
async def batch_auto_evaluate(limit: int = 50):
    """
    Batch process all pending outputs for auto-evaluation.

    This is useful for:
    - Backfilling auto-evaluation for existing outputs
    - Periodic batch processing
    - Testing auto-approval system

    Args:
        limit: Maximum number of outputs to process (default: 50, max: 100)

    Returns:
        BatchAutoEvaluateResponse with counts
    """
    # Validate limit
    if limit > 100:
        raise HTTPException(400, "Limit cannot exceed 100")

    with get_db_session() as db:
        try:
            service = AutoApprovalService(db)
            result = service.batch_auto_evaluate(limit)

            # Notify via WebSocket
            await manager.broadcast({
                "type": "AUTO_APPROVAL_BATCH_UPDATE",
                "data": result
            })

            return BatchAutoEvaluateResponse(
                success=True,
                **result
            )

        except Exception as e:
            raise HTTPException(500, f"Failed to batch evaluate: {str(e)}")


@router.post("/refresh-cache")
async def refresh_confidence_cache():
    """
    Refresh confidence_stats_cache table with latest pass rates.

    This endpoint:
    1. Recalculates pass rates for all event_type, intent, source combinations
    2. Updates the cache table
    3. Returns count of cache entries updated

    Useful for:
    - Weekly maintenance
    - After significant data changes
    - Testing
    """
    with get_db_session() as db:
        try:
            from sqlalchemy import text

            # Clear existing cache
            db.execute(text("DELETE FROM confidence_stats_cache"))
            db.commit()

            # Recalculate event_type pass rates
            event_type_query = text("""
                INSERT INTO confidence_stats_cache (stat_type, stat_key, pass_rate, total_count, pass_count, last_updated)
                SELECT
                    'event_type' AS stat_type,
                    o.event_type AS stat_key,
                    (COUNT(*) FILTER (WHERE e.verdict = 'PASS') * 100.0 / COUNT(*)) AS pass_rate,
                    COUNT(*) AS total_count,
                    COUNT(*) FILTER (WHERE e.verdict = 'PASS') AS pass_count,
                    :now AS last_updated
                FROM evaluations e
                INNER JOIN outputs o ON o.id = e.output_id
                WHERE o.event_type IS NOT NULL
                GROUP BY o.event_type
            """)

            db.execute(event_type_query, {"now": datetime.utcnow()})

            # Recalculate intent pass rates
            intent_query = text("""
                INSERT INTO confidence_stats_cache (stat_type, stat_key, pass_rate, total_count, pass_count, last_updated)
                SELECT
                    'intent' AS stat_type,
                    o.intent AS stat_key,
                    (COUNT(*) FILTER (WHERE e.verdict = 'PASS') * 100.0 / COUNT(*)) AS pass_rate,
                    COUNT(*) AS total_count,
                    COUNT(*) FILTER (WHERE e.verdict = 'PASS') AS pass_count,
                    :now AS last_updated
                FROM evaluations e
                INNER JOIN outputs o ON o.id = e.output_id
                WHERE o.intent IS NOT NULL
                GROUP BY o.intent
            """)

            db.execute(intent_query, {"now": datetime.utcnow()})

            # Recalculate source pass rates
            source_query = text("""
                INSERT INTO confidence_stats_cache (stat_type, stat_key, pass_rate, total_count, pass_count, last_updated)
                SELECT
                    'source' AS stat_type,
                    ev.source AS stat_key,
                    (COUNT(*) FILTER (WHERE e.verdict = 'PASS') * 100.0 / COUNT(*)) AS pass_rate,
                    COUNT(*) AS total_count,
                    COUNT(*) FILTER (WHERE e.verdict = 'PASS') AS pass_count,
                    :now AS last_updated
                FROM evaluations e
                INNER JOIN outputs o ON o.id = e.output_id
                INNER JOIN events ev ON ev.id = o.event_id
                WHERE ev.source IS NOT NULL
                GROUP BY ev.source
            """)

            db.execute(source_query, {"now": datetime.utcnow()})

            db.commit()

            # Count cache entries
            count_result = db.execute(text("SELECT COUNT(*) FROM confidence_stats_cache")).fetchone()
            cache_count = count_result[0] if count_result else 0

            return {
                "success": True,
                "message": "Confidence cache refreshed successfully",
                "cache_entries": cache_count,
                "refreshed_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            db.rollback()
            raise HTTPException(500, f"Failed to refresh cache: {str(e)}")


@router.get("/confidence-breakdown/{output_id}")
async def get_confidence_breakdown(output_id: str):
    """
    Get detailed confidence breakdown for a specific output.

    This is useful for:
    - Debugging auto-approval decisions
    - Understanding why output was/wasn't auto-approved
    - Transparency for users

    Args:
        output_id: UUID of output

    Returns:
        Detailed breakdown of all confidence signals
    """
    with get_db_session() as db:
        try:
            output_uuid = UUID(output_id)

            # Check if output exists
            output = db.query(Output).filter(Output.id == output_uuid).first()
            if not output:
                raise HTTPException(404, f"Output {output_id} not found")

            # Calculate confidence
            service = AutoApprovalService(db)
            decision = service.calculate_confidence(output)

            # Get event for context
            event = db.query(Event).filter(Event.id == output.event_id).first()

            return {
                "output_id": output_id,
                "event_type": output.event_type,
                "intent": output.intent,
                "source": event.source if event else None,
                "suggested_verdict": output.suggested_verdict,
                "hitl_risk_level": output.hitl_risk_level,
                "confidence_score": decision.confidence_score,
                "should_auto_approve": decision.should_auto_approve,
                "reason": decision.reason,
                "signals": {
                    "clarity": {
                        "score": decision.signals.clarity_score,
                        "weight": AutoApprovalService.WEIGHT_CLARITY,
                        "contribution": decision.signals.clarity_score * AutoApprovalService.WEIGHT_CLARITY / 100,
                        "num_issues": len(output.clarity_issues) if output.clarity_issues else 0
                    },
                    "similarity": {
                        "score": decision.signals.similarity_score,
                        "weight": AutoApprovalService.WEIGHT_SIMILARITY,
                        "contribution": decision.signals.similarity_score * AutoApprovalService.WEIGHT_SIMILARITY / 100,
                        "similar_outputs_count": decision.signals.similar_outputs_count,
                        "similar_outputs": decision.signals.similar_outputs[:10]  # First 10
                    },
                    "event_type": {
                        "score": decision.signals.event_type_pass_rate,
                        "weight": AutoApprovalService.WEIGHT_EVENT_TYPE,
                        "contribution": decision.signals.event_type_pass_rate * AutoApprovalService.WEIGHT_EVENT_TYPE / 100
                    },
                    "intent": {
                        "score": decision.signals.intent_pass_rate,
                        "weight": AutoApprovalService.WEIGHT_INTENT,
                        "contribution": decision.signals.intent_pass_rate * AutoApprovalService.WEIGHT_INTENT / 100
                    },
                    "source": {
                        "score": decision.signals.source_reliability,
                        "weight": AutoApprovalService.WEIGHT_SOURCE,
                        "contribution": decision.signals.source_reliability * AutoApprovalService.WEIGHT_SOURCE / 100
                    }
                },
                "thresholds": {
                    "confidence_threshold": AutoApprovalService.CONFIDENCE_THRESHOLD,
                    "similarity_threshold": AutoApprovalService.SIMILARITY_THRESHOLD,
                    "min_similar_pass": AutoApprovalService.MIN_SIMILAR_PASS
                }
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"Failed to get breakdown: {str(e)}")
