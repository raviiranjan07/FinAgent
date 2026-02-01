"""
Check content_queue to see existing v1 pipeline results.
"""

from database.connection import get_db_session
from database.models import ContentQueue
from sqlalchemy import func

with get_db_session() as db:
    # Count by pipeline version
    counts = db.query(
        ContentQueue.pipeline_version,
        func.count(ContentQueue.id).label('count')
    ).group_by(ContentQueue.pipeline_version).all()

    print("=" * 80)
    print("CONTENT QUEUE STATUS")
    print("=" * 80)
    print()

    for version, count in counts:
        print(f"{version or 'NULL'}: {count} items")

    print()
    print("=" * 80)
    print("RECENT v1 ITEMS (Last 5)")
    print("=" * 80)
    print()

    v1_items = db.query(ContentQueue).filter(
        ContentQueue.pipeline_version == 'v1'
    ).order_by(ContentQueue.created_at.desc()).limit(5).all()

    for item in v1_items:
        print(f"- {item.event_title[:70]}")
        print(f"  Format: {item.format}, Status: {item.status}")
        print(f"  Intent: {item.generation_intent or 'N/A'}")
        print()
