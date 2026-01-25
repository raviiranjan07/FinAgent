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

router = APIRouter(prefix="/selection", tags=["selection"])


class ApprovedQueueItem(BaseModel):
    """Item in the approved queue (PASS evaluation, awaiting selection)"""
    output_id: str
    event_id: str
    event_title: str
    event_source: str
    event_published_at: datetime
    event_type: str
    intent: str
    hitl_risk_level: str
    clarity_issues: List[str]
    llm_output: str  # Raw LLM output


class DeleteSelectedRequest(BaseModel):
    """Request body for deleting multiple outputs"""
    output_ids: List[str]


class ApprovedQueueResponse(BaseModel):
    """Response for approved queue list"""
    items: List[ApprovedQueueItem]
    total: int


class SelectForPublishingRequest(BaseModel):
    """Request to select items for publishing"""
    output_ids: List[str]


class SkipContentRequest(BaseModel):
    """Request to skip approved items"""
    output_ids: List[str]
    reason: Optional[str] = None


@router.get("/approved-queue", response_model=ApprovedQueueResponse)
async def get_approved_queue(limit: int = 50, offset: int = 0):
    """
    Get all PASS items waiting for user selection.

    Returns outputs where:
    - evaluation.verdict = PASS
    - No content_queue entry (not yet approved for generation)

    These are items that passed quality check but haven't been selected
    for publishing yet.
    """
    with get_db_session() as db:
        repo = RepositoryManager(db)

        # Get PASS outputs not yet in content queue
        # This query needs to join outputs -> evaluations -> content_queue
        # and filter for verdict=PASS and no queue entry

        from database.models import Output, Evaluation, Event, ContentQueue
        from sqlalchemy import and_, or_
        from sqlalchemy.orm import joinedload, outerjoin

        # Use subquery approach to avoid issues with multiple evaluations per output
        # Step 1: Get output IDs that have PASS evaluation and are NOT in content_queue yet
        from sqlalchemy import distinct

        subquery = (
            db.query(distinct(Output.id))
            .join(Evaluation, Evaluation.output_id == Output.id)
            .outerjoin(ContentQueue, ContentQueue.output_id == Output.id)
            .filter(
                and_(
                    Evaluation.verdict == "PASS",
                    ContentQueue.id.is_(None)  # Not in queue yet
                )
            )
        ).subquery()

        # Step 2: Query full Output objects for those IDs
        query = (
            db.query(Output)
            .filter(Output.id.in_(db.query(subquery)))
            .options(
                joinedload(Output.event),
                joinedload(Output.evaluations)
            )
            .order_by(Output.created_at.desc())
        )

        total = query.count()
        items_db = query.offset(offset).limit(limit).all()

        items = []
        for output in items_db:
            # Get the PASS evaluation
            pass_eval = next((e for e in output.evaluations if e.verdict == "PASS"), None)

            items.append(ApprovedQueueItem(
                output_id=str(output.id),
                event_id=str(output.event_id),
                event_title=output.event.title if output.event else "",
                event_source=output.event.source if output.event else "",
                event_published_at=(output.event.published_at if (output.event and output.event.published_at) else datetime.utcnow()),
                event_type=output.event_type,
                intent=output.intent,
                hitl_risk_level=output.hitl_risk_level,
                clarity_issues=output.clarity_issues or [],
                llm_output=output.llm_output,
                created_at=output.created_at,
                approved_at=pass_eval.evaluated_at if pass_eval else None
            ))

        return ApprovedQueueResponse(items=items, total=total)


def generate_content_background(queue_id: UUID):
    """
    Background task to generate Twitter content for a queue item.

    Args:
        queue_id: ID of the ContentQueue item to process
    """
    from database.models import Output, ContentQueue, GeneratedContent
    from services.content_generator import ContentGeneratorService

    with get_db_session() as db:
        try:
            # Get queue item
            queue_item = db.query(ContentQueue).filter(ContentQueue.id == queue_id).first()
            if not queue_item:
                print(f"[ERROR] Queue item {queue_id} not found")
                return

            # Update status to generating
            queue_item.status = "generating"
            db.commit()

            print(f"[+] Processing queue item {queue_id} for output {queue_item.output_id}")

            # Get the output with event relationship
            from sqlalchemy.orm import joinedload
            output = db.query(Output).options(joinedload(Output.event)).filter(Output.id == queue_item.output_id).first()
            if not output:
                raise ValueError(f"Output {queue_item.output_id} not found")

            # Generate Twitter content
            generator = ContentGeneratorService()
            generated = generator.generate_twitter_content(output, queue_item.id, db)

            # Update ContentQueue with generated content AND HITL decision
            queue_item.content_text = generated.content_text
            queue_item.hashtags = generated.hashtags

            # HITL Gate: Check if human review is required (from POC pipeline)
            # If HITL required, block at "pending_hitl" status until manual approval
            # If HITL not required, proceed directly to "ready_to_schedule"
            queue_item.hitl_required = output.hitl_required or False
            queue_item.hitl_risk_level = output.hitl_risk_level
            queue_item.suggested_verdict = output.suggested_verdict

            if queue_item.hitl_required:
                queue_item.status = "pending_hitl"
                print(f"[HITL] Content requires human review - blocking at pending_hitl status")
                print(f"       Risk Level: {queue_item.hitl_risk_level}")
                print(f"       Suggested Verdict: {queue_item.suggested_verdict}")
            else:
                queue_item.status = "ready_to_schedule"
                print(f"[HITL] No review required - moving to ready_to_schedule")

            queue_item.error_message = None
            db.commit()

            print(f"[OK] Generated content for queue item {queue_id}")
            print(f"    Text: {generated.content_text[:80]}...")
            print(f"    Characters: {generated.character_count}/280")

        except Exception as e:
            # Mark as failed with error message
            queue_item = db.query(ContentQueue).filter(ContentQueue.id == queue_id).first()
            if queue_item:
                queue_item.status = "failed"
                queue_item.error_message = str(e)
                db.commit()

            print(f"[ERROR] Failed to process queue item {queue_id}: {e}")
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
                    created_at=datetime.utcnow()
                )
                db.add(queue_item)
                db.commit()

                # Add background task to generate content
                background_tasks.add_task(generate_content_background, queue_item.id)

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
