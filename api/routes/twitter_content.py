"""
Twitter Plugin API routes.

Endpoints for generating, viewing, editing, and publishing Twitter content.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from zoneinfo import ZoneInfo
import json

from database.connection import get_db, get_db_session
from database.models import ContentQueue, Output, Evaluation
from database.schemas import safe_load_twitter_content
from services.twitter_publishing_service import TwitterPublishingService
from utils.timezone import get_ist_now

router = APIRouter(prefix="/twitter", tags=["twitter"])

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
    pipeline_version: Optional[str] = None  # v1 or v2
    generation_intent: Optional[str] = None  # Intent used for generation

    class Config:
        from_attributes = True


class TwitterContentListResponse(BaseModel):
    """Response for Twitter content list."""
    items: List[TwitterContentItem]
    total: int


@router.post("/generate", response_model=GenerateTwitterContentResponse)
async def generate_twitter_content(request: GenerateTwitterContentRequest, background_tasks: BackgroundTasks):
    """
    Generate Twitter content from an approved output using v2 pipeline.

    Uses TwitterDirectAdapter which generates intent-specific tweets directly from
    the RSS event (no intermediate 400-word explanation needed).

    Format decision: EXPLANATORY/POLICY → THREAD, others → SINGLE

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
        existing_v2 = db.query(ContentQueue).filter(
            ContentQueue.output_id == output.id,
            ContentQueue.pipeline_version == 'v2'
        ).first()

        if existing_v2:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "already_generated",
                    "content_queue_id": str(existing_v2.id),
                    "message": "Twitter content already generated for this output"
                }
            )

        # Trigger v2 pipeline in background
        def run_v2_pipeline():
            output_id = str(output.id)
            event_id = str(output.event_id)
            event_type = output.event_type
            intent = output.intent

            print(f"\n[Generate] Starting v2 pipeline generation for output {output_id}")

            # Run v2 pipeline (direct)
            print(f"[Generate] Running v2 pipeline...")
            try:
                # Import here to avoid startup dependency issues
                from adapters.twitter_direct import TwitterDirectAdapter
                from adapters.context import ExecutionContext
                from models.event import Event as PydanticEvent
                from database.models import Event as DBEvent

                # Get the event
                db_local = next(get_db())
                try:
                    db_event = db_local.query(DBEvent).filter(DBEvent.id == event_id).first()
                    if not db_event:
                        print(f"[Generate] ERROR: Event {event_id} not found for v2 pipeline")
                        return

                    print(f"[Generate] Found event: {db_event.title[:50]}...")

                    # Convert to Pydantic Event
                    pydantic_event = PydanticEvent(
                        event_id=db_event.event_id,
                        source=db_event.source,
                        title=db_event.title,
                        summary=db_event.summary or "",
                        url=db_event.link or "",
                        country="",
                        published_at=db_event.published_at.isoformat() if db_event.published_at else ""
                    )

                    # Create context with existing classification
                    context = ExecutionContext(event=pydantic_event)
                    context.event_type = event_type
                    context.intent = intent
                    context.db_event_id = str(db_event.id)
                    context.db_output_id = output_id  # Pass output_id for content_queue foreign key

                    print(f"[Generate] Running TwitterDirectAdapter...")
                    print(f"[Generate]   Event Type: {event_type}")
                    print(f"[Generate]   Intent: {intent}")

                    # Run v2 adapter
                    twitter_direct = TwitterDirectAdapter()
                    twitter_direct.run(context)

                    print(f"[Generate] v2 pipeline completed successfully")

                except Exception as e:
                    print(f"[Generate] ERROR in v2 pipeline: {e}")
                    import traceback
                    traceback.print_exc()
                finally:
                    db_local.close()

            except Exception as e:
                print(f"[Generate] ERROR importing v2 modules: {e}")
                import traceback
                traceback.print_exc()

        background_tasks.add_task(run_v2_pipeline)

        return GenerateTwitterContentResponse(
            success=True,
            status="generating",
            content_queue_id=None  # Will be created by plugins
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

            # Database stores naive IST timestamps - just add IST timezone info for display
            def to_ist_datetime(dt: Optional[datetime]) -> Optional[datetime]:
                if dt is None:
                    return None
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=IST)
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
                updated_at=to_ist_datetime(item.updated_at),
                pipeline_version=item.pipeline_version,
                generation_intent=item.generation_intent
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
            item.updated_at = get_ist_now()
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
            item.updated_at = get_ist_now()
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
    Regenerate Twitter content for an existing content queue item using v2 pipeline.

    Calls the LLM again to generate a new version of the tweet/thread,
    replacing the existing content.

    Args:
        content_queue_id: ID of the content queue item to regenerate

    Returns:
        Success response with new content
    """
    from config.twitter_prompts import (
        get_intent_specific_single_prompt,
        get_intent_specific_thread_prompt
    )
    from services.llm_service import get_twitter_llm_service

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

            # 5. Update status to generating
            content_item.status = "generating"
            content_item.updated_at = get_ist_now()
            db.commit()

            # 6. Decide format based on intent (v2 logic)
            intent = output.intent
            thread_intents = ["EXPLANATORY", "POLICY"]

            if intent in thread_intents:
                new_format = "THREAD"
            else:
                new_format = "SINGLE"

            print(f"[Regenerate] Format decision: {new_format} for intent {intent}")

            # 7. Generate content using v2 prompts
            llm = get_twitter_llm_service()

            try:
                if new_format == "SINGLE":
                    # Generate single tweet
                    prompt = get_intent_specific_single_prompt(
                        intent=intent,
                        event_title=event.title,
                        poc_content=event.summary or ""
                    )

                    tweet = llm.generate(prompt).strip()

                    # Remove quotes if LLM added them
                    if tweet.startswith('"') and tweet.endswith('"'):
                        tweet = tweet[1:-1]
                    if tweet.startswith("'") and tweet.endswith("'"):
                        tweet = tweet[1:-1]

                    # Enforce length limit
                    max_length = 280
                    if len(tweet) > max_length:
                        print(f"[Regenerate] Tweet exceeds {max_length} chars, truncating")
                        tweet = tweet[:277] + "..."

                    new_content_text = json.dumps({
                        "format": "SINGLE",
                        "content": {
                            "tweet": tweet
                        }
                    })
                    new_thread_length = 1

                else:  # THREAD
                    # Generate thread
                    prompt = get_intent_specific_thread_prompt(
                        intent=intent,
                        event_type=output.event_type,
                        event_title=event.title,
                        poc_content=event.summary or ""
                    )

                    raw_output = llm.generate(prompt).strip()

                    # Parse thread (expecting JSON array)
                    try:
                        thread_tweets = json.loads(raw_output)
                        if not isinstance(thread_tweets, list):
                            raise ValueError("Thread output must be a JSON array")
                    except json.JSONDecodeError:
                        # Fallback: split by newlines if not JSON
                        print(f"[Regenerate] Thread not in JSON format, splitting by lines")
                        thread_tweets = [t.strip() for t in raw_output.split('\n') if t.strip()]

                    # Validate and enforce length limits
                    validated_tweets = []
                    max_length = 280
                    for tweet in thread_tweets[:3]:  # Max 3 tweets
                        tweet = tweet.strip()

                        # Remove quotes
                        if tweet.startswith('"') and tweet.endswith('"'):
                            tweet = tweet[1:-1]
                        if tweet.startswith("'") and tweet.endswith("'"):
                            tweet = tweet[1:-1]

                        # Enforce length
                        if len(tweet) > max_length:
                            tweet = tweet[:277] + "..."

                        validated_tweets.append(tweet)

                    if not validated_tweets:
                        raise ValueError("No valid tweets in thread")

                    new_content_text = json.dumps({
                        "format": "THREAD",
                        "content": {
                            "tweets": validated_tweets
                        }
                    })
                    new_thread_length = len(validated_tweets)

            except Exception as gen_error:
                # Generation failed - mark as failed
                content_item.status = "failed"
                content_item.error_message = f"Regeneration failed: {str(gen_error)}"
                content_item.updated_at = get_ist_now()
                db.commit()
                raise HTTPException(
                    status_code=500,
                    detail=f"Content regeneration failed: {str(gen_error)}"
                )

            # 8. Update the content queue item
            content_item.format = new_format
            content_item.content_text = new_content_text
            content_item.thread_length = new_thread_length
            content_item.status = "ready_to_schedule"  # v2 doesn't use HITL for regeneration
            content_item.edited_content = None  # Clear any previous edits
            content_item.error_message = None
            content_item.updated_at = get_ist_now()
            db.commit()

            print(f"[Regenerate] Content {content_queue_id} regenerated successfully")
            print(f"             Format: {new_format}, Status: ready_to_schedule")

            return {
                "success": True,
                "content_queue_id": content_queue_id,
                "format": new_format,
                "thread_length": new_thread_length,
                "status": "ready_to_schedule",
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
