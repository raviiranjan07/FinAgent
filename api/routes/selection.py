"""
API routes for content selection (Approved Queue).

Handles the workflow where users select which PASS items to publish.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from database.connection import get_db_session
from database.repository import RepositoryManager
from utils.timezone import get_ist_now

router = APIRouter(prefix="/selection", tags=["selection"])


class DeleteSelectedRequest(BaseModel):
    """Request body for deleting multiple outputs"""
    output_ids: List[str]


class SelectForPublishingRequest(BaseModel):
    """Request to select items for publishing"""
    output_ids: List[str]


class SkipContentRequest(BaseModel):
    """Request to skip approved items"""
    output_ids: List[str]
    reason: Optional[str] = None


# DISABLED: Approved Queue removed - users directly generate Twitter content from Outputs page
# @router.get("/approved-queue", response_model=ApprovedQueueResponse)
# async def get_approved_queue(limit: int = 50, offset: int = 0):
#     """
#     DEPRECATED: This endpoint has been removed.
#     Users now generate Twitter content directly from the Outputs page after evaluation.
#     """
#     pass


def generate_v2_content_background(output_id: UUID, event_id: UUID, event_type: str, intent: str):
    """
    Background task to generate v2 Twitter content using TwitterDirectAdapter.

    Args:
        output_id: ID of the Output being processed
        event_id: ID of the Event
        event_type: Event classification
        intent: Content intent
    """
    print(f"\n[Generate v2] Starting v2 pipeline for output {output_id}")

    try:
        from adapters.twitter_direct import TwitterDirectAdapter
        from adapters.context import ExecutionContext
        from models.event import Event as PydanticEvent
        from database.models import Event as DBEvent

        # Get the event
        with get_db_session() as db:
            db_event = db.query(DBEvent).filter(DBEvent.id == event_id).first()
            if not db_event:
                print(f"[Generate v2] ERROR: Event {event_id} not found")
                return

            print(f"[Generate v2] Found event: {db_event.title[:50]}...")

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

            print(f"[Generate v2] Running TwitterDirectAdapter...")
            print(f"[Generate v2]   Event Type: {event_type}")
            print(f"[Generate v2]   Intent: {intent}")

            # Run v2 adapter
            twitter_direct = TwitterDirectAdapter()
            twitter_direct.run(context)

            print(f"[Generate v2] v2 pipeline completed successfully")

    except Exception as e:
        print(f"[Generate v2] ERROR: {e}")
        import traceback
        traceback.print_exc()


@router.post("/approve-for-generation")
async def approve_for_generation(
    request: SelectForPublishingRequest,
    background_tasks: BackgroundTasks
):
    """
    User approves items for Twitter content generation.

    Creates content_queue entries and processes them asynchronously in background.
    Returns immediately without waiting for LLM generation.
    """
    from database.models import Output, Evaluation, ContentQueue
    from api.websocket import manager

    with get_db_session() as db:
        results = []

        for output_id_str in request.output_ids:
            output_id = UUID(output_id_str)

            # Verify output exists and is PASS
            output = db.query(Output).filter(Output.id == output_id).first()
            if not output:
                raise HTTPException(status_code=404, detail=f"Output {output_id_str} not found")

            # Check if has PASS evaluation
            pass_eval = (
                db.query(Evaluation)
                .filter(
                    Evaluation.output_id == output_id,
                    Evaluation.verdict == "PASS"
                )
                .first()
            )

            if not pass_eval:
                raise HTTPException(
                    status_code=400,
                    detail=f"Output {output_id_str} does not have PASS evaluation"
                )

            # Check if already in queue
            existing = (
                db.query(ContentQueue)
                .filter(ContentQueue.output_id == output_id)
                .first()
            )

            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Output {output_id_str} is already in the queue"
                )

            try:
                # Get event data through relationship
                event = output.event
                if not event:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Output {output_id_str} has no associated event"
                    )

                # Create content_queue entry with pending_generation status
                # Format and content_text will be updated by background task
                queue_item = ContentQueue(
                    output_id=output.id,
                    event_title=event.title,
                    event_type=output.event_type,
                    event_url=event.link,
                    format="SINGLE",  # Default, will be updated by background task
                    content_text="(pending generation)",  # Placeholder, required by DB schema
                    status="pending_generation",
                    created_at=get_ist_now()
                )
                db.add(queue_item)
                db.commit()

                # Add background task to generate v2 content
                background_tasks.add_task(generate_v2_content_background, output.id, output.event_id, output.event_type, output.intent)  # v2 pipeline

                results.append({
                    "output_id": output_id_str,
                    "queue_id": str(queue_item.id),
                    "status": "pending_generation"
                })

            except Exception as e:
                db.rollback()
                import traceback
                traceback.print_exc()
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to add {output_id_str} to queue: {str(e)}"
                )

        # Notify connected clients that approved queue has changed
        await manager.broadcast({
            "type": "APPROVED_QUEUE_UPDATE",
            "data": {
                "action": "approved",
                "count": len(results)
            }
        })

        return {
            "success": True,
            "message": f"Approved {len(results)} items for generation. Content is being generated in background.",
            "results": results
        }


@router.delete("/delete-output/{output_id}")
async def delete_output(output_id: str):
    """
    Delete an output and all related data (evaluation, content_queue, generated_content).

    Cascade deletion handles related records automatically.
    """
    from database.models import Output
    from api.websocket import manager

    with get_db_session() as db:
        try:
            output_uuid = UUID(output_id)
            output = db.query(Output).filter(Output.id == output_uuid).first()

            if not output:
                raise HTTPException(status_code=404, detail=f"Output {output_id} not found")

            # Delete output (cascades to evaluations, content_queue, generated_content)
            db.delete(output)
            db.commit()

            # Notify connected clients that approved queue has changed
            await manager.broadcast({
                "type": "APPROVED_QUEUE_UPDATE",
                "data": {
                    "action": "deleted",
                    "output_id": output_id
                }
            })

            return {
                "success": True,
                "message": f"Output {output_id} deleted successfully"
            }

        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid output ID format")
        except Exception as e:
            db.rollback()
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete output: {str(e)}"
            )


@router.post("/skip")
async def skip_content(request: SkipContentRequest):
    """
    User chooses NOT to publish approved items.

    Creates content_queue entries with status = "skipped".
    These items won't appear in approved queue anymore.
    """
    with get_db_session() as db:
        repo = RepositoryManager(db)

        # TODO: Create content_queue entries with status="skipped"
        # For now, just validate outputs exist

        from database.models import Output, Evaluation

        skipped_count = 0
        for output_id_str in request.output_ids:
            output_id = UUID(output_id_str)

            # Verify output exists and is PASS
            output = db.query(Output).filter(Output.id == output_id).first()
            if not output:
                raise HTTPException(status_code=404, detail=f"Output {output_id_str} not found")

            # TODO: Create content_queue entry with status="skipped"

            skipped_count += 1

        return {
            "success": True,
            "message": f"Skipped {skipped_count} items",
            "skipped_count": skipped_count,
            "output_ids": request.output_ids,
            "reason": request.reason
        }


@router.get("/selected")
async def get_selected_items(limit: int = 50, offset: int = 0):
    """
    Get items that have been selected for publishing but not yet generated.

    Returns content_queue items with status = "selected_for_publishing".
    """
    # TODO: Implement once content_queue table exists
    return {
        "items": [],
        "total": 0,
        "message": "TODO: Implement once content_queue table exists"
    }


@router.get("/debug-query")
async def debug_approved_queue():
    """Debug endpoint to diagnose approved queue query issues."""
    from database.models import Output, Evaluation, Event, ContentQueue
    from sqlalchemy import and_, func

    with get_db_session() as db:
        results = {}

        # Step 1: Total outputs
        results["total_outputs"] = db.query(Output).count()

        # Step 2: Total evaluations
        results["total_evaluations"] = db.query(Evaluation).count()

        # Step 3: PASS evaluations
        results["pass_evaluations"] = db.query(Evaluation).filter(Evaluation.verdict == "PASS").count()

        # Step 4: Content queue items
        results["content_queue_items"] = db.query(ContentQueue).count()

        # Step 5: Outputs with PASS evaluation (simple join)
        query_pass = (
            db.query(Output)
            .join(Evaluation, Evaluation.output_id == Output.id)
            .filter(Evaluation.verdict == "PASS")
        )
        results["outputs_with_pass"] = query_pass.count()

        # Step 6: Add outerjoin with ContentQueue
        query_with_queue = (
            db.query(Output)
            .join(Evaluation, Evaluation.output_id == Output.id)
            .outerjoin(ContentQueue, ContentQueue.output_id == Output.id)
            .filter(Evaluation.verdict == "PASS")
        )
        results["after_queue_outerjoin"] = query_with_queue.count()

        # Step 7: Filter for NULL content queue
        query_null_queue = (
            db.query(Output)
            .join(Evaluation, Evaluation.output_id == Output.id)
            .outerjoin(ContentQueue, ContentQueue.output_id == Output.id)
            .filter(
                and_(
                    Evaluation.verdict == "PASS",
                    ContentQueue.id.is_(None)
                )
            )
        )
        results["null_queue_filter"] = query_null_queue.count()

        # Step 8: Check for duplicate outputs (multiple evaluations)
        multi_eval = (
            db.query(Output.id, func.count(Evaluation.id).label('eval_count'))
            .join(Evaluation, Evaluation.output_id == Output.id)
            .group_by(Output.id)
            .having(func.count(Evaluation.id) > 1)
            .all()
        )
        results["outputs_with_multiple_evals"] = len(multi_eval)

        # Step 9: Get sample output IDs from PASS evaluations
        sample_pass_evals = (
            db.query(Evaluation.output_id)
            .filter(Evaluation.verdict == "PASS")
            .limit(5)
            .all()
        )
        results["sample_pass_output_ids"] = [str(e.output_id) for e in sample_pass_evals]

        # Step 10: Check if these sample outputs are in content_queue
        if results["sample_pass_output_ids"]:
            first_output_id = sample_pass_evals[0].output_id
            in_queue = (
                db.query(ContentQueue)
                .filter(ContentQueue.output_id == first_output_id)
                .first()
            )
            results["first_sample_in_queue"] = in_queue is not None

        # Step 11: Count by status
        status_counts = (
            db.query(ContentQueue.status, func.count(ContentQueue.id))
            .group_by(ContentQueue.status)
            .all()
        )
        results["queue_status_counts"] = {status: count for status, count in status_counts}

        return results


@router.get("/queue-status-breakdown")
async def queue_status_breakdown():
    """Show breakdown of content_queue items by status."""
    from database.models import ContentQueue
    from sqlalchemy import func

    with get_db_session() as db:
        status_counts = (
            db.query(ContentQueue.status, func.count(ContentQueue.id))
            .group_by(ContentQueue.status)
            .all()
        )

        return {
            "total_queue_items": db.query(ContentQueue).count(),
            "by_status": {status: count for status, count in status_counts}
        }


@router.delete("/delete-all-outputs")
async def delete_all_outputs():
    """
    Delete ALL outputs and related data from the database.

    This will remove:
    - All outputs
    - All evaluations (cascade)
    - All content_queue entries (cascade)
    - All generated_content (cascade)

    WARNING: This action cannot be undone!
    """
    from database.models import Output
    from api.websocket import manager

    with get_db_session() as db:
        try:
            # Get count before deletion
            total_count = db.query(Output).count()

            if total_count == 0:
                return {
                    "success": True,
                    "message": "No outputs to delete",
                    "deleted_count": 0
                }

            # Delete all outputs (cascades to related tables)
            db.query(Output).delete()
            db.commit()

            # Notify connected clients
            await manager.broadcast({
                "type": "OUTPUTS_CLEARED",
                "data": {
                    "action": "deleted_all",
                    "count": total_count
                }
            })

            return {
                "success": True,
                "message": f"Deleted all {total_count} outputs and related data",
                "deleted_count": total_count
            }

        except Exception as e:
            db.rollback()
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete all outputs: {str(e)}"
            )


@router.delete("/delete-selected-outputs")
async def delete_selected_outputs(request: DeleteSelectedRequest):
    """
    Delete multiple selected outputs by their IDs.

    This will remove:
    - Selected outputs
    - Related evaluations (cascade)
    - Related content_queue entries (cascade)
    - Related generated_content (cascade)

    WARNING: This action cannot be undone!
    """
    from database.models import Output
    from api.websocket import manager
    from uuid import UUID

    output_ids = request.output_ids

    if not output_ids:
        raise HTTPException(status_code=400, detail="No output IDs provided")

    with get_db_session() as db:
        try:
            # Convert string IDs to UUID objects
            uuid_ids = []
            for output_id in output_ids:
                try:
                    uuid_ids.append(UUID(output_id))
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid output ID format: {output_id}"
                    )

            # Delete outputs by IDs (cascades to related tables)
            deleted_count = (
                db.query(Output)
                .filter(Output.id.in_(uuid_ids))
                .delete(synchronize_session=False)
            )
            db.commit()

            if deleted_count == 0:
                return {
                    "success": True,
                    "message": "No outputs found to delete",
                    "deleted_count": 0
                }

            # Notify connected clients
            await manager.broadcast({
                "type": "OUTPUTS_DELETED",
                "data": {
                    "action": "deleted_selected",
                    "count": deleted_count,
                    "output_ids": output_ids
                }
            })

            return {
                "success": True,
                "message": f"Deleted {deleted_count} output(s) and related data",
                "deleted_count": deleted_count
            }

        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete selected outputs: {str(e)}"
            )


@router.delete("/cleanup-old-queue")
async def cleanup_old_queue():
    """
    Clean up old content_queue items with removed statuses.

    Removes items with legacy statuses: 'pending', 'approved', 'rejected', 'scheduled'.
    These statuses were removed in the Pre-MVP status simplification.
    """
    from database.models import ContentQueue

    with get_db_session() as db:
        # Find items with old/unused statuses (removed in Pre-MVP)
        old_statuses = ["pending", "approved", "rejected", "scheduled"]
        old_items = (
            db.query(ContentQueue)
            .filter(ContentQueue.status.in_(old_statuses))
            .all()
        )

        count = len(old_items)

        # Delete them
        for item in old_items:
            db.delete(item)

        db.commit()

        return {
            "success": True,
            "message": f"Cleaned up {count} old content_queue items",
            "deleted_count": count,
            "deleted_statuses": old_statuses
        }
