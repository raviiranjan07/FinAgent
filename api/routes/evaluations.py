"""Evaluation routes."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from uuid import UUID

from database.connection import get_db_session
from database.repository import RepositoryManager
from api.schemas.schemas import (
    EvaluationCreate,
    EvaluationResponse,
    EvaluationListResponse,
)
from api.websocket import manager

router = APIRouter()

# Valid values for dropdowns
VALID_EVENT_TYPES = [
    "DIGITAL_ASSETS", "FINANCE_POLICY", "GEO_FINANCIAL",
    "MACRO_ECONOMIC", "MARKET_INFRASTRUCTURE", "MARKET_MOVEMENT",
    "NON_FINANCE", "SKIP"
]

VALID_INTENTS = ["EXPLANATORY", "DESCRIPTIVE", "MARKET_OPINION"]


@router.post("", response_model=EvaluationResponse)
async def create_evaluation(evaluation: EvaluationCreate):
    """
    Create a new evaluation for an output.

    This is the core HITL endpoint - marking content as PASS or FAIL.
    """
    with get_db_session() as db:
        repo = RepositoryManager(db)

        # Validate output exists
        try:
            output = repo.outputs.get_by_id(UUID(evaluation.output_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid output ID format")

        if not output:
            raise HTTPException(status_code=404, detail="Output not found")

        # Check if already evaluated
        existing = repo.evaluations.get_by_output_id(UUID(evaluation.output_id))
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Output already evaluated. Use PUT to update."
            )

        # Validate verdict (supports 3 verdicts: PASS, FAIL, ACCEPT)
        if evaluation.verdict not in ["PASS", "FAIL", "ACCEPT"]:
            raise HTTPException(
                status_code=400,
                detail="Verdict must be 'PASS', 'FAIL', or 'ACCEPT'"
            )

        # FAIL and ACCEPT require corrected_event_type and corrected_intent for training data
        if evaluation.verdict in ["FAIL", "ACCEPT"]:
            if not evaluation.corrected_event_type:
                raise HTTPException(
                    status_code=400,
                    detail="corrected_event_type is required for FAIL/ACCEPT verdicts"
                )
            if not evaluation.corrected_intent:
                raise HTTPException(
                    status_code=400,
                    detail="corrected_intent is required for FAIL/ACCEPT verdicts"
                )

            # Validate dropdown values
            if evaluation.corrected_event_type not in VALID_EVENT_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid event type: {evaluation.corrected_event_type}. Must be one of {VALID_EVENT_TYPES}"
                )
            if evaluation.corrected_intent not in VALID_INTENTS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid intent: {evaluation.corrected_intent}. Must be one of {VALID_INTENTS}"
                )

        # Create evaluation
        eval_data = {
            "event_id": output.event_id,
            "output_id": UUID(evaluation.output_id),
            "verdict": evaluation.verdict,
            "failure_reason": evaluation.failure_reason,
            "corrected_event_type": evaluation.corrected_event_type,
            "corrected_intent": evaluation.corrected_intent,
            "comment": evaluation.comment,
            "evaluator": evaluation.evaluator or "default",
        }

        new_eval = repo.evaluations.create(eval_data)
        repo.commit()

        # Notify via WebSocket
        await manager.notify_evaluation(
            str(new_eval.id),
            str(new_eval.output_id),
            new_eval.verdict
        )

        return EvaluationResponse(
            id=str(new_eval.id),
            event_id=str(new_eval.event_id),
            output_id=str(new_eval.output_id),
            verdict=new_eval.verdict,
            failure_reason=new_eval.failure_reason,
            corrected_event_type=new_eval.corrected_event_type,
            corrected_intent=new_eval.corrected_intent,
            comment=new_eval.comment,
            evaluator=new_eval.evaluator,
            evaluated_at=new_eval.evaluated_at,
        )


@router.get("", response_model=EvaluationListResponse)
async def list_evaluations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    verdict: Optional[str] = None,
):
    """List evaluations with pagination."""
    with get_db_session() as db:
        repo = RepositoryManager(db)

        # Get evaluations
        if verdict:
            if verdict not in ["PASS", "FAIL", "ACCEPT"]:
                raise HTTPException(
                    status_code=400,
                    detail="verdict must be 'PASS', 'FAIL', or 'ACCEPT'"
                )
            evaluations = repo.evaluations.get_by_verdict(verdict, limit=page_size * page)
        else:
            evaluations = repo.evaluations.get_recent(limit=page_size * page)

        # Get total count
        stats = repo.evaluations.get_stats()
        total = stats["total"]

        # Calculate pagination
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_evals = evaluations[start_idx:end_idx]

        # Convert to response
        items = [
            EvaluationResponse(
                id=str(e.id),
                event_id=str(e.event_id),
                output_id=str(e.output_id),
                verdict=e.verdict,
                failure_reason=e.failure_reason,
                corrected_event_type=e.corrected_event_type,
                corrected_intent=e.corrected_intent,
                comment=e.comment,
                evaluator=e.evaluator,
                evaluated_at=e.evaluated_at,
            )
            for e in paginated_evals
        ]

        return EvaluationListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


@router.get("/{evaluation_id}", response_model=EvaluationResponse)
async def get_evaluation(evaluation_id: str):
    """Get a single evaluation by ID."""
    with get_db_session() as db:
        repo = RepositoryManager(db)

        try:
            evaluation = repo.evaluations.get_by_id(UUID(evaluation_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid evaluation ID format")

        if not evaluation:
            raise HTTPException(status_code=404, detail="Evaluation not found")

        return EvaluationResponse(
            id=str(evaluation.id),
            event_id=str(evaluation.event_id),
            output_id=str(evaluation.output_id),
            verdict=evaluation.verdict,
            failure_reason=evaluation.failure_reason,
            corrected_event_type=evaluation.corrected_event_type,
            corrected_intent=evaluation.corrected_intent,
            comment=evaluation.comment,
            evaluator=evaluation.evaluator,
            evaluated_at=evaluation.evaluated_at,
        )


@router.put("/{evaluation_id}", response_model=EvaluationResponse)
async def update_evaluation(evaluation_id: str, evaluation: EvaluationCreate):
    """Update an existing evaluation."""
    with get_db_session() as db:
        repo = RepositoryManager(db)

        try:
            existing = repo.evaluations.get_by_id(UUID(evaluation_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid evaluation ID format")

        if not existing:
            raise HTTPException(status_code=404, detail="Evaluation not found")

        # Validate verdict (supports 3 verdicts: PASS, FAIL, ACCEPT)
        if evaluation.verdict not in ["PASS", "FAIL", "ACCEPT"]:
            raise HTTPException(
                status_code=400,
                detail="Verdict must be 'PASS', 'FAIL', or 'ACCEPT'"
            )

        # FAIL and ACCEPT require corrected_event_type and corrected_intent for training data
        if evaluation.verdict in ["FAIL", "ACCEPT"]:
            if not evaluation.corrected_event_type:
                raise HTTPException(
                    status_code=400,
                    detail="corrected_event_type is required for FAIL/ACCEPT verdicts"
                )
            if not evaluation.corrected_intent:
                raise HTTPException(
                    status_code=400,
                    detail="corrected_intent is required for FAIL/ACCEPT verdicts"
                )

            # Validate dropdown values
            if evaluation.corrected_event_type not in VALID_EVENT_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid event type: {evaluation.corrected_event_type}. Must be one of {VALID_EVENT_TYPES}"
                )
            if evaluation.corrected_intent not in VALID_INTENTS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid intent: {evaluation.corrected_intent}. Must be one of {VALID_INTENTS}"
                )

        # Update evaluation
        update_data = {
            "verdict": evaluation.verdict,
            "failure_reason": evaluation.failure_reason,
            "corrected_event_type": evaluation.corrected_event_type,
            "corrected_intent": evaluation.corrected_intent,
            "comment": evaluation.comment,
            "evaluator": evaluation.evaluator or existing.evaluator,
        }

        updated = repo.evaluations.update(UUID(evaluation_id), update_data)
        repo.commit()

        # Notify via WebSocket
        await manager.notify_evaluation(
            str(updated.id),
            str(updated.output_id),
            updated.verdict
        )

        return EvaluationResponse(
            id=str(updated.id),
            event_id=str(updated.event_id),
            output_id=str(updated.output_id),
            verdict=updated.verdict,
            failure_reason=updated.failure_reason,
            corrected_event_type=updated.corrected_event_type,
            corrected_intent=updated.corrected_intent,
            comment=updated.comment,
            evaluator=updated.evaluator,
            evaluated_at=updated.evaluated_at,
        )


@router.delete("/{evaluation_id}")
async def delete_evaluation(evaluation_id: str):
    """Delete an evaluation."""
    with get_db_session() as db:
        repo = RepositoryManager(db)

        try:
            deleted = repo.evaluations.delete(UUID(evaluation_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid evaluation ID format")

        if not deleted:
            raise HTTPException(status_code=404, detail="Evaluation not found")

        repo.commit()
        return {"status": "deleted", "id": evaluation_id}
