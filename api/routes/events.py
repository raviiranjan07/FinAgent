"""Event routes."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database.connection import get_db_session
from database.repository import RepositoryManager
from api.schemas.schemas import EventResponse, EventListResponse

router = APIRouter()


def get_repo():
    """Get repository manager with database session."""
    with get_db_session() as db:
        yield RepositoryManager(db)


@router.get("", response_model=EventListResponse)
async def list_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source: Optional[str] = None,
):
    """List events with pagination."""
    with get_db_session() as db:
        repo = RepositoryManager(db)

        # Get events
        if source:
            events = repo.events.get_by_source(source, limit=page_size * page)
        else:
            events = repo.events.get_recent(hours=720, limit=page_size * page)  # 30 days

        # Get total count
        total = repo.events.count()

        # Calculate pagination
        total_pages = (total + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_events = events[start_idx:end_idx]

        # Convert to response
        items = []
        for event in paginated_events:
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
