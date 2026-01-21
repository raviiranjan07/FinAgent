"""Output routes."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from uuid import UUID

from database.connection import get_db_session
from database.repository import RepositoryManager
from api.schemas.schemas import (
    OutputResponse,
    OutputListResponse,
    OutputDetailResponse,
    EventResponse,
    EvaluationResponse,
)

router = APIRouter()


@router.get("", response_model=OutputListResponse)
async def list_outputs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    event_type: Optional[str] = None,
    pending_only: bool = False,
    hitl_only: bool = False,
):
    """
    List outputs with pagination.

    Args:
        pending_only: Only show outputs without evaluation
        hitl_only: Only show outputs requiring HITL review
    """
    with get_db_session() as db:
        repo = RepositoryManager(db)

        # Get outputs based on filters
        if pending_only:
            outputs = repo.outputs.get_unevaluated(limit=page_size * page)
        elif hitl_only:
            outputs = repo.outputs.get_pending_review(limit=page_size * page)
        elif event_type:
            outputs = repo.outputs.get_by_event_type(event_type, limit=page_size * page)
        else:
            # Get all recent outputs
            from sqlalchemy import desc
            from database.models import Output
            outputs = (
                db.query(Output)
                .order_by(desc(Output.created_at))
                .limit(page_size * page)
                .all()
            )

        # Get total count
        total = repo.outputs.count()

        # Calculate pagination
        total_pages = (total + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_outputs = outputs[start_idx:end_idx]

        # Convert to response
        items = []
        for output in paginated_outputs:
            has_evaluation = len(output.evaluations) > 0 if output.evaluations else False
            evaluation_verdict = output.evaluations[0].verdict if has_evaluation else None

            items.append(OutputResponse(
                id=str(output.id),
                event_id=str(output.event_id),
                llm_output=output.llm_output,
                event_type=output.event_type,
                intent=output.intent,
                clarity_issues=output.clarity_issues or [],
                hitl_required=output.hitl_required,
                hitl_risk_level=output.hitl_risk_level,
                created_at=output.created_at,
                event_title=output.event.title if output.event else None,
                event_source=output.event.source if output.event else None,
                event_published_at=output.event.published_at if output.event else None,
                has_evaluation=has_evaluation,
                evaluation_verdict=evaluation_verdict,
            ))

        return OutputListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


@router.get("/{output_id}", response_model=OutputDetailResponse)
async def get_output(output_id: str):
    """Get a single output with full details."""
    with get_db_session() as db:
        repo = RepositoryManager(db)

        try:
            output = repo.outputs.get_by_id(UUID(output_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid output ID format")

        if not output:
            raise HTTPException(status_code=404, detail="Output not found")

        # Build event response
        event_response = None
        if output.event:
            event_response = EventResponse(
                id=str(output.event.id),
                event_id=output.event.event_id,
                title=output.event.title,
                summary=output.event.summary,
                link=output.event.link,
                source=output.event.source,
                published_at=output.event.published_at,
                created_at=output.event.created_at,
                has_output=True,
                has_evaluation=len(output.evaluations) > 0 if output.evaluations else False,
            )

        # Build evaluation response
        evaluation_response = None
        if output.evaluations and len(output.evaluations) > 0:
            eval_obj = output.evaluations[0]
            evaluation_response = EvaluationResponse(
                id=str(eval_obj.id),
                event_id=str(eval_obj.event_id),
                output_id=str(eval_obj.output_id),
                verdict=eval_obj.verdict,
                failure_reason=eval_obj.failure_reason,
                comment=eval_obj.comment,
                evaluator=eval_obj.evaluator,
                evaluated_at=eval_obj.evaluated_at,
            )

        has_evaluation = evaluation_response is not None

        return OutputDetailResponse(
            id=str(output.id),
            event_id=str(output.event_id),
            llm_output=output.llm_output,
            event_type=output.event_type,
            intent=output.intent,
            clarity_issues=output.clarity_issues or [],
            hitl_required=output.hitl_required,
            hitl_risk_level=output.hitl_risk_level,
            created_at=output.created_at,
            event_title=output.event.title if output.event else None,
            event_source=output.event.source if output.event else None,
            has_evaluation=has_evaluation,
            evaluation_verdict=evaluation_response.verdict if evaluation_response else None,
            event=event_response,
            evaluation=evaluation_response,
        )


@router.get("/event-types/list")
async def list_event_types():
    """Get all event types with counts."""
    with get_db_session() as db:
        repo = RepositoryManager(db)
        counts = repo.outputs.count_by_event_type()
        return {"event_types": counts}
