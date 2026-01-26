"""
Data retention service for cleaning up old data.

[WARN] IMPORTANT: DO NOT USE THIS DURING PRE-MVP/MVP PHASE (First 6 months)

During MVP, we need ALL historical data for:
- Analytics (30/90 day trends)
- HITL automation training (learning from past decisions)
- Pattern recognition (need 100+ evaluations)
- Audit trail for compliance

This service should ONLY be used after MVP (6+ months), with selective retention:
- Events/Outputs/Evaluations: 90 days (for learning)
- Published content: Forever (audit + analytics)
- Analytics data: Forever (trend analysis)
- Content queue (unpublished): 30 days

See doc/MVP_PLAN.md Section E for full data retention policy.
"""

from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy import and_
from sqlalchemy.orm import Session

from database.models import Event, Output, Evaluation, ContentQueue
from database.connection import get_db_session
from utils.timezone import get_ist_now


class DataRetentionService:
    """Manages data retention and cleanup."""

    def __init__(self, retention_days: int = 10):
        """
        Initialize data retention service.

        Args:
            retention_days: Number of days to keep data (default: 10)
        """
        self.retention_days = retention_days

    def get_cutoff_date(self) -> datetime:
        """Calculate the cutoff date for data retention."""
        return get_ist_now() - timedelta(days=self.retention_days)

    def cleanup_old_data(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Delete data older than retention period.

        Args:
            dry_run: If True, only count records without deleting

        Returns:
            Dictionary with cleanup statistics
        """
        cutoff_date = self.get_cutoff_date()

        with get_db_session() as db:
            stats = {
                "cutoff_date": cutoff_date.isoformat(),
                "retention_days": self.retention_days,
                "deleted": {},
                "dry_run": dry_run
            }

            # Count/delete old events (cascade will handle related data)
            old_events_query = db.query(Event).filter(
                Event.created_at < cutoff_date
            )

            event_count = old_events_query.count()
            stats["deleted"]["events"] = event_count

            if event_count > 0:
                # Count related data before deletion
                old_event_ids = [e.id for e in old_events_query.all()]

                # Count outputs
                output_count = db.query(Output).filter(
                    Output.event_id.in_(old_event_ids)
                ).count()
                stats["deleted"]["outputs"] = output_count

                # Count evaluations
                evaluation_count = db.query(Evaluation).filter(
                    Evaluation.event_id.in_(old_event_ids)
                ).count()
                stats["deleted"]["evaluations"] = evaluation_count

                # Count content queue items
                content_queue_count = db.query(ContentQueue).filter(
                    ContentQueue.event_id.in_(old_event_ids)
                ).count()
                stats["deleted"]["content_queue"] = content_queue_count

                if not dry_run:
                    # Delete old events (cascade will delete related data)
                    old_events_query.delete(synchronize_session=False)
                    db.commit()
                    stats["message"] = f"Successfully deleted {event_count} events and related data older than {self.retention_days} days"
                else:
                    stats["message"] = f"DRY RUN: Would delete {event_count} events and related data older than {self.retention_days} days"
            else:
                stats["message"] = f"No data older than {self.retention_days} days found"

            return stats

    def get_retention_info(self) -> Dict[str, Any]:
        """Get information about current data retention status."""
        cutoff_date = self.get_cutoff_date()

        with get_db_session() as db:
            # Count data within retention period
            active_events = db.query(Event).filter(
                Event.created_at >= cutoff_date
            ).count()

            # Count data outside retention period (to be deleted)
            old_events = db.query(Event).filter(
                Event.created_at < cutoff_date
            ).count()

            # Total data
            total_events = db.query(Event).count()

            return {
                "retention_days": self.retention_days,
                "cutoff_date": cutoff_date.isoformat(),
                "active_events": active_events,
                "old_events": old_events,
                "total_events": total_events,
                "retention_percentage": round((active_events / total_events * 100) if total_events > 0 else 0, 2)
            }


def run_cleanup(retention_days: int = 10, dry_run: bool = False):
    """
    Convenience function to run data cleanup.

    Args:
        retention_days: Number of days to keep data
        dry_run: If True, only show what would be deleted

    Returns:
        Cleanup statistics
    """
    service = DataRetentionService(retention_days=retention_days)
    return service.cleanup_old_data(dry_run=dry_run)


if __name__ == "__main__":
    # Run as script for testing
    print("Data Retention Cleanup")
    print("=" * 60)

    # First, show what would be deleted (dry run)
    print("\nDRY RUN - Checking what would be deleted...")
    dry_run_stats = run_cleanup(retention_days=10, dry_run=True)
    print(f"\nCutoff Date: {dry_run_stats['cutoff_date']}")
    print(f"Events to delete: {dry_run_stats['deleted'].get('events', 0)}")
    print(f"Outputs to delete: {dry_run_stats['deleted'].get('outputs', 0)}")
    print(f"Evaluations to delete: {dry_run_stats['deleted'].get('evaluations', 0)}")
    print(f"Content queue items to delete: {dry_run_stats['deleted'].get('content_queue', 0)}")

    # Ask for confirmation
    response = input("\nProceed with actual deletion? (yes/no): ").strip().lower()

    if response == 'yes':
        print("\nRunning actual cleanup...")
        stats = run_cleanup(retention_days=10, dry_run=False)
        print(f"\n[OK] {stats['message']}")
    else:
        print("\n[FAIL] Cleanup cancelled")
