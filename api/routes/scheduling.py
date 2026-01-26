"""Scheduling API endpoints for smart tweet scheduling."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from database.connection import get_db_session
from database.models import ContentQueue, GeneratedContent
from services.smart_scheduler import SmartScheduler
from api.websocket import manager
from utils.timezone import get_ist_now

router = APIRouter()

# Timezone conversion helper
IST = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")


def to_ist_isoformat(dt: Optional[datetime]) -> Optional[str]:
    """
    Format database datetime (naive IST) to IST ISO format string.

    Args:
        dt: Datetime from database (naive IST timestamp)

    Returns:
        ISO format string with IST timezone (e.g., "2026-01-25T15:28:34+05:30")
        or None if input is None
    """
    if dt is None:
        return None

    # Database stores naive IST timestamps - just add IST timezone info for display
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)

    # Return ISO format (includes +05:30 suffix)
    return dt.isoformat()


# Request/Response Models
class ScheduleItemsRequest(BaseModel):
    """Request to schedule multiple items."""
    content_queue_ids: List[str]
    start_date: Optional[str] = None  # ISO format, defaults to tomorrow
    days: int = 7  # Spread across how many days


class ScheduleSingleRequest(BaseModel):
    """Request to schedule a single item."""
    content_queue_id: str
    scheduled_for: str  # ISO format datetime


class RescheduleRequest(BaseModel):
    """Request to reschedule an item."""
    new_time: str  # ISO format datetime


class ScheduledItem(BaseModel):
    """Response model for a scheduled item."""
    content_queue_id: str
    scheduled_for: str
    content_text: str
    event_title: str
    event_type: str
    status: str
    randomization_applied: Optional[Dict] = None  # {base_time, jitter_minutes, gap_from_previous_hours}


class CalendarResponse(BaseModel):
    """Response for calendar view."""
    items: List[ScheduledItem]
    total: int
    date_range: dict


class SuggestedTimeResponse(BaseModel):
    """Response for optimal time suggestion."""
    suggested_time: str
    window: str
    reason: str
    note: str


@router.post("/schedule-smart")
async def schedule_items_smart(request: ScheduleItemsRequest):
    """
    Schedule items using smart scheduler with anti-bot randomization.

    This endpoint:
    1. Takes a list of content_queue items
    2. Distributes them across multiple days (default 7)
    3. Applies time randomization, gap randomization, and human-like patterns
    4. Updates each item with scheduled_for time
    """
    with get_db_session() as db:
        try:
            # Parse start date if provided
            start_date = None
            if request.start_date:
                start_date = datetime.fromisoformat(request.start_date)

            # Get content queue items
            items = []
            for queue_id_str in request.content_queue_ids:
                queue_id = UUID(queue_id_str)
                queue_item = db.query(ContentQueue).filter(ContentQueue.id == queue_id).first()

                if not queue_item:
                    raise HTTPException(404, f"Content queue item {queue_id_str} not found")

                if queue_item.status != "ready_to_schedule":
                    raise HTTPException(
                        400,
                        f"Item {queue_id_str} is not ready to schedule (status: {queue_item.status})"
                    )

                # Get generated content for preview
                generated = (
                    db.query(GeneratedContent)
                    .filter(GeneratedContent.content_queue_id == queue_id)
                    .first()
                )

                items.append({
                    "id": str(queue_item.id),
                    "content_queue_id": str(queue_item.id),
                    "content_text": generated.content_text if generated else "",
                })

            # Use smart scheduler with database session for incremental scheduling
            scheduler = SmartScheduler()
            scheduled = scheduler.schedule_items(items, start_date, request.days, db=db)

            # Update database
            results = []
            days_used = set()
            for item in scheduled:
                queue_id = UUID(item["content_queue_id"])
                queue_item = db.query(ContentQueue).filter(ContentQueue.id == queue_id).first()

                # Store as naive IST (strip timezone info - database stores naive IST)
                scheduled_time_ist = item["scheduled_for"]
                scheduled_time_naive = scheduled_time_ist.replace(tzinfo=None)

                queue_item.scheduled_for = scheduled_time_naive
                queue_item.status = "scheduled"
                db.commit()

                # Track which days were used
                days_used.add(item["scheduled_for"].date())

                results.append({
                    "content_queue_id": str(queue_id),
                    "scheduled_for": item["scheduled_for"].isoformat(),  # Already IST from scheduler
                    "content_preview": item["content_preview"],
                })

            # Notify via WebSocket
            await manager.broadcast({
                "type": "SCHEDULE_UPDATE",
                "data": {
                    "action": "scheduled",
                    "count": len(results)
                }
            })

            return {
                "success": True,
                "scheduled_count": len(results),
                "days_used": len(days_used),
                "message": f"Scheduled {len(results)} items across {len(days_used)} days with smart randomization",
                "scheduled_items": results,
                "note": "Times randomized with ±15-30 min jitter and 1.5-3.5 hour gaps for human-like posting"
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"Failed to schedule items: {str(e)}")


@router.post("/schedule-manual")
async def schedule_item_manual(request: ScheduleSingleRequest):
    """
    Manually schedule a single item at a specific time (user override).

    Use this when you want exact control over posting time.
    """
    with get_db_session() as db:
        try:
            queue_id = UUID(request.content_queue_id)
            queue_item = db.query(ContentQueue).filter(ContentQueue.id == queue_id).first()

            if not queue_item:
                raise HTTPException(404, "Content queue item not found")

            if queue_item.status not in ["ready_to_schedule", "scheduled"]:
                raise HTTPException(
                    400,
                    f"Item cannot be scheduled (status: {queue_item.status})"
                )

            # Parse scheduled time (user sends IST datetime)
            scheduled_for = datetime.fromisoformat(request.scheduled_for)

            # Validate not in the past
            if scheduled_for < datetime.now(IST):
                raise HTTPException(400, "Cannot schedule in the past")

            # Store as naive IST (strip timezone info - database stores naive IST)
            scheduled_for_naive = scheduled_for.replace(tzinfo=None)

            # Update database
            queue_item.scheduled_for = scheduled_for_naive
            queue_item.status = "scheduled"
            db.commit()

            # Notify via WebSocket
            await manager.broadcast({
                "type": "SCHEDULE_UPDATE",
                "data": {
                    "action": "scheduled",
                    "content_queue_id": str(queue_id)
                }
            })

            return {
                "success": True,
                "message": "Item scheduled successfully",
                "content_queue_id": str(queue_id),
                "scheduled_for": scheduled_for.isoformat()
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"Failed to schedule item: {str(e)}")


@router.put("/reschedule/{content_queue_id}")
async def reschedule_item(content_queue_id: str, request: RescheduleRequest):
    """
    Reschedule an already scheduled item to a new time.
    """
    with get_db_session() as db:
        try:
            queue_id = UUID(content_queue_id)
            queue_item = db.query(ContentQueue).filter(ContentQueue.id == queue_id).first()

            if not queue_item:
                raise HTTPException(404, "Content queue item not found")

            if queue_item.status != "scheduled":
                raise HTTPException(400, f"Item is not scheduled (status: {queue_item.status})")

            # Parse new time (user sends IST datetime)
            new_time = datetime.fromisoformat(request.new_time)

            # Validate not in the past
            if new_time < datetime.now(IST):
                raise HTTPException(400, "Cannot reschedule to the past")

            # Store as naive IST (strip timezone info - database stores naive IST)
            new_time_naive = new_time.replace(tzinfo=None)

            # Update
            old_time = queue_item.scheduled_for
            queue_item.scheduled_for = new_time_naive
            db.commit()

            # Notify via WebSocket
            await manager.broadcast({
                "type": "SCHEDULE_UPDATE",
                "data": {
                    "action": "rescheduled",
                    "content_queue_id": str(queue_id)
                }
            })

            return {
                "success": True,
                "message": "Item rescheduled successfully",
                "old_time": to_ist_isoformat(old_time),
                "new_time": new_time.isoformat()  # From request, already has timezone
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"Failed to reschedule item: {str(e)}")


@router.delete("/cancel/{content_queue_id}")
async def cancel_scheduled_item(content_queue_id: str):
    """
    Cancel a scheduled item (removes from schedule, keeps in ready_to_schedule status).
    """
    with get_db_session() as db:
        try:
            queue_id = UUID(content_queue_id)
            queue_item = db.query(ContentQueue).filter(ContentQueue.id == queue_id).first()

            if not queue_item:
                raise HTTPException(404, "Content queue item not found")

            if queue_item.status != "scheduled":
                raise HTTPException(400, "Item is not scheduled")

            # Clear schedule
            queue_item.scheduled_for = None
            queue_item.status = "ready_to_schedule"
            db.commit()

            # Notify via WebSocket
            await manager.broadcast({
                "type": "SCHEDULE_UPDATE",
                "data": {
                    "action": "cancelled",
                    "content_queue_id": str(queue_id)
                }
            })

            return {
                "success": True,
                "message": "Schedule cancelled - item moved back to ready_to_schedule"
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"Failed to cancel schedule: {str(e)}")


@router.get("/calendar", response_model=CalendarResponse)
async def get_calendar(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Get calendar view of all scheduled items.

    Args:
        start_date: ISO format (optional, defaults to today)
        end_date: ISO format (optional, defaults to +30 days)

    Returns:
        List of scheduled items with times
    """
    with get_db_session() as db:
        try:
            from database.models import Output, Event

            # Parse dates
            ist = ZoneInfo("Asia/Kolkata")
            if start_date:
                start = datetime.fromisoformat(start_date)
            else:
                start = datetime.now(ist).replace(hour=0, minute=0, second=0, microsecond=0)

            if end_date:
                end = datetime.fromisoformat(end_date)
            else:
                end = start + timedelta(days=30)

            # Query scheduled items
            scheduled_items = (
                db.query(ContentQueue)
                .filter(ContentQueue.status == "scheduled")
                .filter(ContentQueue.scheduled_for >= start)
                .filter(ContentQueue.scheduled_for <= end)
                .order_by(ContentQueue.scheduled_for)
                .all()
            )

            # Format response
            items = []
            for queue_item in scheduled_items:
                # Get output and event for context
                output = db.query(Output).filter(Output.id == queue_item.output_id).first()
                event = db.query(Event).filter(Event.id == queue_item.event_id).first() if output else None

                # Get generated content
                generated = (
                    db.query(GeneratedContent)
                    .filter(GeneratedContent.content_queue_id == queue_item.id)
                    .first()
                )

                items.append(ScheduledItem(
                    content_queue_id=str(queue_item.id),
                    scheduled_for=to_ist_isoformat(queue_item.scheduled_for),
                    content_text=generated.content_text if generated else "",
                    event_title=event.title if event else "Unknown",
                    event_type=output.event_type if output else "UNKNOWN",
                    status=queue_item.status
                ))

            return CalendarResponse(
                items=items,
                total=len(items),
                date_range={
                    "start": start.isoformat(),
                    "end": end.isoformat()
                }
            )

        except Exception as e:
            raise HTTPException(500, f"Failed to get calendar: {str(e)}")


@router.get("/suggest-time", response_model=SuggestedTimeResponse)
async def suggest_optimal_time(event_type: Optional[str] = None):
    """
    Get optimal time suggestion based on event type and best practices.

    Returns a suggested time with randomization applied.
    """
    try:
        scheduler = SmartScheduler()
        suggestion = scheduler.suggest_optimal_time(event_type)

        return SuggestedTimeResponse(
            suggested_time=suggestion["suggested_time"].isoformat(),
            window=suggestion["window"],
            reason=suggestion["reason"],
            note=suggestion["note"]
        )

    except Exception as e:
        raise HTTPException(500, f"Failed to suggest time: {str(e)}")


@router.get("/next-slot")
async def get_next_available_slot():
    """
    Get the next available posting slot with randomization.

    Useful for "Schedule Next" quick action.
    """
    try:
        scheduler = SmartScheduler()
        next_slot = scheduler.get_next_available_slot()

        return {
            "next_available_slot": next_slot.isoformat(),
            "note": "Time includes randomization to avoid bot detection"
        }

    except Exception as e:
        raise HTTPException(500, f"Failed to get next slot: {str(e)}")


@router.post("/publish-now/{content_queue_id}")
async def publish_now(content_queue_id: str):
    """
    Bypass schedule and publish content immediately.

    This endpoint:
    - Clears any scheduled_for time
    - Sets status to 'ready_to_schedule' (triggers immediate publish by worker)
    - Useful for urgent manual overrides

    Args:
        content_queue_id: UUID of content queue item

    Returns:
        Success message
    """
    with get_db_session() as db:
        try:
            from services.twitter_publishing_service import TwitterPublishingService

            queue_id = UUID(content_queue_id)
            queue_item = db.query(ContentQueue).filter(ContentQueue.id == queue_id).first()

            if not queue_item:
                raise HTTPException(404, "Content queue item not found")

            if queue_item.status not in ["ready_to_schedule", "scheduled", "failed"]:
                raise HTTPException(
                    400,
                    f"Item cannot be published (status: {queue_item.status})"
                )

            # Publish directly using TwitterPublishingService
            publishing_service = TwitterPublishingService()
            result = publishing_service.publish_content(
                content_queue_id=content_queue_id,
                db=db
            )

            if result["success"]:
                # Notify via WebSocket
                await manager.broadcast({
                    "type": "PUBLISH_UPDATE",
                    "data": {
                        "action": "published_now",
                        "content_queue_id": content_queue_id,
                        "tweet_id": result.get("tweet_id")
                    }
                })

                return {
                    "success": True,
                    "message": "Content published immediately",
                    "tweet_id": result.get("tweet_id"),
                    "tweet_url": result.get("tweet_url")
                }
            else:
                raise HTTPException(500, f"Publishing failed: {result.get('error')}")

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"Failed to publish: {str(e)}")


@router.post("/reset-for-republish/{content_queue_id}")
async def reset_for_republish(content_queue_id: str):
    """
    Reset a published item so it can be republished.

    This endpoint:
    - Clears twitter_post_id and published_at
    - Sets status back to 'ready_to_schedule'
    - Allows republishing content that was already posted

    Use this when:
    - The original tweet was deleted from Twitter
    - You want to post the same content again
    - There was an issue with the original publish

    Args:
        content_queue_id: UUID of content queue item

    Returns:
        Success message
    """
    with get_db_session() as db:
        try:
            queue_id = UUID(content_queue_id)
            queue_item = db.query(ContentQueue).filter(ContentQueue.id == queue_id).first()

            if not queue_item:
                raise HTTPException(404, "Content queue item not found")

            if queue_item.status != "published":
                raise HTTPException(
                    400,
                    f"Item is not published (status: {queue_item.status}). Only published items can be reset for republishing."
                )

            # Store old values for response
            old_tweet_id = queue_item.twitter_post_id
            old_published_at = queue_item.published_at

            # Reset for republishing
            queue_item.twitter_post_id = None
            queue_item.published_at = None
            queue_item.status = "ready_to_schedule"
            queue_item.updated_at = get_ist_now()
            db.commit()

            # Notify via WebSocket
            await manager.broadcast({
                "type": "PUBLISH_UPDATE",
                "data": {
                    "action": "reset_for_republish",
                    "content_queue_id": content_queue_id
                }
            })

            return {
                "success": True,
                "message": "Content reset for republishing. You can now schedule or publish it again.",
                "content_queue_id": content_queue_id,
                "previous_tweet_id": old_tweet_id,
                "previous_published_at": to_ist_isoformat(old_published_at) if old_published_at else None,
                "new_status": "ready_to_schedule"
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"Failed to reset for republishing: {str(e)}")


@router.get("/health")
async def get_worker_health():
    """
    Check Twitter publishing worker health status.

    This endpoint:
    - Reads worker heartbeat file
    - Determines if worker is alive (heartbeat within last 2 minutes)
    - Returns worker stats (success count, failure count, uptime)

    Returns:
        Worker health status with metrics
    """
    try:
        import os
        from datetime import datetime, timedelta

        HEARTBEAT_FILE = os.getenv("WORKER_HEARTBEAT_FILE", "/tmp/twitter_worker_heartbeat.txt")

        # Check if heartbeat file exists
        if not os.path.exists(HEARTBEAT_FILE):
            return {
                "is_alive": False,
                "status": "offline",
                "message": "Worker has never started (no heartbeat file)",
                "heartbeat_file": HEARTBEAT_FILE
            }

        # Read heartbeat file
        with open(HEARTBEAT_FILE, 'r') as f:
            lines = f.readlines()

        if not lines:
            return {
                "is_alive": False,
                "status": "offline",
                "message": "Heartbeat file is empty"
            }

        # Parse heartbeat data
        heartbeat_data = {}
        last_heartbeat_str = lines[0].strip()
        last_heartbeat = datetime.fromisoformat(last_heartbeat_str)

        for line in lines[1:]:
            if ':' in line:
                key, value = line.strip().split(':', 1)
                heartbeat_data[key.strip()] = value.strip()

        # Determine if worker is alive (heartbeat within last 2 minutes)
        now = get_ist_now()
        time_since_heartbeat = now - last_heartbeat
        is_alive = time_since_heartbeat < timedelta(minutes=2)

        # Calculate success rate
        success_count = int(heartbeat_data.get('success_count', 0))
        failure_count = int(heartbeat_data.get('failure_count', 0))
        total = success_count + failure_count
        success_rate = round((success_count / total * 100), 2) if total > 0 else 0

        return {
            "is_alive": is_alive,
            "status": "active" if is_alive else "stale",
            "last_heartbeat": last_heartbeat.isoformat(),
            "time_since_heartbeat_seconds": int(time_since_heartbeat.total_seconds()),
            "success_count": success_count,
            "failure_count": failure_count,
            "total_processed": total,
            "success_rate": success_rate,
            "last_error": heartbeat_data.get('last_error', None),
            "check_interval_seconds": int(os.getenv("WORKER_CHECK_INTERVAL", 60))
        }

    except Exception as e:
        return {
            "is_alive": False,
            "status": "error",
            "error": str(e)
        }
