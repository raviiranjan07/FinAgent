"""RSS Ingestion Worker.

Background worker that automatically fetches and processes RSS feeds.

Features:
- APScheduler for reliable job scheduling
- FileLock to prevent duplicate worker instances
- Heartbeat file for health monitoring
- Configurable interval (default: 4 hours)
- Integrates with existing pipeline

Runs every INGESTION_INTERVAL hours and processes:
1. Fetches events from all configured RSS sources
2. Processes through adapter pipeline (embedding, dedup, classification, etc.)
3. Stores results in database
"""

import sys
import os
import time
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from filelock import FileLock, Timeout

from utils.timezone import get_ist_now

# Worker configuration - use system temp dir for cross-platform compatibility
TEMP_DIR = tempfile.gettempdir()
INGESTION_INTERVAL_HOURS = float(os.getenv("INGESTION_INTERVAL_HOURS", 4))  # Default: every 4 hours
WORKER_LOCK_FILE = os.getenv("INGESTION_LOCK_FILE", os.path.join(TEMP_DIR, "rss_ingestion_worker.lock"))
WORKER_HEARTBEAT_FILE = os.getenv("INGESTION_HEARTBEAT_FILE", os.path.join(TEMP_DIR, "rss_ingestion_worker_heartbeat.txt"))


class RSSIngestionWorker:
    """Worker that automatically fetches and processes RSS feeds."""

    def __init__(self):
        """Initialize ingestion worker."""
        self.success_count = 0
        self.failure_count = 0
        self.last_error = None
        self.events_processed = 0
        self.last_run_time = None

        print(f"[Ingestion Worker] RSS Ingestion Worker initialized")
        print(f"[Ingestion Worker] Interval: {INGESTION_INTERVAL_HOURS} hours")
        print(f"[Ingestion Worker] Lock file: {WORKER_LOCK_FILE}")
        print(f"[Ingestion Worker] Heartbeat file: {WORKER_HEARTBEAT_FILE}")

    def update_heartbeat(self, status: str = "idle"):
        """Update heartbeat file with current timestamp and stats."""
        try:
            with open(WORKER_HEARTBEAT_FILE, 'w') as f:
                f.write(f"{get_ist_now().isoformat()}\n")
                f.write(f"status: {status}\n")
                f.write(f"success_count: {self.success_count}\n")
                f.write(f"failure_count: {self.failure_count}\n")
                f.write(f"events_processed: {self.events_processed}\n")
                if self.last_run_time:
                    f.write(f"last_run_time: {self.last_run_time.isoformat()}\n")
                if self.last_error:
                    f.write(f"last_error: {self.last_error}\n")
        except Exception as e:
            print(f"[Ingestion Worker] Warning: Failed to update heartbeat: {e}")

    def run_pipeline(self):
        """Execute the RSS ingestion pipeline."""
        from run_pipeline import (
            load_processed_urls,
            create_pipeline,
            select_events_by_priority,
            process_event,
            get_category_for_source
        )

        print(f"\n{'='*70}")
        print(f"[Ingestion Worker] Starting pipeline run at {get_ist_now().strftime('%Y-%m-%d %H:%M:%S IST')}")
        print(f"{'='*70}\n")

        self.update_heartbeat("running")
        start_time = time.time()

        try:
            # Load processed URLs at startup
            load_processed_urls()

            # Create pipeline
            pipeline = create_pipeline()
            print(f"Pipeline: {' -> '.join(a.name for a in pipeline)}\n")

            # Fetch events
            events = select_events_by_priority()

            if not events:
                print("[Ingestion Worker] No new events to process")
                self.success_count += 1
                self.last_run_time = get_ist_now()
                self.update_heartbeat("idle")
                return

            # Process events
            total_processed = 0
            total_duplicates = 0
            total_skipped = 0
            hitl_required = 0

            print(f"\nProcessing {len(events)} events through pipeline...")
            print("-" * 60)

            for idx, event in enumerate(events, start=1):
                category = get_category_for_source(event.source) or "UNKNOWN"
                print(f"[{idx}/{len(events)}] [{category}] {event.source}: {event.title[:50]}...")

                context = process_event(event, pipeline)

                # Check if duplicate
                if context.dedup and context.dedup.is_duplicate:
                    total_duplicates += 1
                    print(f"  -> DUPLICATE (semantic match)")
                    continue

                # Check if skipped
                if context.event_type == "SKIP":
                    total_skipped += 1
                    print(f"  -> SKIPPED: Administrative/legal content")
                    continue

                # Successfully processed
                total_processed += 1
                print(f"  -> {context.event_type} | {context.intent}")

                if context.hitl and context.hitl.required:
                    hitl_required += 1

            # Update stats
            self.events_processed += total_processed
            self.success_count += 1
            self.last_run_time = get_ist_now()
            self.last_error = None

            # Summary
            total_time = time.time() - start_time
            print(f"\n{'='*70}")
            print(f"[Ingestion Worker] Pipeline Run Complete")
            print(f"{'='*70}")
            print(f"  Events fetched: {len(events)}")
            print(f"  Events processed: {total_processed}")
            print(f"  Duplicates skipped: {total_duplicates}")
            print(f"  Admin/legal skipped: {total_skipped}")
            print(f"  Requiring HITL: {hitl_required}")
            print(f"  Time: {total_time:.2f} seconds")
            print(f"  Next run: {(get_ist_now() + timedelta(hours=INGESTION_INTERVAL_HOURS)).strftime('%Y-%m-%d %H:%M:%S IST')}")
            print(f"{'='*70}\n")

            self.update_heartbeat("idle")

        except Exception as e:
            self.failure_count += 1
            self.last_error = str(e)
            self.update_heartbeat("error")

            print(f"\n[Ingestion Worker] ERROR: Pipeline run failed: {e}")
            import traceback
            traceback.print_exc()

    def run_scheduled(self):
        """Run worker with APScheduler (production mode)."""

        print(f"\n{'='*70}")
        print(f"[RSS INGESTION WORKER] STARTED (APScheduler)")
        print(f"{'='*70}")
        print(f"Interval: {INGESTION_INTERVAL_HOURS} hours")
        print(f"Lock file: {WORKER_LOCK_FILE}")
        print(f"Press Ctrl+C to stop")
        print(f"{'='*70}\n")

        # Initialize scheduler
        scheduler = BlockingScheduler()

        # Add job to run every INGESTION_INTERVAL_HOURS hours
        scheduler.add_job(
            self.run_pipeline,
            trigger=IntervalTrigger(hours=INGESTION_INTERVAL_HOURS),
            id='rss_ingestion',
            name='RSS Ingestion Worker',
            replace_existing=True,
            max_instances=1  # Prevent overlapping runs
        )

        # Run first batch immediately
        self.run_pipeline()

        # Start scheduler
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            print(f"\n\n{'='*70}")
            print(f"[Ingestion Worker] Shutting down...")
            print(f"{'='*70}\n")
            scheduler.shutdown()

    def run_once(self):
        """Run worker once (useful for testing or manual triggers)."""

        print(f"\n{'='*70}")
        print(f"[RSS INGESTION WORKER] Single Run Mode")
        print(f"{'='*70}\n")

        self.run_pipeline()

        print(f"\n{'='*70}")
        print(f"[Ingestion Worker] Single run complete")
        print(f"{'='*70}\n")


def main():
    """Main entry point with file lock to prevent duplicate workers."""
    global INGESTION_INTERVAL_HOURS

    import argparse

    parser = argparse.ArgumentParser(description="RSS Ingestion Worker")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (instead of continuous loop)"
    )
    parser.add_argument(
        "--no-lock",
        action="store_true",
        help="Disable file lock (dangerous - may cause duplicate workers)"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=None,
        help=f"Override ingestion interval in hours (default: {INGESTION_INTERVAL_HOURS})"
    )

    args = parser.parse_args()

    # Override interval if specified
    if args.interval:
        INGESTION_INTERVAL_HOURS = args.interval

    # Create worker
    worker = RSSIngestionWorker()

    # If running once, skip lock
    if args.once:
        worker.run_once()
        return

    # Use file lock to prevent duplicate workers
    if not args.no_lock:
        lock = FileLock(WORKER_LOCK_FILE, timeout=1)

        try:
            with lock:
                print(f"[Ingestion Worker] Acquired lock: {WORKER_LOCK_FILE}")
                worker.run_scheduled()
        except Timeout:
            print(f"\n{'='*70}")
            print(f"ERROR: Another ingestion worker instance is already running!")
            print(f"Lock file: {WORKER_LOCK_FILE}")
            print(f"\nIf you're sure no other worker is running, delete the lock file:")
            print(f"  rm {WORKER_LOCK_FILE}")
            print(f"{'='*70}\n")
            sys.exit(1)
    else:
        print(f"[Ingestion Worker] WARNING: Running without file lock (duplicate workers possible)")
        worker.run_scheduled()


if __name__ == "__main__":
    main()
