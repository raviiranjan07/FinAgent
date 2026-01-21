"""LoggerAdapter - Records all context data to JSONL."""

import json
import datetime
from adapters.base import BaseAdapter
from adapters.context import ExecutionContext
from config.settings import EVENTS_LOG_FILE


class LoggerAdapter(BaseAdapter):
    """
    Records all context data to JSONL format.

    As per documentation Section 4.5.6 LoggerAdapter.
    """

    name = "logger_adapter"
    version = "1.1.0"  # Updated to include dedup/embedding support
    input_keys = ["*"]  # Reads all context fields
    output_keys = ["log_record"]

    def run(self, context: ExecutionContext) -> ExecutionContext:
        """Log the complete context to JSONL file."""
        # Build the log record
        record = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "event_id": context.event.event_id,
            "source": context.event.source,
            "title": context.event.title,
            "url": context.event.url,
            "country": context.event.country,
            "published_at": context.event.published_at,
            "event_type": context.event_type,
            "intent": context.intent,
            "clarity_issues": context.clarity_issues,
            "hitl": {
                "required": context.hitl.required if context.hitl else False,
                "reasons": context.hitl.reasons if context.hitl else [],
                "risk_level": context.hitl.risk_level if context.hitl else "LOW",
                "auto_action": context.hitl.auto_action if context.hitl else "PROCEED"
            },
            "llm_output": context.llm_output,
            # Deduplication data (embedding stored for future similarity checks)
            "embedding": context.dedup.embedding if context.dedup else None
        }

        # Write to JSONL file
        with open(EVENTS_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        context.log_record = record
        return context
