"""
Clear events table to allow v2 pipeline to re-process same RSS events.
Keeps content_queue intact so we can compare v1 vs v2 results.
"""

from database.connection import get_db_session
from database.models import Event

with get_db_session() as db:
    # Count before
    before_count = db.query(Event).count()
    print(f"Events table has {before_count} events")

    confirm = input("Clear events table? This will let v2 re-fetch from RSS. (yes/no): ")

    if confirm.lower() == 'yes':
        db.query(Event).delete()
        db.commit()

        after_count = db.query(Event).count()
        print(f"\nCleared! Events table now has {after_count} events")
        print("\nYou can now run: python scripts/run_pipeline.py --pipeline v2")
        print("This will re-fetch from RSS and process with v2 pipeline")
    else:
        print("Cancelled")
