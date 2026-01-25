"""
API routes for generated content management.

Handles viewing, scheduling, and publishing of generated Twitter content.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from database.connection import get_db_session
from database.models import GeneratedContent, ContentQueue, Output, Event
from api.validators import ContentValidator

router = APIRouter(prefix="/content", tags=["content"])


class GeneratedContentItem(BaseModel):
    """Generated content item for display."""
    id: str
    output_id: str
    content_queue_id: str
    platform: str
    content_text: Optional[str] = None
    edited_content: Optional[str] = None
    hashtags: List[str]
    character_count: Optional[int] = 0
    edited_character_count: Optional[int] = 0
    is_edited: bool = False
    is_published: bool = False
    generated_at: Optional[datetime] = None
    status: str
    error_message: Optional[str] = None
    event_title: Optional[str] = None
    event_source: Optional[str] = None

    class Config:
        from_attributes = True


class GeneratedContentResponse(BaseModel):
    """Response for generated content list."""
    items: List[GeneratedContentItem]
    total: int


class EditContentRequest(BaseModel):
    """Request to edit generated content."""
    edited_content: str


class EditContentResponse(BaseModel):
    """Response after editing content."""
    id: str  # UUID as string
    content_text: str
    edited_content: str
    is_edited: bool
    edited_character_count: int


@router.get("/generated", response_model=GeneratedContentResponse)
async def get_generated_content(limit: int = 50, offset: int = 0):
    """
    Get all content queue items (including pending, generating, ready, failed).

    Returns all items that have been approved for generation, regardless of status.
    """
    with get_db_session() as db:
        from sqlalchemy.orm import joinedload, outerjoin

        # Query content queue items (left join with generated_content since it might not exist yet)
        query = (
            db.query(ContentQueue)
            .join(Output, Output.id == ContentQueue.output_id)
            .join(Event, Event.id == Output.event_id)
            .outerjoin(GeneratedContent, GeneratedContent.content_queue_id == ContentQueue.id)
            .filter(ContentQueue.status.in_([
                "pending_generation",
                "generating",
                "ready_to_schedule",
                "scheduled",
                "published",
                "failed"
            ]))
            .options(
                joinedload(ContentQueue.output).joinedload(Output.event)
            )
            .order_by(ContentQueue.created_at.desc())
        )

        total = query.count()
        queue_items = query.offset(offset).limit(limit).all()

        items = []
        for queue_item in queue_items:
            # Get generated content if it exists
            gen_content = (
                db.query(GeneratedContent)
                .filter(GeneratedContent.content_queue_id == queue_item.id)
                .first()
            )

            # Determine if content is edited and published
            is_edited = bool(queue_item.edited_content)
            is_published = bool(queue_item.platform_post_id or queue_item.published_at)

            items.append(GeneratedContentItem(
                id=str(gen_content.id) if gen_content else str(queue_item.id),
                output_id=str(queue_item.output_id),
                content_queue_id=str(queue_item.id),
                platform=queue_item.platform or "twitter",
                content_text=gen_content.content_text if gen_content else None,
                edited_content=queue_item.edited_content,
                hashtags=gen_content.hashtags if gen_content else [],
                character_count=gen_content.character_count if gen_content else 0,
                edited_character_count=len(queue_item.edited_content) if queue_item.edited_content else 0,
                is_edited=is_edited,
                is_published=is_published,
                generated_at=gen_content.generated_at if gen_content else queue_item.created_at,
                status=queue_item.status,
                error_message=queue_item.error_message,
                event_title=queue_item.output.event.title if queue_item.output and queue_item.output.event else None,
                event_source=queue_item.output.event.source if queue_item.output and queue_item.output.event else None
            ))

        return GeneratedContentResponse(items=items, total=total)


@router.put("/edit/{content_queue_id}", response_model=EditContentResponse)
async def edit_content(content_queue_id: str, request: EditContentRequest):
    """
    Edit generated content before publishing.

    Validates:
    - Content length (≤280 chars)
    - Forbidden phrases
    - Not already published

    Args:
        content_queue_id: The content queue ID
        request: EditContentRequest with edited_content

    Returns:
        EditContentResponse with updated content details
    """
    with get_db_session() as db:
        try:
            content_uuid = UUID(content_queue_id)

            # 1. Fetch content queue item
            queue_item = db.query(ContentQueue).filter(ContentQueue.id == content_uuid).first()

            if not queue_item:
                raise HTTPException(status_code=404, detail="Content not found")

            # 2. Check if already published
            if queue_item.platform_post_id or queue_item.published_at:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "already_published",
                        "message": "Cannot edit published content"
                    }
                )

            # 3. Validate edited content
            validation = ContentValidator.validate_twitter_content(request.edited_content)

            if not validation.is_valid:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "validation_failed",
                        "issues": [issue.dict() for issue in validation.issues]
                    }
                )

            # 4. Save edited content
            queue_item.edited_content = request.edited_content
            queue_item.updated_at = datetime.utcnow()
            db.commit()

            # 5. Get the generated content for content_text
            gen_content = (
                db.query(GeneratedContent)
                .filter(GeneratedContent.content_queue_id == queue_item.id)
                .first()
            )

            return EditContentResponse(
                id=str(queue_item.id),  # Convert UUID to string
                content_text=gen_content.content_text if gen_content else "",
                edited_content=queue_item.edited_content,
                is_edited=True,
                edited_character_count=len(queue_item.edited_content)
            )

        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid content queue ID format")
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to edit content: {str(e)}"
            )


@router.put("/publish/{content_queue_id}")
async def mark_as_published(content_queue_id: str):
    """
    Manually mark content as published.

    Sets status to 'published' and records published_at timestamp.

    Args:
        content_queue_id: The content queue ID

    Returns:
        Success response with published_at timestamp
    """
    with get_db_session() as db:
        try:
            content_uuid = UUID(content_queue_id)

            # Fetch queue item
            queue_item = db.query(ContentQueue).filter(ContentQueue.id == content_uuid).first()

            if not queue_item:
                raise HTTPException(status_code=404, detail="Content not found")

            # Validate status
            if queue_item.status != "ready_to_schedule":
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot publish content with status '{queue_item.status}'. Only 'ready_to_schedule' content can be published."
                )

            # Update status and timestamp
            queue_item.status = "published"
            queue_item.published_at = datetime.utcnow()
            queue_item.updated_at = datetime.utcnow()
            db.commit()

            return {
                "success": True,
                "published_at": queue_item.published_at,
                "content_queue_id": str(queue_item.id)
            }

        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid content queue ID format")
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to mark content as published: {str(e)}"
            )


@router.delete("/delete-generated/{generated_id}")
async def delete_generated_content(generated_id: str):
    """
    Delete generated content and its queue entry.

    This removes the GeneratedContent and ContentQueue records, but keeps
    the Output and Evaluation intact.
    """
    with get_db_session() as db:
        try:
            generated_uuid = UUID(generated_id)

            # Try to find by generated_content id first
            gen_content = db.query(GeneratedContent).filter(GeneratedContent.id == generated_uuid).first()

            if gen_content:
                # Get queue item
                queue_item = db.query(ContentQueue).filter(ContentQueue.id == gen_content.content_queue_id).first()

                # Delete generated content
                db.delete(gen_content)

                # Delete queue item if it exists
                if queue_item:
                    db.delete(queue_item)

                db.commit()
                return {
                    "success": True,
                    "message": f"Generated content {generated_id} deleted successfully"
                }
            else:
                # Maybe it's a queue_id (for pending items that don't have generated content yet)
                queue_item = db.query(ContentQueue).filter(ContentQueue.id == generated_uuid).first()

                if queue_item:
                    db.delete(queue_item)
                    db.commit()
                    return {
                        "success": True,
                        "message": f"Queue item {generated_id} deleted successfully"
                    }
                else:
                    raise HTTPException(status_code=404, detail=f"Content {generated_id} not found")

        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid ID format")
        except Exception as e:
            db.rollback()
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete content: {str(e)}"
            )
