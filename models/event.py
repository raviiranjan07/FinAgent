"""Event model schema for FinAgent POC."""

from pydantic import BaseModel
from typing import Optional


class Event(BaseModel):
    """
    Structured event object for finance content processing.

    As per documentation Section 5.6 Event Object Schema.
    """
    event_id: str
    source: str
    title: str
    summary: str  # Event content/summary (renamed from raw_text)
    url: str = ""  # Original source URL
    country: str = ""  # Jurisdiction (e.g., "IN", "US")
    published_at: str = ""
