"""Event routes."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, asc

from database.connection import get_db_session
from database.repository import RepositoryManager
from database.models import Event as DBEvent, Output, Evaluation
from api.schemas.schemas import EventResponse, EventListResponse

router = APIRouter()

# Whitelist of allowed sort fields (security: prevents arbitrary attribute access)
ALLOWED_SORT_FIELDS = {"published_at", "created_at", "source", "title"}


def get_repo():
    """Get repository manager with database session."""
    with get_db_session() as db:
        yield RepositoryManager(db)


@router.get("", response_model=EventListResponse)
async def list_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source: Optional[str] = None,
    sort_by: str = Query("published_at", description="Sort by field (published_at, created_at)"),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
):
    """
    List events with pagination and sorting.

    Performance: Uses joinedload to fetch related data in 1-2 queries
    instead of N+1 queries.
    """
    with get_db_session() as db:
        # Build query with eager loading (prevents N+1 queries)
        query = (
            db.query(DBEvent)
            .options(
                joinedload(DBEvent.outputs).joinedload(Output.evaluations)
            )
        )

        # Apply source filter
        if source:
            query = query.filter(DBEvent.source == source)

        # Apply sorting (with whitelist validation)
        if sort_by not in ALLOWED_SORT_FIELDS:
            sort_by = "published_at"
        sort_field = getattr(DBEvent, sort_by, DBEvent.published_at)
        if sort_order == "desc":
            query = query.order_by(desc(sort_field))
        else:
            query = query.order_by(asc(sort_field))

        # Get total count (without eager loading for performance)
        total = db.query(DBEvent).filter(DBEvent.source == source if source else True).count()

        # Apply pagination
        events = query.offset((page - 1) * page_size).limit(page_size).all()

        # Calculate pagination metadata
        total_pages = (total + page_size - 1) // page_size

        # Convert to response (no additional queries - data already loaded)
        items = []
        for event in events:
            has_output = len(event.outputs) > 0 if event.outputs else False
            has_evaluation = any(
                len(o.evaluations) > 0 for o in event.outputs
            ) if event.outputs else False

            items.append(EventResponse(
                id=str(event.id),
                event_id=event.event_id,
                title=event.title,
                summary=event.summary,
                link=event.link,
                source=event.source,
                published_at=event.published_at,
                created_at=event.created_at,
                has_output=has_output,
                has_evaluation=has_evaluation,
            ))

        return EventListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: str):
    """Get a single event by ID."""
    with get_db_session() as db:
        repo = RepositoryManager(db)

        # Try UUID first, then event_id
        event = repo.events.get_by_event_id(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        has_output = len(event.outputs) > 0 if event.outputs else False
        has_evaluation = any(
            len(o.evaluations) > 0 for o in event.outputs
        ) if event.outputs else False

        return EventResponse(
            id=str(event.id),
            event_id=event.event_id,
            title=event.title,
            summary=event.summary,
            link=event.link,
            source=event.source,
            published_at=event.published_at,
            created_at=event.created_at,
            has_output=has_output,
            has_evaluation=has_evaluation,
        )


@router.get("/sources/list")
async def list_sources():
    """Get all unique sources with counts."""
    with get_db_session() as db:
        repo = RepositoryManager(db)
        counts = repo.events.count_by_source()
        return {"sources": counts}


@router.delete("/{event_id}")
async def delete_event(event_id: str):
    """
    Permanently delete an event and all related data.

    WARNING: This cascades to outputs, evaluations, and content_queue.
    All generated content for this event will be deleted.
    """
    from uuid import UUID
    from database.models import Event as DBEvent

    with get_db_session() as db:
        try:
            # Get event from database
            event_uuid = UUID(event_id)
            db_event = db.query(DBEvent).filter(DBEvent.id == event_uuid).first()

            if not db_event:
                raise HTTPException(status_code=404, detail=f"Event {event_id} not found")

            event_title = db_event.title

            # Delete event (cascades to outputs, evaluations, content_queue)
            db.delete(db_event)
            db.commit()

            return {
                "success": True,
                "message": f"Event '{event_title}' deleted successfully",
                "event_id": event_id
            }

        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid event ID format")
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete event: {str(e)}"
            )


@router.post("/{event_id}/regenerate")
async def regenerate_output(event_id: str):
    """
    Regenerate LLM output for an event (useful after deleting previous output).

    Runs the event through the adapter pipeline (skipping embedding/dedup).
    """
    from uuid import UUID
    from database.models import Event as DBEvent
    from models.event import Event as PipelineEvent
    from adapters.context import ExecutionContext
    from adapters.event_type import EventTypeAdapter
    from adapters.intent import IntentAdapter
    from adapters.output import OutputAdapter
    from adapters.clarity import ClarityAdapter
    from adapters.hitl import HITLDecisionAdapter
    from adapters.database import DatabaseAdapter

    with get_db_session() as db:
        try:
            # Get event from database
            event_uuid = UUID(event_id)
            db_event = db.query(DBEvent).filter(DBEvent.id == event_uuid).first()

            if not db_event:
                raise HTTPException(status_code=404, detail=f"Event {event_id} not found")

            # Convert to pipeline Event model
            pipeline_event = PipelineEvent(
                event_id=db_event.event_id,
                source=db_event.source,
                title=db_event.title,
                summary=db_event.summary or "",
                url=db_event.link or "",
                country="",  # Not stored in DB
                published_at=db_event.published_at.isoformat() if db_event.published_at else "",
            )

            # Build pipeline (skip embedding/dedup for regeneration)
            pipeline = [
                EventTypeAdapter(),
                IntentAdapter(),
                OutputAdapter(),
                ClarityAdapter(),
                HITLDecisionAdapter(),
                DatabaseAdapter(),  # Saves to database
            ]

            # Run through pipeline
            context = ExecutionContext(event=pipeline_event)
            for adapter in pipeline:
                context = adapter.run(context)

                # Skip if event type is SKIP
                if context.event_type == "SKIP":
                    return {
                        "success": False,
                        "message": "Event type is SKIP - not suitable for content generation",
                        "event_type": "SKIP"
                    }

            return {
                "success": True,
                "message": "Output regenerated successfully",
                "output_id": str(context.output_id) if hasattr(context, 'output_id') else None,
                "event_type": context.event_type,
                "intent": context.intent,
                "hitl_required": context.hitl_required,
            }

        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid event ID format")
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to regenerate output: {str(e)}"
            )
