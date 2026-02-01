"""Output routes."""

from typing import Optional, Literal
from fastapi import APIRouter, HTTPException, Query
from uuid import UUID
from sqlalchemy import desc, asc
from sqlalchemy.orm import joinedload

from database.connection import get_db_session
from database.repository import RepositoryManager
from database.models import Output, Event, Evaluation
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
    intent: Optional[str] = None,
    pending_only: bool = False,
    hitl_only: bool = False,
    sort_order: Literal["asc", "desc"] = "desc",
):
    """
    List outputs with pagination.

    Args:
        pending_only: Only show outputs without evaluation
        hitl_only: Only show outputs requiring HITL review

    Performance: Uses joinedload to fetch related data in 1-2 queries
    instead of N+1 queries. Uses offset/limit for efficient pagination.
    """
    with get_db_session() as db:
        repo = RepositoryManager(db)

        # Determine sort order
        order_func = desc if sort_order == "desc" else asc

        # Base query with eager loading (prevents N+1 queries)
        base_query = (
            db.query(Output)
            .join(Event, Output.event_id == Event.id)
            .options(
                joinedload(Output.event),       # Eager load event
                joinedload(Output.evaluations)  # Eager load evaluations
            )
            .order_by(order_func(Event.published_at))
        )

        # Apply filters
        if pending_only:
            # Use outerjoin to find outputs without evaluations
            base_query = (
                db.query(Output)
                .join(Event, Output.event_id == Event.id)
                .outerjoin(Evaluation, Output.id == Evaluation.output_id)
                .filter(Evaluation.id.is_(None))  # No evaluation exists
                .options(
                    joinedload(Output.event),
                    joinedload(Output.evaluations)
                )
                .order_by(order_func(Event.published_at))
            )
        elif hitl_only:
            base_query = base_query.filter(Output.hitl_required == True)

        # Apply event_type filter if provided
        if event_type:
            base_query = base_query.filter(Output.event_type == event_type)

        # Apply intent filter if provided
        if intent:
            base_query = base_query.filter(Output.intent == intent)

        # Get total count for this filter
        total = base_query.count()

        # Apply pagination with offset/limit (efficient - only loads needed records)
        outputs = (
            base_query
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        # Calculate pagination info
        total_pages = (total + page_size - 1) // page_size

        # Convert to response (no additional queries - data already loaded)
        items = []
        for output in outputs:
            has_evaluation = len(output.evaluations) > 0 if output.evaluations else False
            evaluation_verdict = output.evaluations[0].verdict if has_evaluation else None

            # Calculate AI-human agreement
            ai_human_agreement = None
            if has_evaluation and output.suggested_verdict:
                ai_human_agreement = output.suggested_verdict == evaluation_verdict

            items.append(OutputResponse(
                id=str(output.id),
                event_id=str(output.event_id),
                llm_output=output.llm_output,
                event_type=output.event_type,
                intent=output.intent,
                clarity_issues=output.clarity_issues or [],
                hitl_required=output.hitl_required,
                hitl_risk_level=output.hitl_risk_level,
                llm_model=output.llm_model,
                created_at=output.created_at,
                event_title=output.event.title if output.event else None,
                event_source=output.event.source if output.event else None,
                event_published_at=output.event.published_at if output.event else None,
                has_evaluation=has_evaluation,
                evaluation_verdict=evaluation_verdict,
                suggested_verdict=output.suggested_verdict,
                suggested_verdict_reason=output.suggested_verdict_reason,
                ai_human_agreement=ai_human_agreement,
                generation_metadata=output.generation_metadata,
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

        # Calculate AI-human agreement
        ai_human_agreement = None
        agreement_details = None

        if has_evaluation and output.suggested_verdict and evaluation_response:
            ai_human_agreement = output.suggested_verdict == evaluation_response.verdict

            # Build full agreement comparison
            agreement_details = {
                "agreed": ai_human_agreement,
                "ai_verdict": output.suggested_verdict,
                "ai_reason": output.suggested_verdict_reason,
                "human_verdict": evaluation_response.verdict,
                "human_reason": evaluation_response.failure_reason,
            }

        return OutputDetailResponse(
            id=str(output.id),
            event_id=str(output.event_id),
            llm_output=output.llm_output,
            event_type=output.event_type,
            intent=output.intent,
            clarity_issues=output.clarity_issues or [],
            hitl_required=output.hitl_required,
            hitl_risk_level=output.hitl_risk_level,
            llm_model=output.llm_model,
            created_at=output.created_at,
            event_title=output.event.title if output.event else None,
            event_source=output.event.source if output.event else None,
            event_published_at=output.event.published_at if output.event else None,
            has_evaluation=has_evaluation,
            evaluation_verdict=evaluation_response.verdict if evaluation_response else None,
            suggested_verdict=output.suggested_verdict,
            suggested_verdict_reason=output.suggested_verdict_reason,
            ai_human_agreement=ai_human_agreement,
            generation_metadata=output.generation_metadata,
            event=event_response,
            evaluation=evaluation_response,
            agreement_details=agreement_details,
        )


@router.get("/event-types/list")
async def list_event_types():
    """Get all event types with counts."""
    with get_db_session() as db:
        repo = RepositoryManager(db)
        counts = repo.outputs.count_by_event_type()
        return {"event_types": counts}


@router.get("/intents/list")
async def list_intents():
    """Get all intents with counts."""
    with get_db_session() as db:
        repo = RepositoryManager(db)
        counts = repo.outputs.count_by_intent()
        return {"intents": counts}
