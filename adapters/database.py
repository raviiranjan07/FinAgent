"""DatabaseAdapter - Persists pipeline results to PostgreSQL."""

from datetime import datetime
from typing import Optional

from adapters.base import BaseAdapter
from adapters.context import ExecutionContext
from database.connection import get_db_session
from database.repository import RepositoryManager


class DatabaseAdapter(BaseAdapter):
    """
    Persists pipeline results to PostgreSQL.

    Saves:
    - Event data with embedding
    - LLM output with classification
    - Creates content queue entry if HITL required

    Runs at the end of the pipeline (after or alongside LoggerAdapter).
    """

    name = "database_adapter"
    version = "1.0.0"
    input_keys = ["event", "event_type", "intent", "llm_output", "clarity_issues", "hitl", "event_embedding"]
    output_keys = ["db_event_id", "db_output_id"]

    def __init__(self, enabled: bool = True):
        """
        Initialize adapter.

        Args:
            enabled: If False, adapter becomes a no-op (for POC compatibility)
        """
        self._enabled = enabled

    def run(self, context: ExecutionContext) -> ExecutionContext:
        """Save pipeline results to database."""
        if not self._enabled:
            return context

        # Skip if duplicate (no need to save)
        if context.dedup and context.dedup.is_duplicate:
            return context

        # Skip if event type is SKIP
        if context.event_type == "SKIP":
            return context

        try:
            with get_db_session() as db:
                repo = RepositoryManager(db)

                # 1. Save Event
                event_data = {
                    "event_id": context.event.event_id,
                    "title": context.event.title,
                    "summary": context.event.summary,
                    "link": context.event.url,
                    "source": context.event.source,
                    "published_at": self._parse_datetime(context.event.published_at),
                    "fetched_at": datetime.utcnow(),
                    "embedding": context.event_embedding,
                }

                # Check if event already exists (by event_id)
                existing_event = repo.events.get_by_event_id(context.event.event_id)
                if existing_event:
                    db_event = existing_event
                else:
                    db_event = repo.events.create(event_data)

                # Store event DB ID in context
                context.db_event_id = str(db_event.id)

                # 2. Save Output (only if we have LLM output)
                if context.llm_output:
                    output_data = {
                        "event_id": db_event.id,
                        "llm_output": context.llm_output,
                        "event_type": context.event_type or "UNKNOWN",
                        "intent": context.intent or "UNKNOWN",
                        "clarity_issues": context.clarity_issues or [],
                        "hitl_required": context.hitl.required if context.hitl else False,
                        "hitl_risk_level": context.hitl.risk_level if context.hitl else None,
                        "output_embedding": context.output_embedding,
                    }

                    db_output = repo.outputs.create(output_data)
                    context.db_output_id = str(db_output.id)

                    # 3. Create ContentQueue entry if HITL required
                    if context.hitl and context.hitl.required:
                        queue_data = {
                            "event_id": db_event.id,
                            "output_id": db_output.id,
                            "status": "pending",
                        }
                        repo.content_queue.create(queue_data)

                # Commit transaction
                repo.commit()
                print(f"    [DATABASE] Saved event {context.db_event_id[:8]}... and output to DB")

        except Exception as e:
            print(f"    [DATABASE] Error saving to database: {e}")
            import traceback
            traceback.print_exc()
            # Don't raise - allow pipeline to continue even if DB fails

        return context

    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string to datetime object."""
        if not date_str:
            return None

        # Try common formats
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
            "%a, %d %b %Y %H:%M:%S %z",  # RSS format
            "%a, %d %b %Y %H:%M:%S GMT",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except (ValueError, AttributeError):
                continue

        return None
