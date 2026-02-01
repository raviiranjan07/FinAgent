"""
Process existing events through v2 pipeline for comparison.
Takes events that were already processed by v1 and runs them through v2.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import database modules
from database.connection import get_db_session
from database.models import ContentQueue, Event as DBEvent, Output

# Import Pydantic Event model
from models.event import Event as PydanticEvent

# Direct imports to avoid __init__.py (which imports EventTypeAdapter that needs onnxruntime)
import importlib.util
spec = importlib.util.spec_from_file_location(
    "twitter_direct",
    os.path.join(os.path.dirname(__file__), "adapters", "twitter_direct.py")
)
twitter_direct_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(twitter_direct_module)
TwitterDirectAdapter = twitter_direct_module.TwitterDirectAdapter

spec = importlib.util.spec_from_file_location(
    "context",
    os.path.join(os.path.dirname(__file__), "adapters", "context.py")
)
context_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(context_module)
ExecutionContext = context_module.ExecutionContext

def get_events_with_v1_data():
    """Get events that were processed by v1 pipeline with their classification data."""
    with get_db_session() as db:
        # Get v1 content queue items that link to outputs
        v1_items = db.query(ContentQueue).filter(
            ContentQueue.pipeline_version == 'v1',
            ContentQueue.output_id.isnot(None)
        ).limit(10).all()  # Process 10 events for comparison

        event_data = []
        for item in v1_items:
            # Get the output to find the event and classification
            output = db.query(Output).filter(Output.id == item.output_id).first()
            if output:
                db_event = db.query(DBEvent).filter(DBEvent.id == output.event_id).first()
                if db_event:
                    # Convert SQLAlchemy Event to Pydantic Event
                    pydantic_event = PydanticEvent(
                        event_id=db_event.event_id,  # Use event_id field, not id
                        source=db_event.source,
                        title=db_event.title,
                        summary=db_event.summary or "",
                        url=db_event.link or "",  # Database has 'link', Pydantic has 'url'
                        country="",  # Not in database schema
                        published_at=db_event.published_at.isoformat() if db_event.published_at else ""
                    )
                    event_data.append({
                        'event': pydantic_event,
                        'db_event_id': str(db_event.id),  # Keep DB ID for saving
                        'event_type': output.event_type,
                        'intent': output.intent
                    })

        return event_data

def process_event_through_v2(event, db_event_id, event_type, intent):
    """Process a single event through v2 pipeline using existing classification."""

    # Create context
    context = ExecutionContext(event=event)

    # Run adapters
    print(f"\nProcessing: {event.title[:70]}...")

    # Use existing classification from v1
    context.event_type = event_type
    context.intent = intent
    print(f"  Event Type: {context.event_type} (from v1)")
    print(f"  Intent: {context.intent} (from v1)")

    # TwitterDirect (generate content)
    # We need to set db_event_id manually since we're not running DatabaseAdapter
    context.db_event_id = db_event_id

    twitter_adapter = TwitterDirectAdapter()
    context = twitter_adapter.run(context)

    if context.db_event_id:
        print(f"  [OK] v2 content generated and saved!")
    else:
        print(f"  [FAIL] Failed to generate v2 content")

    return context

if __name__ == "__main__":
    print("=" * 80)
    print("v2 PIPELINE - Process Existing Events")
    print("=" * 80)
    print()
    print("This script will:")
    print("1. Find events that were processed by v1")
    print("2. Reuse v1 classification (event_type, intent)")
    print("3. Generate v2 Twitter content for same events")
    print("4. Save v2 results to content_queue for comparison")
    print()

    confirm = input("Continue? (yes/no): ")

    if confirm.lower() != 'yes':
        print("Cancelled")
        sys.exit(0)

    print("\nFetching events from v1 content queue...")
    event_data = get_events_with_v1_data()

    print(f"Found {len(event_data)} events to process")
    print()

    if len(event_data) == 0:
        print("No events found. Make sure v1 pipeline has processed some events.")
        sys.exit(0)

    print("=" * 80)
    print("Processing through v2 pipeline...")
    print("=" * 80)

    for idx, data in enumerate(event_data, 1):
        print(f"\n[{idx}/{len(event_data)}]")
        process_event_through_v2(data['event'], data['db_event_id'], data['event_type'], data['intent'])

    print()
    print("=" * 80)
    print("DONE!")
    print("=" * 80)
    print()
    print("Next step: View comparison in dashboard")
    print("http://localhost:5173/generated-content")
    print()
    print("Look for:")
    print("  - Gray 'v1' badges = Traditional pipeline")
    print("  - Purple 'v2 Direct' badges = Direct pipeline")
    print()
