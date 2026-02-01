"""
FinAgent Pipeline - Adapter-Based Content Processing

Main entry point for the Pre-MVP system.
Orchestrates the adapter pipeline for processing finance events.
"""

import os
import sys
import time
import argparse
from datetime import datetime, timedelta

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()
import uuid
import feedparser
import requests
import urllib3

# SSL verification control (set RSS_VERIFY_SSL=false in .env to disable)
RSS_VERIFY_SSL = os.getenv("RSS_VERIFY_SSL", "true").lower() == "true"
if not RSS_VERIFY_SSL:
    # Suppress SSL warnings only if verification is disabled
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    print("⚠️  WARNING: SSL verification disabled for RSS feeds (RSS_VERIFY_SSL=false)")

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.event import Event
from adapters.context import ExecutionContext
from adapters.embedding import EmbeddingAdapter
from adapters.dedup import DeduplicationAdapter
from adapters.event_type import EventTypeAdapter
from adapters.intent import IntentAdapter
from adapters.output import ContextAdapter
from adapters.clarity import ClarityAdapter
from adapters.hitl import HITLDecisionAdapter
from adapters.logger import LoggerAdapter
from adapters.database import DatabaseAdapter
from adapters.twitter_direct import TwitterDirectAdapter
from config.settings import (
    RSS_SOURCES,
    MAX_EVENTS,
    LOG_DIR,
    SOURCE_CATEGORIES,
    get_enabled_categories,
    get_source_url,
    get_category_for_source,
    EVENTS_LOG_FILE,
)


# Ensure logs directory exists
os.makedirs(LOG_DIR, exist_ok=True)


# Global set to track processed URLs (loaded once at startup)
_PROCESSED_URLS = set()


def load_processed_urls():
    """Load all processed URLs from database or log file."""
    global _PROCESSED_URLS

    # Try database first if enabled
    db_enabled = os.getenv("DATABASE_ENABLED", "false").lower() == "true"

    if db_enabled:
        try:
            from database.connection import SessionLocal
            from database.models import Event as DBEvent

            session = SessionLocal()
            try:
                # Query all URLs from events table
                urls = session.query(DBEvent.link).filter(DBEvent.link.isnot(None)).all()
                _PROCESSED_URLS = {url[0] for url in urls if url[0]}
                print(f"Loaded {len(_PROCESSED_URLS)} URLs from database")
                return
            finally:
                session.close()
        except Exception as e:
            print(f"Database URL loading failed: {e}, falling back to log file")

    # Fallback to log file
    if os.path.exists(EVENTS_LOG_FILE):
        import json
        with open(EVENTS_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    if record.get("url"):
                        _PROCESSED_URLS.add(record["url"])
                except (json.JSONDecodeError, KeyError):
                    continue
        print(f"Loaded {len(_PROCESSED_URLS)} URLs from log file")
    else:
        print("No existing URL history found (first run)")


def is_duplicate_url(url: str) -> bool:
    """Check if URL has been processed before."""
    return url in _PROCESSED_URLS if url else False


def get_date_cutoff():
    """
    Calculate cutoff date for fetching events (2 days ago at midnight IST).

    Example: If today is Jan 24, 2026 at 3pm IST:
    - Keep: Jan 24, Jan 23, Jan 22
    - Reject: Jan 21 and older

    Returns:
        datetime: Cutoff datetime (2 days ago at 00:00:00 IST, timezone-aware)
    """
    from datetime import timezone
    # IST is UTC+5:30
    IST = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(IST)
    # Go back 2 days and set to midnight IST (timezone-aware for comparison)
    cutoff = (now - timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
    return cutoff


def is_recent_event(published_date_str: str, cutoff: datetime) -> bool:
    """
    Check if event was published within the last 2 calendar days.

    Args:
        published_date_str: Published date string from RSS feed
        cutoff: Cutoff datetime (events before this are rejected)

    Returns:
        bool: True if event is recent (within last 2 days), False otherwise
    """
    if not published_date_str:
        # No published date - assume it's recent (keep it)
        return True

    try:
        import email.utils
        published_dt = email.utils.parsedate_to_datetime(published_date_str)
        return published_dt >= cutoff
    except (ValueError, TypeError):
        # If parsing fails, assume it's recent (keep it)
        return True


def fetch_events(source_name: str, url: str, quota: int = MAX_EVENTS) -> list:
    """
    Fetch unique events from RSS feed with per-source backfill.

    Args:
        source_name: Name identifier for the source
        url: RSS feed URL
        quota: Target number of unique (non-duplicate) events to fetch

    Returns:
        List of Event objects (up to quota unique events)
    """
    # Fetch with requests first (handles SSL issues, custom headers)
    headers = {
        "User-Agent": "FinAgent/1.0 (RSS Reader)",
        "Accept": "application/rss+xml, application/xml, text/xml, */*"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30, verify=RSS_VERIFY_SSL)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
    except requests.RequestException as e:
        print(f"  ERROR: Failed to fetch feed - {e}")
        return []

    # Check for feed errors
    if feed.bozo and not feed.entries:
        print(f"  ERROR: Feed parsing failed - {feed.get('bozo_exception', 'Unknown error')}")
        return []

    # Sort entries by published date (newest first) for priority
    entries = feed.entries
    try:
        import email.utils
        entries = sorted(
            entries,
            key=lambda e: email.utils.parsedate_to_datetime(e.get("published", "")) if e.get("published") else datetime.fromtimestamp(0),
            reverse=True
        )
    except (ValueError, TypeError) as e:
        # If parsing fails, use original order (log warning for debugging)
        print(f"  WARNING: Date sorting failed ({e}), using original feed order")

    # Calculate date cutoff (2 days ago at midnight)
    date_cutoff = get_date_cutoff()

    # Fetch until we have enough unique events or exhaust the feed
    events = []
    duplicates = 0
    too_old = 0
    total_checked = 0

    for entry in entries:
        if len(events) >= quota:
            break  # Quota reached

        total_checked += 1
        event_url = entry.get("link", "")

        # Check if event is too old (older than 2 days)
        published_date = entry.get("published", "")
        if not is_recent_event(published_date, date_cutoff):
            too_old += 1
            continue  # Skip old event, keep fetching

        # Check for duplicate URL
        if is_duplicate_url(event_url):
            duplicates += 1
            continue  # Skip duplicate, keep fetching

        # Unique and recent event - add to list
        events.append(Event(
            event_id=str(uuid.uuid4()),
            source=source_name,
            title=entry.get("title", ""),
            summary=entry.get("summary", ""),
            url=event_url,
            country="",  # Could be inferred from source
            published_at=entry.get("published", "")
        ))

        # Mark URL as processed for subsequent checks in this run
        _PROCESSED_URLS.add(event_url)

    print(f"  Feed entries: {len(feed.entries)}, checked: {total_checked}, unique: {len(events)}, duplicates: {duplicates}, too old: {too_old}")
    return events


def create_pipeline(pipeline_version: str = "v1") -> list:
    """
    Create the adapter pipeline.

    Pipeline versions:
    - v1 (default): Full pipeline with 400-word explanation generation
      EmbeddingAdapter -> DeduplicationAdapter -> EventTypeAdapter -> IntentAdapter ->
      ContextAdapter -> ClarityAdapter -> HITLDecisionAdapter -> LoggerAdapter -> DatabaseAdapter

    - v2: Direct Twitter generation (bypasses 400-word explanation)
      EmbeddingAdapter -> DeduplicationAdapter -> EventTypeAdapter -> IntentAdapter ->
      TwitterDirectAdapter -> LoggerAdapter -> DatabaseAdapter

    Note: Embedding runs first, then Dedup uses embeddings for semantic similarity.
    Dedup skips duplicates early to save LLM calls.
    IntentAdapter runs BEFORE content generation so intent is available for prompts.
    DatabaseAdapter saves to PostgreSQL (disabled by default, enable when DB is running).
    """
    # Check if database is available
    db_enabled = os.getenv("DATABASE_ENABLED", "false").lower() == "true"
    print(f"Database persistence: {'ENABLED' if db_enabled else 'DISABLED'}")
    print(f"Pipeline version: {pipeline_version}")

    # Common adapters (used by both pipelines)
    common_adapters = [
        EmbeddingAdapter(),
        DeduplicationAdapter(),
        EventTypeAdapter(),
        IntentAdapter(),
    ]

    if pipeline_version == "v2":
        # v2 pipeline: Direct Twitter generation
        # DatabaseAdapter runs BEFORE TwitterDirectAdapter to save event and get db_event_id
        return common_adapters + [
            DatabaseAdapter(enabled=db_enabled),  # Saves event first
            TwitterDirectAdapter(),  # Uses db_event_id from DatabaseAdapter
            LoggerAdapter(),
        ]
    else:
        # v1 pipeline: Traditional flow (with 400-word explanation)
        return common_adapters + [
            ContextAdapter(),       # OutputAdapter - generates 400-word explanation
            # ClarityAdapter(),     # DISABLED: Collecting real data for ML training
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
    Fetch events from all sources in a category with per-source quota.

    Each source gets an equal share of the category quota. If a source has fewer
    unique events than its quota, others can still reach their full quota.

    Args:
        category_name: Name of the category
        config: Category configuration dict

    Returns:
        List of (event, published_timestamp) tuples for sorting
    """
    all_events = []
    category_quota = config["quota"]
    sources = config["sources"]
    num_sources = len(sources)

    # Calculate per-source quota (distribute evenly)
    # Add 1 to allow some flexibility
    per_source_quota = max(1, (category_quota + num_sources - 1) // num_sources)

    for source_key in sources:
        url = get_source_url(source_key)
        if not url:
            print(f"    WARNING: No URL found for source {source_key}")
            continue

        print(f"    Fetching: {source_key} (target: {per_source_quota} unique)")
        events = fetch_events(source_key, url, quota=per_source_quota)

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


def run(pipeline_version: str = "v1"):
    """
    Main Pipeline execution with per-source backfill.

    Args:
        pipeline_version: "v1" (traditional), "v2" (direct Twitter), or "both" (side-by-side)

    Deduplication and backfill are handled at the fetch level (per-source),
    so each source independently fetches until it has enough unique events.
    """
    print(f"Starting Pipeline run (Pipeline version: {pipeline_version})...\n")
    start_time = time.time()

    # Load processed URLs at startup
    load_processed_urls()

    # Handle "both" mode: run both pipelines side-by-side
    if pipeline_version == "both":
        print("Running BOTH v1 and v2 pipelines for comparison")
        print("=" * 60)

        v1_pipeline = create_pipeline("v1")
        v2_pipeline = create_pipeline("v2")

        print(f"\nv1 Pipeline: {' -> '.join(a.name for a in v1_pipeline)}")
        print(f"v2 Pipeline: {' -> '.join(a.name for a in v2_pipeline)}\n")

        # Fetch events once (shared for both pipelines)
        events = select_events_by_priority()

        # Process through both pipelines
        v1_stats = process_events_with_pipeline(events, v1_pipeline, "v1")
        v2_stats = process_events_with_pipeline(events, v2_pipeline, "v2")

        # Combined summary
        total_time = time.time() - start_time
        print("\n" + "=" * 60)
        print("COMPARISON: v1 vs v2 Pipelines")
        print("=" * 60)
        print(f"Events selected: {len(events)}")
        print(f"\nv1 (Traditional):")
        print(f"  Processed: {v1_stats['processed']}, Duplicates: {v1_stats['duplicates']}, Skipped: {v1_stats['skipped']}")
        print(f"  HITL required: {v1_stats['hitl_required']}, Clarity issues: {v1_stats['clarity_issues']}")
        print(f"\nv2 (Direct Twitter):")
        print(f"  Processed: {v2_stats['processed']}, Duplicates: {v2_stats['duplicates']}, Skipped: {v2_stats['skipped']}")
        print(f"  HITL required: {v2_stats['hitl_required']}")
        print(f"\nTotal time: {total_time:.2f} seconds")
        print("=" * 60)
        print("Next step: Review content_queue in dashboard to compare v1 vs v2 outputs")
        print("=" * 60)
        return

    # Single pipeline mode (v1 or v2)
    pipeline = create_pipeline(pipeline_version)
    print(f"Pipeline: {' -> '.join(a.name for a in pipeline)}\n")

    # Fetch events
    events = select_events_by_priority()

    # Process events
    stats = process_events_with_pipeline(events, pipeline, pipeline_version)

    # Summary
    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"Pipeline Run Complete ({pipeline_version})")
    print("=" * 60)
    print(f"Events selected (unique URLs): {len(events)}")
    print(f"Events successfully processed: {stats['processed']}")
    print(f"Semantic duplicates skipped: {stats['duplicates']}")
    print(f"Admin/legal skipped: {stats['skipped']}")
    if pipeline_version == "v1":
        print(f"Total clarity issues: {stats['clarity_issues']}")
    print(f"Events requiring HITL: {stats['hitl_required']}")
    print(f"Total time: {total_time:.2f} seconds")


def process_events_with_pipeline(events: list, pipeline: list, pipeline_name: str) -> dict:
    """
    Process events through a pipeline and return statistics.

    Args:
        events: List of events to process
        pipeline: List of adapter instances
        pipeline_name: Name for logging (v1, v2, etc.)

    Returns:
        Dict with processing statistics
    """
    total_processed = 0
    total_duplicates = 0
    total_skipped = 0
    total_issues = 0
    hitl_required_count = 0

    print(f"\nProcessing {len(events)} events through {pipeline_name} pipeline...")
    print("-" * 60)

    for idx, event in enumerate(events, start=1):
        category = get_category_for_source(event.source) or "UNKNOWN"
        print(f"[{pipeline_name}][{idx}/{len(events)}] [{category}] {event.source}: {event.title[:50]}...")

        context = process_event(event, pipeline)

        # Check if duplicate (semantic duplicate, URL duplicates already filtered)
        if context.dedup and context.dedup.is_duplicate:
            total_duplicates += 1
            print(f"  -> DUPLICATE (semantic match)")
            continue

        # Check if skipped (administrative/legal)
        if context.event_type == "SKIP":
            total_skipped += 1
            print(f"  -> SKIPPED: Administrative/legal content")
            continue

        # Successfully processed
        total_processed += 1
        print(f"  -> {context.event_type} | {context.intent}")

        if hasattr(context, 'clarity_issues') and context.clarity_issues:
            total_issues += len(context.clarity_issues)
            print(f"     Clarity issues: {context.clarity_issues}")

        if context.hitl and context.hitl.required:
            hitl_required_count += 1
            print(f"     HITL: {context.hitl.risk_level} - {context.hitl.auto_action}")

    return {
        "processed": total_processed,
        "duplicates": total_duplicates,
        "skipped": total_skipped,
        "clarity_issues": total_issues,
        "hitl_required": hitl_required_count
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="FinAgent Pipeline - Process finance events with optional pipeline version selection"
    )
    parser.add_argument(
        "--pipeline",
        type=str,
        choices=["v1", "v2", "both"],
        default="v1",
        help="Pipeline version: v1 (traditional with 400-word explanation), v2 (direct Twitter generation), or both (side-by-side comparison)"
    )
    args = parser.parse_args()

    run(pipeline_version=args.pipeline)
