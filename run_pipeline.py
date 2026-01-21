"""
FinAgent Pipeline - Adapter-Based Content Processing

Main entry point for the Pre-MVP system.
Orchestrates the adapter pipeline for processing finance events.
"""

import os
import sys
import time

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()
import uuid
import feedparser
import requests
import urllib3

# Suppress SSL warnings for government sites with certificate issues
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.event import Event
from adapters.context import ExecutionContext
from adapters.embedding import EmbeddingAdapter
from adapters.dedup import DeduplicationAdapter
from adapters.event_type import EventTypeAdapter
from adapters.intent import IntentAdapter
from adapters.output import OutputAdapter
from adapters.clarity import ClarityAdapter
from adapters.hitl import HITLDecisionAdapter
from adapters.logger import LoggerAdapter
from adapters.database import DatabaseAdapter
from config.settings import (
    RSS_SOURCES,
    MAX_EVENTS,
    LOG_DIR,
    SOURCE_CATEGORIES,
    get_enabled_categories,
    get_source_url,
    get_category_for_source,
)


# Ensure logs directory exists
os.makedirs(LOG_DIR, exist_ok=True)


def fetch_events(source_name: str, url: str) -> list:
    """
    Fetch events from RSS feed.

    Args:
        source_name: Name identifier for the source
        url: RSS feed URL

    Returns:
        List of Event objects
    """
    # Fetch with requests first (handles SSL issues, custom headers)
    headers = {
        "User-Agent": "FinAgent/1.0 (RSS Reader)",
        "Accept": "application/rss+xml, application/xml, text/xml, */*"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
    except requests.RequestException as e:
        print(f"  ERROR: Failed to fetch feed - {e}")
        return []

    events = []

    # Check for feed errors
    if feed.bozo and not feed.entries:
        print(f"  ERROR: Feed parsing failed - {feed.get('bozo_exception', 'Unknown error')}")
        return events

    for entry in feed.entries[:MAX_EVENTS]:
        # Extract URL from entry
        event_url = entry.get("link", "")

        events.append(Event(
            event_id=str(uuid.uuid4()),
            source=source_name,
            title=entry.get("title", ""),
            summary=entry.get("summary", ""),
            url=event_url,
            country="",  # Could be inferred from source
            published_at=entry.get("published", "")
        ))

    print(f"  Entries found: {len(feed.entries)}, processing: {len(events)}")
    return events


def create_pipeline() -> list:
    """
    Create the adapter pipeline.

    Pipeline order:
    EmbeddingAdapter -> DeduplicationAdapter -> EventTypeAdapter -> IntentAdapter ->
    OutputAdapter -> ClarityAdapter -> HITLDecisionAdapter -> LoggerAdapter -> DatabaseAdapter

    Note: Embedding runs first, then Dedup uses embeddings for semantic similarity.
    Dedup skips duplicates early to save LLM calls.
    DatabaseAdapter saves to PostgreSQL (disabled by default, enable when DB is running).
    """
    # Check if database is available
    db_enabled = os.getenv("DATABASE_ENABLED", "false").lower() == "true"
    print(f"Database persistence: {'ENABLED' if db_enabled else 'DISABLED'}")

    return [
        EmbeddingAdapter(),
        DeduplicationAdapter(),
        EventTypeAdapter(),
        IntentAdapter(),
        OutputAdapter(),
        ClarityAdapter(),
        HITLDecisionAdapter(),
        LoggerAdapter(),
        DatabaseAdapter(enabled=db_enabled)
    ]


def process_event(event: Event, pipeline: list) -> ExecutionContext:
    """
    Process a single event through the adapter pipeline.

    Args:
        event: The event to process
        pipeline: List of adapter instances

    Returns:
        Final ExecutionContext after all adapters have run
        (or partial context if duplicate or skip detected)
    """
    context = ExecutionContext(event=event)

    for adapter in pipeline:
        context = adapter.run(context)

        # If dedup adapter found a duplicate, skip remaining adapters
        # (no need to call LLM, clarity checks, etc.)
        if context.dedup and context.dedup.is_duplicate:
            break

        # If event_type is SKIP (administrative/legal content), skip processing
        if context.event_type == "SKIP":
            break

    return context


def fetch_events_for_category(category_name: str, config: dict) -> list:
    """
    Fetch events from all sources in a category.

    Args:
        category_name: Name of the category
        config: Category configuration dict

    Returns:
        List of (event, published_timestamp) tuples for sorting
    """
    all_events = []

    for source_key in config["sources"]:
        url = get_source_url(source_key)
        if not url:
            print(f"    WARNING: No URL found for source {source_key}")
            continue

        print(f"    Fetching: {source_key}")
        events = fetch_events(source_key, url)

        # Add events with parsed timestamp for sorting
        for event in events:
            # Try to parse published_at for sorting (use fetched time as fallback)
            try:
                import email.utils
                parsed_time = email.utils.parsedate_to_datetime(event.published_at)
                timestamp = parsed_time.timestamp()
            except (ValueError, TypeError):
                timestamp = time.time()  # Fallback to current time

            all_events.append((event, timestamp))

    return all_events


def select_events_by_priority() -> list:
    """
    Select events using the priority-based category system.

    Algorithm:
    1. For each category (sorted by priority)
    2. Fetch all events from category sources
    3. Sort by published time (most recent first)
    4. Select up to quota events

    Returns:
        List of Event objects selected for processing
    """
    selected_events = []
    categories = get_enabled_categories()

    print("Source Prioritization System Active")
    print("=" * 60)

    for category_name, config in categories:
        print(f"\n[Priority {config['priority']}] {category_name} (quota: {config['quota']})")
        print(f"  Type: {config['type']}, Region: {config['region']}")

        # Fetch events from all sources in this category
        category_events = fetch_events_for_category(category_name, config)

        if not category_events:
            print(f"  No events found")
            continue

        # Sort by timestamp (most recent first)
        category_events.sort(key=lambda x: x[1], reverse=True)

        # Select up to quota events
        quota = config["quota"]
        selected = [event for event, _ in category_events[:quota]]

        print(f"  Total fetched: {len(category_events)}, selected: {len(selected)}")

        # Add category info to events for tracking
        for event in selected:
            event.country = config["region"]  # Use country field for region tracking

        selected_events.extend(selected)

    print("\n" + "=" * 60)
    print(f"Total events selected: {len(selected_events)}")
    print("=" * 60 + "\n")

    return selected_events


def run():
    """Main Pipeline execution function with priority-based event selection."""
    print("Starting Pipeline run (Adapter-Based Architecture)...\n")
    start_time = time.time()

    pipeline = create_pipeline()
    print(f"Pipeline: {' -> '.join(a.name for a in pipeline)}\n")

    # Use priority-based event selection
    events = select_events_by_priority()

    total_events = len(events)
    total_processed = 0
    total_duplicates = 0
    total_skipped = 0
    total_issues = 0
    hitl_required_count = 0

    print("Processing selected events through pipeline...")
    print("-" * 60)

    for idx, event in enumerate(events, start=1):
        category = get_category_for_source(event.source) or "UNKNOWN"
        print(f"[{idx}/{total_events}] [{category}] {event.source}: {event.title[:50]}...")

        context = process_event(event, pipeline)

        # Check if duplicate (skip reporting normal results)
        if context.dedup and context.dedup.is_duplicate:
            total_duplicates += 1
            print(f"  -> DUPLICATE (skipped)")
            continue

        # Check if skipped (administrative/legal content)
        if context.event_type == "SKIP":
            total_skipped += 1
            print(f"  -> SKIPPED: Administrative/legal content")
            continue

        # Report results for non-duplicate, non-skipped events
        total_processed += 1
        print(f"  -> {context.event_type} | {context.intent}")

        if context.clarity_issues:
            total_issues += len(context.clarity_issues)
            print(f"     Clarity issues: {context.clarity_issues}")

        if context.hitl and context.hitl.required:
            hitl_required_count += 1
            print(f"     HITL: {context.hitl.risk_level} - {context.hitl.auto_action}")

    # Summary
    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print("Pipeline Run Complete")
    print("=" * 60)
    print(f"Total events selected: {total_events}")
    print(f"Duplicates skipped: {total_duplicates}")
    print(f"Admin/legal skipped: {total_skipped}")
    print(f"Events processed: {total_processed}")
    print(f"Total clarity issues: {total_issues}")
    print(f"Events requiring HITL: {hitl_required_count}")
    print(f"Total time: {total_time:.2f} seconds")


if __name__ == "__main__":
    run()
