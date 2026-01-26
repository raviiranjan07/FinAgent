"""Twitter Publishing Worker (Enhanced).

Background worker that publishes scheduled tweets to Twitter.

Features:
- APScheduler for reliable job scheduling
- FileLock to prevent duplicate worker instances
- Heartbeat file for health monitoring
- Exponential backoff retry logic (1s, 2s, 4s)
- Processes both scheduled and failed items

Runs every 60 seconds and processes:
1. Scheduled content (status='scheduled', scheduled_for <= now + 1 min)
2. Failed content ready for retry (status='failed', retry_count < 3, backoff elapsed)
"""

import sys
import os
import time
import tempfile
from datetime import datetime, timedelta
from typing import List
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from filelock import FileLock, Timeout

from database.connection import get_db_session
from database.models import ContentQueue
from services.twitter_publishing_service import TwitterPublishingService
from config.settings import TWITTER_PUBLISHING_ENABLED
from utils.timezone import get_ist_now

# Worker configuration - use system temp dir for cross-platform compatibility
TEMP_DIR = tempfile.gettempdir()
WORKER_CHECK_INTERVAL = int(os.getenv("WORKER_CHECK_INTERVAL", 60))  # seconds
WORKER_MAX_RETRIES = int(os.getenv("WORKER_MAX_RETRIES", 3))
WORKER_LOCK_FILE = os.getenv("WORKER_LOCK_FILE", os.path.join(TEMP_DIR, "twitter_worker.lock"))
WORKER_HEARTBEAT_FILE = os.getenv("WORKER_HEARTBEAT_FILE", os.path.join(TEMP_DIR, "twitter_worker_heartbeat.txt"))


class TwitterPublishingWorker:
    """Enhanced worker that publishes scheduled tweets with retry logic."""

    def __init__(self):
        """Initialize publishing worker."""
        self.publishing_service = TwitterPublishingService()
        self.success_count = 0
        self.failure_count = 0
        self.last_error = None

        print(f"[Worker] Twitter Publishing Worker initialized")
        print(f"[Worker] Check interval: {WORKER_CHECK_INTERVAL}s")
        print(f"[Worker] Max retries: {WORKER_MAX_RETRIES}")
        print(f"[Worker] Publishing enabled: {TWITTER_PUBLISHING_ENABLED}")
        print(f"[Worker] Lock file: {WORKER_LOCK_FILE}")
        print(f"[Worker] Heartbeat file: {WORKER_HEARTBEAT_FILE}")

    def update_heartbeat(self):
        """Update heartbeat file with current timestamp."""
        try:
            with open(WORKER_HEARTBEAT_FILE, 'w') as f:
                f.write(f"{get_ist_now().isoformat()}\n")
                f.write(f"success_count: {self.success_count}\n")
                f.write(f"failure_count: {self.failure_count}\n")
                if self.last_error:
                    f.write(f"last_error: {self.last_error}\n")
        except Exception as e:
            print(f"[Worker] Warning: Failed to update heartbeat: {e}")

    def get_scheduled_items(self, db) -> List[ContentQueue]:
        """
        Get content items scheduled for publishing.

        Returns items where:
        - status = 'scheduled'
        - scheduled_for <= now + 1 minute (publish window)

        Args:
            db: Database session

        Returns:
            List of ContentQueue items ready to publish
        """
        now = get_ist_now()
        publish_window = now + timedelta(minutes=1)

        items = db.query(ContentQueue).filter(
            ContentQueue.status == 'scheduled',
            ContentQueue.scheduled_for <= publish_window
        ).order_by(
            ContentQueue.scheduled_for.asc()
        ).all()

        return items

    def get_failed_items_for_retry(self, db) -> List[ContentQueue]:
        """
        Get failed items ready for retry.

        Returns items where:
        - status = 'failed'
        - retry_count < max_retries
        - rate limit reset time has passed (if rate limited)
        - exponential backoff time has elapsed (for non-rate-limit errors)

        Exponential backoff: 1s, 2s, 4s (only for transient errors)
        Rate limit: Waits until rate_limit_reset timestamp

        Args:
            db: Database session

        Returns:
            List of ContentQueue items ready for retry
        """
        now = get_ist_now()
        retry_items = []

        # Get all failed items
        # CRITICAL: Include rate-limited items even if retry_count >= max
        # Rate limits are temporary and shouldn't count against retry limit
        failed = db.query(ContentQueue).filter(
            ContentQueue.status == 'failed'
        ).all()

        for item in failed:
            # CRITICAL: Check rate limit reset first (takes priority over backoff)
            if item.rate_limit_reset:
                if now < item.rate_limit_reset:
                    # Still rate limited - skip this item
                    hours_remaining = (item.rate_limit_reset - now).total_seconds() / 3600
                    print(f"[Worker] Skipping {str(item.id)[:8]}... - rate limited for {hours_remaining:.1f}h more")
                    continue
                else:
                    # Rate limit expired - clear it and reset retry counter for fresh start
                    print(f"[Worker] Rate limit expired for {str(item.id)[:8]}... - retrying")
                    item.rate_limit_reset = None
                    item.retry_count = 0  # Reset for fresh attempt
                    db.commit()
                    retry_items.append(item)
                    continue

            # Check if exceeded max retries (non-rate-limited items only)
            if item.retry_count >= WORKER_MAX_RETRIES:
                # Max retries exceeded - skip (will remain in failed state)
                continue

            if item.last_publish_attempt is None:
                # No attempt recorded, retry immediately
                retry_items.append(item)
                continue

            # Calculate backoff delay: 2^retry_count seconds (1s, 2s, 4s)
            backoff_seconds = 2 ** min(item.retry_count, 2)
            next_retry = item.last_publish_attempt + timedelta(seconds=backoff_seconds)

            if now >= next_retry:
                retry_items.append(item)

        return retry_items

    def publish_item(self, item: ContentQueue, db) -> bool:
        """
        Publish a single content item with retry tracking.

        Args:
            item: ContentQueue item to publish
            db: Database session

        Returns:
            True if published successfully, False otherwise
        """
        try:
            scheduled_str = item.scheduled_for.strftime('%Y-%m-%d %H:%M:%S') if item.scheduled_for else 'IMMEDIATE'
            print(f"[Worker] Publishing: {item.id}")
            print(f"  Event: {item.event_title}")
            print(f"  Format: {item.format}")
            print(f"  Scheduled: {scheduled_str}")
            print(f"  Attempts: {item.publish_attempts + 1}")
            if item.retry_count > 0:
                print(f"  Retry: {item.retry_count}/{WORKER_MAX_RETRIES}")

            # Update attempt counters BEFORE publishing
            item.publish_attempts = (item.publish_attempts or 0) + 1
            item.last_publish_attempt = get_ist_now()
            db.commit()

            # Publish
            result = self.publishing_service.publish_content(
                content_queue_id=str(item.id),
                db=db
            )

            if result["success"]:
                # Success - reset retry counter
                item.retry_count = 0
                db.commit()

                self.success_count += 1
                print(f"  [OK] Published: {result.get('tweet_id', 'N/A')}")
                return True
            else:
                # Failed - check if rate limit error
                is_rate_limit = 'Rate limit exceeded' in result.get('error', '')

                if is_rate_limit:
                    # Rate limit: Don't increment retry_count (temporary failure)
                    # rate_limit_reset already set by publishing_service
                    item.error_message = result.get('error', 'Unknown error')
                    item.status = 'failed'
                    print(f"  [WAIT] Rate limited (retry_count unchanged: {item.retry_count})")
                else:
                    # Real failure: Increment retry counter
                    item.retry_count = (item.retry_count or 0) + 1
                    item.error_message = result.get('error', 'Unknown error')
                    item.status = 'failed'
                    print(f"  [FAIL] Failed: {self.last_error}")
                    print(f"     Retry {item.retry_count}/{WORKER_MAX_RETRIES}")

                db.commit()

                self.failure_count += 1
                self.last_error = result.get('error', 'Unknown error')

                return False

        except Exception as e:
            # Exception - increment retry counter
            item.retry_count = (item.retry_count or 0) + 1
            item.error_message = str(e)
            item.status = 'failed'
            db.commit()

            self.failure_count += 1
            self.last_error = str(e)
            print(f"  [FAIL] Error: {e}")
            print(f"     Retry {item.retry_count}/{WORKER_MAX_RETRIES}")

            import traceback
            traceback.print_exc()

            return False

    def process_batch(self):
        """Process one batch of scheduled and failed content."""

        with get_db_session() as db:
            try:
                # Get scheduled items
                scheduled_items = self.get_scheduled_items(db)

                # Get failed items ready for retry
                retry_items = self.get_failed_items_for_retry(db)

                # Combine lists
                all_items = scheduled_items + retry_items

                if not all_items:
                    now_str = get_ist_now().strftime('%Y-%m-%d %H:%M:%S')
                    print(f"[Worker] No content ready to publish at {now_str}")
                    self.update_heartbeat()
                    return

                print(f"\n{'='*70}")
                print(f"[Worker] Processing batch at {get_ist_now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"  Scheduled: {len(scheduled_items)}")
                print(f"  Retries: {len(retry_items)}")
                print(f"  Total: {len(all_items)}")
                print(f"{'='*70}\n")

                # Publish each item
                batch_success = 0
                batch_fail = 0

                for item in all_items:
                    success = self.publish_item(item, db)

                    if success:
                        batch_success += 1
                    else:
                        batch_fail += 1

                    # Rate limit protection - wait between publishes
                    if len(all_items) > 1:
                        time.sleep(2)  # 2 seconds between items

                # Summary
                print(f"\n{'='*70}")
                print(f"[Worker] Batch complete:")
                print(f"  [OK] Success: {batch_success}")
                print(f"  [FAIL] Failed: {batch_fail}")
                print(f"  [STATS] Session totals: {self.success_count} success, {self.failure_count} failures")
                print(f"{'='*70}\n")

                # Update heartbeat after successful batch
                self.update_heartbeat()

            except Exception as e:
                print(f"[Worker] Error processing batch: {e}")
                self.last_error = str(e)
                self.update_heartbeat()

                import traceback
                traceback.print_exc()

    def run_scheduled(self):
        """Run worker with APScheduler (production mode)."""

        print(f"\n{'='*70}")
        print(f"[TWITTER] TWITTER PUBLISHING WORKER STARTED (APScheduler)")
        print(f"{'='*70}")
        print(f"Check interval: {WORKER_CHECK_INTERVAL}s")
        print(f"Publishing enabled: {TWITTER_PUBLISHING_ENABLED}")
        print(f"Lock file: {WORKER_LOCK_FILE}")
        print(f"Press Ctrl+C to stop")
        print(f"{'='*70}\n")

        # Initialize scheduler
        scheduler = BlockingScheduler()

        # Add job to run every WORKER_CHECK_INTERVAL seconds
        scheduler.add_job(
            self.process_batch,
            trigger=IntervalTrigger(seconds=WORKER_CHECK_INTERVAL),
            id='twitter_publishing',
            name='Twitter Publishing Worker',
            replace_existing=True,
            max_instances=1  # Prevent overlapping runs
        )

        # Run first batch immediately
        self.process_batch()

        # Start scheduler
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            print(f"\n\n{'='*70}")
            print(f"[Worker] Shutting down...")
            print(f"{'='*70}\n")
            scheduler.shutdown()

    def run_once(self):
        """Run worker once (useful for testing or manual triggers)."""

        print(f"\n{'='*70}")
        print(f"[TWITTER] TWITTER PUBLISHING WORKER (Single Run)")
        print(f"{'='*70}\n")

        self.process_batch()

        print(f"\n{'='*70}")
        print(f"[Worker] Single run complete")
        print(f"{'='*70}\n")


def main():
    """Main entry point with file lock to prevent duplicate workers."""

    import argparse

    parser = argparse.ArgumentParser(description="Twitter Publishing Worker")
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

    args = parser.parse_args()

    # Create worker
    worker = TwitterPublishingWorker()

    # If running once, skip lock
    if args.once:
        worker.run_once()
        return

    # Use file lock to prevent duplicate workers
    if not args.no_lock:
        lock = FileLock(WORKER_LOCK_FILE, timeout=1)

        try:
            with lock:
                print(f"[Worker] Acquired lock: {WORKER_LOCK_FILE}")
                worker.run_scheduled()
        except Timeout:
            print(f"\n{'='*70}")
            print(f"[FAIL] ERROR: Another worker instance is already running!")
            print(f"Lock file: {WORKER_LOCK_FILE}")
            print(f"\nIf you're sure no other worker is running, delete the lock file:")
            print(f"  rm {WORKER_LOCK_FILE}")
            print(f"{'='*70}\n")
            sys.exit(1)
    else:
        print(f"[Worker] WARNING: Running without file lock (duplicate workers possible)")
        worker.run_scheduled()


if __name__ == "__main__":
    main()
