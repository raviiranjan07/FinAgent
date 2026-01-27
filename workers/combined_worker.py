"""Combined Worker - RSS Ingestion + Twitter Publishing.

Single process running both workers with APScheduler:
- RSS Ingestion: Every 4 hours
- Twitter Publishing: Every 60 seconds

Usage:
    python workers/combined_worker.py           # Run both continuously
    python workers/combined_worker.py --once    # Run both once
    python workers/combined_worker.py --rss-once      # Run only RSS once
    python workers/combined_worker.py --twitter-once  # Run only Twitter once
"""

import sys
import os
import tempfile
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from filelock import FileLock, Timeout

from workers.rss_ingestion_worker import RSSIngestionWorker
from workers.twitter_publishing_worker import TwitterPublishingWorker
from utils.timezone import get_ist_now

# Configuration
TEMP_DIR = tempfile.gettempdir()
RSS_INTERVAL_HOURS = int(os.getenv("INGESTION_INTERVAL_HOURS", 4))
TWITTER_INTERVAL_SECONDS = int(os.getenv("WORKER_CHECK_INTERVAL", 60))

# Lock files - Combined worker acquires ALL locks to prevent conflicts
COMBINED_LOCK_FILE = os.path.join(TEMP_DIR, "finagent_combined_worker.lock")
RSS_LOCK_FILE = os.path.join(TEMP_DIR, "rss_ingestion_worker.lock")
TWITTER_LOCK_FILE = os.path.join(TEMP_DIR, "twitter_worker.lock")
COMBINED_HEARTBEAT_FILE = os.path.join(TEMP_DIR, "finagent_combined_worker_heartbeat.txt")


class CombinedWorker:
    """Combined worker running RSS ingestion and Twitter publishing."""

    def __init__(self):
        """Initialize both workers."""
        print(f"\n{'='*70}")
        print(f"FINAGENT COMBINED WORKER")
        print(f"{'='*70}")
        print(f"RSS Ingestion interval: {RSS_INTERVAL_HOURS} hours")
        print(f"Twitter Publishing interval: {TWITTER_INTERVAL_SECONDS} seconds")
        print(f"Lock file: {COMBINED_LOCK_FILE}")
        print(f"{'='*70}\n")

        self.rss_worker = RSSIngestionWorker()
        self.twitter_worker = TwitterPublishingWorker()

    def update_heartbeat(self, last_task: str):
        """Update heartbeat file."""
        try:
            with open(COMBINED_HEARTBEAT_FILE, 'w', encoding='utf-8') as f:
                f.write(f"timestamp: {get_ist_now().isoformat()}\n")
                f.write(f"last_task: {last_task}\n")
                f.write(f"rss_interval: {RSS_INTERVAL_HOURS}h\n")
                f.write(f"twitter_interval: {TWITTER_INTERVAL_SECONDS}s\n")
        except Exception as e:
            print(f"[Combined] Warning: Failed to update heartbeat: {e}")

    def run_rss_task(self):
        """Run RSS ingestion task."""
        print(f"\n{'='*70}")
        print(f"[Combined] Running RSS Ingestion at {get_ist_now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")
        try:
            self.rss_worker.run_pipeline()
            self.update_heartbeat("rss_ingestion")
        except Exception as e:
            print(f"[Combined] RSS Ingestion error: {e}")
            import traceback
            traceback.print_exc()

    def run_twitter_task(self):
        """Run Twitter publishing task."""
        try:
            self.twitter_worker.process_batch()
            self.update_heartbeat("twitter_publishing")
        except Exception as e:
            print(f"[Combined] Twitter Publishing error: {e}")
            import traceback
            traceback.print_exc()

    def run_scheduled(self):
        """Run both workers with APScheduler."""
        print(f"\n{'='*70}")
        print(f"COMBINED WORKER STARTED (APScheduler)")
        print(f"{'='*70}")
        print(f"RSS Ingestion: Every {RSS_INTERVAL_HOURS} hours")
        print(f"Twitter Publishing: Every {TWITTER_INTERVAL_SECONDS} seconds")
        print(f"Press Ctrl+C to stop")
        print(f"{'='*70}\n")

        scheduler = BlockingScheduler()

        # RSS Ingestion job - every N hours
        scheduler.add_job(
            self.run_rss_task,
            trigger=IntervalTrigger(hours=RSS_INTERVAL_HOURS),
            id='rss_ingestion',
            name='RSS Ingestion Worker',
            replace_existing=True,
            max_instances=1
        )

        # Twitter Publishing job - every N seconds
        scheduler.add_job(
            self.run_twitter_task,
            trigger=IntervalTrigger(seconds=TWITTER_INTERVAL_SECONDS),
            id='twitter_publishing',
            name='Twitter Publishing Worker',
            replace_existing=True,
            max_instances=1
        )

        # Run initial tasks (Twitter first - quick, RSS second - slow)
        print("[Combined] Running initial Twitter publishing check...")
        self.run_twitter_task()

        print("[Combined] Running initial RSS ingestion...")
        self.run_rss_task()

        print(f"\n[Combined] Scheduler started. Waiting for next tasks...")

        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            print(f"\n\n{'='*70}")
            print(f"[Combined] Shutting down...")
            print(f"{'='*70}\n")
            scheduler.shutdown()

    def run_once(self, rss: bool = True, twitter: bool = True):
        """Run tasks once and exit."""
        print(f"\n{'='*70}")
        print(f"COMBINED WORKER (Single Run)")
        print(f"{'='*70}")
        print(f"RSS: {'Yes' if rss else 'No'}")
        print(f"Twitter: {'Yes' if twitter else 'No'}")
        print(f"{'='*70}\n")

        if rss:
            self.run_rss_task()

        if twitter:
            self.run_twitter_task()

        print(f"\n{'='*70}")
        print(f"[Combined] Single run complete")
        print(f"{'='*70}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="FinAgent Combined Worker")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run both tasks once and exit"
    )
    parser.add_argument(
        "--rss-once",
        action="store_true",
        help="Run only RSS ingestion once and exit"
    )
    parser.add_argument(
        "--twitter-once",
        action="store_true",
        help="Run only Twitter publishing once and exit"
    )
    parser.add_argument(
        "--no-lock",
        action="store_true",
        help="Disable file lock (dangerous - may cause duplicate workers)"
    )

    args = parser.parse_args()

    worker = CombinedWorker()

    # Handle --once flags (with lock check unless --no-lock)
    if args.once or args.rss_once or args.twitter_once:
        run_rss = args.once or args.rss_once
        run_twitter = args.once or args.twitter_once

        if not args.no_lock:
            # Check locks even for --once mode to prevent conflicts
            locks_to_check = []
            if run_rss:
                locks_to_check.append(("RSS", RSS_LOCK_FILE))
            if run_twitter:
                locks_to_check.append(("Twitter", TWITTER_LOCK_FILE))

            for name, lock_file in locks_to_check:
                try:
                    test_lock = FileLock(lock_file, timeout=0)
                    test_lock.acquire()
                    test_lock.release()
                except Timeout:
                    print(f"\n{'='*70}")
                    print(f"ERROR: {name} worker is already running!")
                    print(f"Lock file: {lock_file}")
                    print(f"{'='*70}\n")
                    sys.exit(1)

        worker.run_once(rss=run_rss, twitter=run_twitter)
        return

    # Run continuously with file locks
    # Acquire ALL locks to prevent standalone workers from running simultaneously
    if not args.no_lock:
        combined_lock = FileLock(COMBINED_LOCK_FILE, timeout=1)
        rss_lock = FileLock(RSS_LOCK_FILE, timeout=1)
        twitter_lock = FileLock(TWITTER_LOCK_FILE, timeout=1)

        try:
            with combined_lock:
                print(f"[Combined] Acquired lock: {COMBINED_LOCK_FILE}")
                try:
                    with rss_lock:
                        print(f"[Combined] Acquired lock: {RSS_LOCK_FILE}")
                        try:
                            with twitter_lock:
                                print(f"[Combined] Acquired lock: {TWITTER_LOCK_FILE}")
                                print(f"[Combined] All locks acquired - standalone workers blocked")
                                worker.run_scheduled()
                        except Timeout:
                            print(f"\n{'='*70}")
                            print(f"ERROR: Twitter publishing worker is already running!")
                            print(f"Lock file: {TWITTER_LOCK_FILE}")
                            print(f"\nStop the standalone worker first, or delete the lock file:")
                            print(f"  del {TWITTER_LOCK_FILE}")
                            print(f"{'='*70}\n")
                            sys.exit(1)
                except Timeout:
                    print(f"\n{'='*70}")
                    print(f"ERROR: RSS ingestion worker is already running!")
                    print(f"Lock file: {RSS_LOCK_FILE}")
                    print(f"\nStop the standalone worker first, or delete the lock file:")
                    print(f"  del {RSS_LOCK_FILE}")
                    print(f"{'='*70}\n")
                    sys.exit(1)
        except Timeout:
            print(f"\n{'='*70}")
            print(f"ERROR: Another combined worker instance is already running!")
            print(f"Lock file: {COMBINED_LOCK_FILE}")
            print(f"\nIf you're sure no other worker is running, delete the lock file:")
            print(f"  del {COMBINED_LOCK_FILE}")
            print(f"{'='*70}\n")
            sys.exit(1)
    else:
        print(f"[Combined] WARNING: Running without file lock")
        worker.run_scheduled()


if __name__ == "__main__":
    main()
