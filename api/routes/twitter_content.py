"""Twitter Plugin API routes.

Endpoints for generating, viewing, editing, and publishing Twitter content.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from zoneinfo import ZoneInfo
import subprocess
import sys
import json

from database.connection import get_db, get_db_session
from database.models import ContentQueue, Output, Evaluation
from database.schemas import safe_load_twitter_content
from services.twitter_publishing_service import TwitterPublishingService

router = APIRouter(prefix="/twitter", tags=["twitter"])

# Timezone conversion helper
IST = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")


def to_ist_isoformat(dt: Optional[datetime]) -> Optional[str]:
    """
    Convert database datetime (UTC, timezone-naive) to IST ISO format string.

    Args:
        dt: Datetime from database (UTC, timezone-naive)

    Returns:
        ISO format string with IST timezone (e.g., "2026-01-25T15:28:34+05:30")
        or None if input is None
    """
    if dt is None:
        return None

    # Database stores timezone-naive UTC - make it timezone-aware and convert to IST
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    # Convert to IST and return ISO format (includes +05:30 suffix)
    return dt.astimezone(IST).isoformat()


class GenerateTwitterContentRequest(BaseModel):
    """Request to generate Twitter content from an approved output."""
    output_id: str


class GenerateTwitterContentResponse(BaseModel):
    """Response after triggering Twitter content generation."""
    success: bool
    content_queue_id: Optional[str] = None
    format: Optional[str] = None
    status: str
    error: Optional[str] = None


class TwitterContentItem(BaseModel):
    """Twitter content item for display."""
    id: str
    output_id: str
    event_title: Optional[str] = "(Unknown Event)"
    event_type: Optional[str] = None
    event_url: Optional[str] = None
    format: str  # SINGLE or THREAD
    thread_length: int
    content_text: str  # For display (single tweet or formatted thread)
    tweets: Optional[List[str]] = None  # Parsed tweets for THREAD format
    edited_content: Optional[str] = None
    impact_framing: Optional[dict] = None
    character_count: int
    edited_character_count: Optional[int] = 0
    is_edited: bool
    is_published: bool
    status: str
    twitter_post_id: Optional[str] = None
    published_at: Optional[datetime] = None
    scheduled_for: Optional[datetime] = None  # Scheduled publish time
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TwitterContentListResponse(BaseModel):
    """Response for Twitter content list."""
    items: List[TwitterContentItem]
    total: int


@router.post("/generate", response_model=GenerateTwitterContentResponse)
async def generate_twitter_content(request: GenerateTwitterContentRequest, background_tasks: BackgroundTasks):
    """
    Generate Twitter content from an approved output.

    This triggers the Twitter plugin pipeline:
    1. ImpactFraming: Extract angles
    2. FormatDecision: Decide SINGLE vs THREAD
    3. TwitterGeneration: Create content
    4. TwitterClarity: Validate
    5. Save to content_queue

    Args:
        request: GenerateTwitterContentRequest with output_id

    Returns:
        GenerateTwitterContentResponse with status and content_queue_id
    """
    db = next(get_db())

    try:
        # Validate output_id
        output = db.query(Output).filter(Output.id == request.output_id).first()

        if not output:
            raise HTTPException(status_code=404, detail="Output not found")

        # Check if output has PASS evaluation
        has_pass = db.query(Evaluation).filter(
            Evaluation.output_id == output.id,
            Evaluation.verdict == "PASS"
        ).first()

        if not has_pass:
            raise HTTPException(
                status_code=400,
                detail="Output must have PASS evaluation before generating Twitter content"
            )

        # Check if already generated
        existing = db.query(ContentQueue).filter(
            ContentQueue.output_id == output.id
        ).first()

        if existing:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "already_generated",
                    "content_queue_id": str(existing.id),
                    "message": "Twitter content already generated for this output"
                }
            )

        # Trigger Twitter plugin in background
        # We'll use subprocess to run the plugin script
        def run_twitter_plugin():
            subprocess.run([
                sys.executable,
                "run_twitter_plugin.py",
                "--output-id", str(output.id)
            ])

        background_tasks.add_task(run_twitter_plugin)

        return GenerateTwitterContentResponse(
            success=True,
            status="generating",
            content_queue_id=None  # Will be created by plugin
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to trigger generation: {str(e)}")

    finally:
        db.close()


@router.get("/list", response_model=TwitterContentListResponse)
async def list_twitter_content(
    status: Optional[str] = None,
    format: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    Get list of Twitter content from content_queue.

    Args:
        status: Filter by status (optional)
        format: Filter by format - SINGLE or THREAD (optional)
        limit: Max number of items to return
        offset: Offset for pagination

    Returns:
        TwitterContentListResponse with items and total count
    """
    db = next(get_db())

    try:
        query = db.query(ContentQueue)

        if status:
            query = query.filter(ContentQueue.status == status)

        if format:
            query = query.filter(ContentQueue.format == format)

        query = query.order_by(ContentQueue.created_at.desc())

        total = query.count()
        queue_items = query.offset(offset).limit(limit).all()

        items = []
        for item in queue_items:
            # Skip items with no content (failed generation)
            if not item.content_text:
                content_display = "(No content - generation failed)"
                tweets = []
                char_count = 0
            else:
                # Use Pydantic schema for validation and parsing
                twitter_content = safe_load_twitter_content(item.format, item.content_text)

                if twitter_content:
                    # Successfully parsed with schema
                    if item.format == "SINGLE":
                        tweet_text = twitter_content.content.tweet
                        content_display = tweet_text
                        tweets = [tweet_text]
                        char_count = len(tweet_text)
                    else:  # THREAD
                        tweets = twitter_content.content.tweets
                        content_display = f"Thread ({len(tweets)} tweets)"
                        char_count = sum(len(t) for t in tweets)
                else:
                    # Fallback for malformed content
                    tweets = []
                    content_display = f"(Invalid {item.format} content)"
                    char_count = 0

            # Parse impact_framing
            impact_framing = None
            if item.impact_framing:
                try:
                    impact_framing = json.loads(item.impact_framing)
                except json.JSONDecodeError:
                    pass

            # Convert timezone-naive UTC datetimes to IST for display
            def to_ist_datetime(dt: Optional[datetime]) -> Optional[datetime]:
                if dt is None:
                    return None
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=UTC).astimezone(IST)
                return dt

            items.append(TwitterContentItem(
                id=str(item.id),
                output_id=str(item.output_id),
                event_title=item.event_title or "(Unknown Event)",
                event_type=item.event_type,
                event_url=item.event_url,
                format=item.format,
                thread_length=item.thread_length,
                content_text=content_display,
                tweets=tweets,
                edited_content=item.edited_content,
                impact_framing=impact_framing,
                character_count=char_count,
                edited_character_count=len(item.edited_content) if item.edited_content else 0,
                is_edited=bool(item.edited_content),
                is_published=bool(item.twitter_post_id or item.published_at),
                status=item.status,
                twitter_post_id=item.twitter_post_id,
                published_at=to_ist_datetime(item.published_at),
                scheduled_for=to_ist_datetime(item.scheduled_for),
                created_at=to_ist_datetime(item.created_at),
                updated_at=to_ist_datetime(item.updated_at)
            ))

        return TwitterContentListResponse(items=items, total=total)

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch content: {str(e)}")

    finally:
        db.close()


@router.post("/approve-hitl/{content_queue_id}")
async def approve_hitl_content(content_queue_id: str):
    """
    Approve Twitter content that requires HITL review.

    Moves content from 'pending_hitl' to 'ready_to_schedule' status.

    Args:
        content_queue_id: ID of content to approve

    Returns:
        Success response
    """
    with get_db_session() as db:
        try:
            item = db.query(ContentQueue).filter(ContentQueue.id == content_queue_id).first()

            if not item:
                raise HTTPException(status_code=404, detail="Content not found")

            if item.status != "pending_hitl":
                raise HTTPException(
                    status_code=400,
                    detail=f"Content status is '{item.status}', expected 'pending_hitl'"
                )

            # Approve: Move to ready_to_schedule
            item.status = "ready_to_schedule"
            item.updated_at = datetime.utcnow()
            db.commit()

            print(f"[HITL] Content {content_queue_id} approved by user")

            return {
                "success": True,
                "message": "Content approved - moved to ready_to_schedule",
                "content_queue_id": content_queue_id,
                "new_status": "ready_to_schedule"
            }

        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Failed to approve content: {str(e)}")


class RejectHITLRequest(BaseModel):
    """Request to reject HITL content with reason."""
    reason: Optional[str] = None


@router.post("/reject-hitl/{content_queue_id}")
async def reject_hitl_content(content_queue_id: str, request: RejectHITLRequest = RejectHITLRequest()):
    """
    Reject Twitter content that requires HITL review.

    Moves content from 'pending_hitl' to 'failed' status with rejection reason.

    Args:
        content_queue_id: ID of content to reject
        request: Optional rejection reason

    Returns:
        Success response
    """
    with get_db_session() as db:
        try:
            item = db.query(ContentQueue).filter(ContentQueue.id == content_queue_id).first()

            if not item:
                raise HTTPException(status_code=404, detail="Content not found")

            if item.status != "pending_hitl":
                raise HTTPException(
                    status_code=400,
                    detail=f"Content status is '{item.status}', expected 'pending_hitl'"
                )

            # Extract rejection reason from request body
            rejection_reason = request.reason if request and request.reason else None

            # Reject: Move to failed with rejection reason
            item.status = "failed"
            if rejection_reason:
                item.error_message = f"Rejected during HITL review: {rejection_reason}"
            else:
                item.error_message = "Rejected during HITL review"
            item.updated_at = datetime.utcnow()
            db.commit()

            print(f"[HITL] Content {content_queue_id} rejected by user")
            if rejection_reason:
                print(f"       Reason: {rejection_reason}")

            return {
                "success": True,
                "message": "Content rejected - moved to failed",
                "content_queue_id": content_queue_id,
                "new_status": "failed",
                "rejection_reason": rejection_reason
            }

        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Failed to reject content: {str(e)}")


@router.delete("/{content_queue_id}")
async def delete_twitter_content(content_queue_id: str):
    """
    Delete Twitter content from queue.

    Args:
        content_queue_id: ID of content to delete

    Returns:
        Success response
    """
    db = next(get_db())

    try:
        item = db.query(ContentQueue).filter(ContentQueue.id == content_queue_id).first()

        if not item:
            raise HTTPException(status_code=404, detail="Content not found")

        # Don't allow deletion of live published content (but allow dry run deletion)
        if item.status == "published":
            # Check if it's a dry run publish (tweet_id starts with "dry_run_")
            is_dry_run = item.twitter_post_id and item.twitter_post_id.startswith("dry_run_")
            if not is_dry_run:
                raise HTTPException(
                    status_code=409,
                    detail="Cannot delete live published content"
                )

        db.delete(item)
        db.commit()

        return {"success": True, "message": f"Content {content_queue_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to delete content: {str(e)}")

    finally:
        db.close()


# =============================================================================
# Publishing Routes (Phase 3)
# =============================================================================

@router.post("/publish/{content_queue_id}")
async def publish_now(content_queue_id: str):
    """
    Publish content to Twitter immediately.

    Args:
        content_queue_id: ID of content to publish

    Returns:
        Publishing result with tweet ID and URL
    """
    with get_db_session() as db:
        try:
            # Check if content exists
            content = db.query(ContentQueue).filter(
                ContentQueue.id == content_queue_id
            ).first()

            if not content:
                raise HTTPException(status_code=404, detail="Content not found")

            # Check if already published
            if content.twitter_post_id:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "already_published",
                        "tweet_id": content.twitter_post_id,
                        "twitter_url": f"https://twitter.com/i/web/status/{content.twitter_post_id}"
                    }
                )

            # Check status
            if content.status not in ["ready_to_schedule", "failed"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Content status is '{content.status}', cannot publish"
                )

            # Publish
            publishing_service = TwitterPublishingService()
            result = publishing_service.publish_content(content_queue_id, db)

            if result["success"]:
                return {
                    "success": True,
                    "tweet_id": result["tweet_id"],
                    "tweet_ids": result.get("tweet_ids"),
                    "twitter_url": result["twitter_url"],
                    "published_at": result["published_at"]
                }
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Publishing failed: {result.get('error', 'Unknown error')}"
                )

        except HTTPException:
            raise
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Failed to publish: {str(e)}")


@router.post("/retry/{content_queue_id}")
async def retry_failed_publish(content_queue_id: str):
    """
    Retry publishing failed content.

    Args:
        content_queue_id: ID of content to retry

    Returns:
        Publishing result
    """
    with get_db_session() as db:
        try:
            content = db.query(ContentQueue).filter(
                ContentQueue.id == content_queue_id
            ).first()

            if not content:
                raise HTTPException(status_code=404, detail="Content not found")

            if content.status != "failed":
                raise HTTPException(
                    status_code=400,
                    detail=f"Content status is '{content.status}', not 'failed'"
                )

            # Retry
            publishing_service = TwitterPublishingService()
            result = publishing_service.retry_failed(content_queue_id, db)

            if result["success"]:
                return {
                    "success": True,
                    "tweet_id": result["tweet_id"],
                    "twitter_url": result["twitter_url"],
                    "published_at": result["published_at"]
                }
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Retry failed: {result.get('error', 'Unknown error')}"
                )

        except HTTPException:
            raise
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Failed to retry: {str(e)}")


@router.get("/status/{content_queue_id}")
async def get_publish_status(content_queue_id: str):
    """
    Get publishing status for content.

    Args:
        content_queue_id: ID of content

    Returns:
        Status information including tweet URL if published
    """
    db = next(get_db())

    try:
        content = db.query(ContentQueue).filter(
            ContentQueue.id == content_queue_id
        ).first()

        if not content:
            raise HTTPException(status_code=404, detail="Content not found")

        response = {
            "content_queue_id": str(content.id),
            "status": content.status,
            "format": content.format,
            "scheduled_for": to_ist_isoformat(content.scheduled_for),
            "published_at": to_ist_isoformat(content.published_at),
            "twitter_post_id": content.twitter_post_id,
            "error_message": content.error_message
        }

        if content.twitter_post_id:
            response["twitter_url"] = f"https://twitter.com/i/web/status/{content.twitter_post_id}"

        return response

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch status: {str(e)}")

    finally:
        db.close()


@router.get("/settings")
async def get_publishing_settings():
    """
    Get current publishing mode settings.

    Returns:
        Publishing configuration (enabled, dry_run, etc.)
    """
    import os
    from dotenv import load_dotenv

    load_dotenv()

    enabled = os.getenv("TWITTER_PUBLISHING_ENABLED", "false").lower() == "true"
    dry_run = os.getenv("TWITTER_DRY_RUN", "true").lower() == "true"

    # Determine mode
    if not enabled:
        mode = "DISABLED"
    elif dry_run:
        mode = "DRY_RUN"
    else:
        mode = "LIVE"

    return {
        "enabled": enabled,
        "dry_run": dry_run,
        "mode": mode,
        "description": {
            "DISABLED": "Publishing is disabled - content won't be posted",
            "DRY_RUN": "Dry run mode - simulates posting without actual Twitter API calls",
            "LIVE": "Live mode - content will be posted to real Twitter account"
        }.get(mode, "Unknown mode")
    }


# =============================================================================
# Regenerate Endpoint
# =============================================================================

@router.post("/regenerate/{content_queue_id}")
async def regenerate_twitter_content(content_queue_id: str):
    """
    Regenerate Twitter content for an existing content queue item.

    Calls the LLM again to generate a new version of the tweet/thread,
    replacing the existing content.

    Args:
        content_queue_id: ID of the content queue item to regenerate

    Returns:
        Success response with new content
    """
    from adapters.context import ExecutionContext
    from adapters.plugins.twitter import (
        FormatDecisionAdapter,
        TwitterSingleAdapter,
        TwitterThreadAdapter,
        TwitterClarityAdapter,
        TwitterHITLAdapter
    )
    from models.event import Event as EventModel

    with get_db_session() as db:
        try:
            # 1. Get the content queue item
            content_item = db.query(ContentQueue).filter(
                ContentQueue.id == content_queue_id
            ).first()

            if not content_item:
                raise HTTPException(status_code=404, detail="Content not found")

            # 2. Check if already published (cannot regenerate published content)
            if content_item.status == "published" and content_item.twitter_post_id:
                # Allow regeneration of dry run publishes
                if not content_item.twitter_post_id.startswith("dry_run_"):
                    raise HTTPException(
                        status_code=409,
                        detail="Cannot regenerate published content"
                    )

            # 3. Get the associated output
            output = db.query(Output).filter(Output.id == content_item.output_id).first()
            if not output:
                raise HTTPException(status_code=404, detail="Associated output not found")

            # 4. Get the event
            from database.models import Event as DBEvent
            event = db.query(DBEvent).filter(DBEvent.id == output.event_id).first()
            if not event:
                raise HTTPException(status_code=404, detail="Associated event not found")

            # 5. Create ExecutionContext for the adapters
            event_model = EventModel(
                event_id=str(event.id),
                source=event.source or "",
                title=event.title or "",
                summary=event.summary or "",
                url=event.link or "",
                country="",
                published_at=event.published_at.isoformat() if event.published_at else ""
            )

            context = ExecutionContext(
                event=event_model,
                event_type=output.event_type,
                intent=output.intent,
                llm_output=output.llm_output
            )

            # 6. Update status to generating
            content_item.status = "generating"
            content_item.updated_at = datetime.utcnow()
            db.commit()

            # 7. Run Twitter adapters pipeline
            try:
                # Format Decision
                format_adapter = FormatDecisionAdapter()
                context = format_adapter.run(context)

                # Generate content based on format
                if context.twitter_format and context.twitter_format.get("format") == "SINGLE":
                    single_adapter = TwitterSingleAdapter()
                    context = single_adapter.run(context)
                else:
                    thread_adapter = TwitterThreadAdapter()
                    context = thread_adapter.run(context)

                # Clarity check
                clarity_adapter = TwitterClarityAdapter()
                context = clarity_adapter.run(context)

                # HITL check
                hitl_adapter = TwitterHITLAdapter()
                context = hitl_adapter.run(context)

            except Exception as gen_error:
                # Generation failed - mark as failed
                content_item.status = "failed"
                content_item.error_message = f"Regeneration failed: {str(gen_error)}"
                content_item.updated_at = datetime.utcnow()
                db.commit()
                raise HTTPException(
                    status_code=500,
                    detail=f"Content regeneration failed: {str(gen_error)}"
                )

            # 8. Check if generation succeeded
            if not context.twitter_content:
                content_item.status = "failed"
                content_item.error_message = "Regeneration failed: No content generated"
                content_item.updated_at = datetime.utcnow()
                db.commit()
                raise HTTPException(
                    status_code=500,
                    detail="Content regeneration failed: No content generated"
                )

            # 9. Update content queue with new content
            new_format = context.twitter_content.get("format", "SINGLE")

            if new_format == "SINGLE":
                new_content_text = json.dumps({
                    "format": "SINGLE",
                    "content": {
                        "tweet": context.twitter_content.get("tweet", "")
                    }
                })
                new_thread_length = 1
            else:  # THREAD
                tweets_dict = context.twitter_content.get("tweets", {})
                tweets_list = [tweets_dict.get(f"tweet{i}", "") for i in range(1, len(tweets_dict) + 1)]
                new_content_text = json.dumps({
                    "format": "THREAD",
                    "content": {
                        "tweets": tweets_list
                    }
                })
                new_thread_length = len(tweets_list)

            # Determine new status based on HITL
            # Handle both dict and HITLDecision object
            hitl_required = False
            if context.twitter_hitl:
                if isinstance(context.twitter_hitl, dict):
                    hitl_required = context.twitter_hitl.get("required", False)
                else:
                    hitl_required = context.twitter_hitl.required

            if hitl_required:
                new_status = "pending_hitl"
            else:
                new_status = "ready_to_schedule"

            # Update the content queue item
            content_item.format = new_format
            content_item.content_text = new_content_text
            content_item.thread_length = new_thread_length
            content_item.status = new_status
            content_item.edited_content = None  # Clear any previous edits
            content_item.error_message = None
            content_item.updated_at = datetime.utcnow()

            # Store clarity issues if any
            if context.twitter_clarity_issues:
                content_item.clarity_issues = json.dumps(context.twitter_clarity_issues)

            db.commit()

            print(f"[Regenerate] Content {content_queue_id} regenerated successfully")
            print(f"             Format: {new_format}, Status: {new_status}")

            return {
                "success": True,
                "content_queue_id": content_queue_id,
                "format": new_format,
                "thread_length": new_thread_length,
                "status": new_status,
                "message": "Content regenerated successfully"
            }

        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to regenerate content: {str(e)}"
            )
