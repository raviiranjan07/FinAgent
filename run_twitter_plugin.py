#!/usr/bin/env python
"""Twitter Plugin - Generate Twitter content from approved outputs.

Usage:
    python run_twitter_plugin.py --output-id <uuid>

This script runs the Twitter content generation pipeline:
1. FormatDecision: Decide SINGLE vs THREAD based on event_type/intent
2. TwitterSingle/TwitterThread: Generate content via LLM
3. TwitterClarity: Validate safety and formatting
4. TwitterHITL: Determine if human review needed
5. Save to content_queue table
"""

import argparse
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from uuid import UUID
from database.connection import get_db_session
from database.models import Output, Event as DBEvent, ContentQueue
from models.event import Event as EventModel
from adapters.context import ExecutionContext
from adapters.plugins.twitter import (
    FormatDecisionAdapter,
    TwitterSingleAdapter,
    TwitterThreadAdapter,
    TwitterClarityAdapter,
    TwitterHITLAdapter
)
from utils.timezone import get_ist_now
from config.settings import TWITTER_PROMPT_VERSION


def run_twitter_plugin(output_id: str) -> dict:
    """
    Run Twitter content generation pipeline for a single output.

    Args:
        output_id: UUID of the approved output

    Returns:
        dict with success status and content_queue_id
    """
    print(f"\n{'='*60}")
    print(f"[TwitterPlugin] Starting content generation for output: {output_id}")
    print(f"{'='*60}\n")

    with get_db_session() as db:
        try:
            # 1. Get output from database
            output = db.query(Output).filter(Output.id == UUID(output_id)).first()
            if not output:
                print(f"[TwitterPlugin] ERROR: Output {output_id} not found")
                return {"success": False, "error": "Output not found"}

            # 2. Get associated event
            event = db.query(DBEvent).filter(DBEvent.id == output.event_id).first()
            if not event:
                print(f"[TwitterPlugin] ERROR: Event not found for output {output_id}")
                return {"success": False, "error": "Event not found"}

            print(f"[TwitterPlugin] Event: {event.title[:50]}...")
            print(f"[TwitterPlugin] Event Type: {output.event_type}")
            print(f"[TwitterPlugin] Intent: {output.intent}")

            # 3. Check if content already exists
            existing = db.query(ContentQueue).filter(
                ContentQueue.output_id == output.id
            ).first()
            if existing:
                print(f"[TwitterPlugin] WARNING: Content already exists for this output")
                return {
                    "success": False,
                    "error": "Content already generated",
                    "content_queue_id": str(existing.id)
                }

            # 4. Create ExecutionContext
            event_model = EventModel(
                event_id=str(event.id),
                source=event.source or "",
                title=event.title or "",
                summary=event.summary or "",
                url=event.link or "",
                country="",
                published_at=event.published_at.isoformat() if event.published_at else ""
            )

            context = ExecutionContext(
                event=event_model,
                event_type=output.event_type,
                intent=output.intent,
                llm_output=output.llm_output
            )

            # 5. Run Twitter adapters pipeline
            print(f"\n[TwitterPlugin] Running adapter pipeline...")

            # Step 1: Format Decision
            format_adapter = FormatDecisionAdapter()
            context = format_adapter.run(context)

            twitter_format = context.twitter_format
            if not twitter_format:
                print(f"[TwitterPlugin] ERROR: Format decision failed")
                return {"success": False, "error": "Format decision failed"}

            format_type = twitter_format.get("format", "SINGLE")
            print(f"[TwitterPlugin] Format decided: {format_type}")

            # Step 2: Generate content based on format
            if format_type == "SINGLE":
                single_adapter = TwitterSingleAdapter()
                context = single_adapter.run(context)
            else:
                thread_adapter = TwitterThreadAdapter()
                context = thread_adapter.run(context)

            # Step 3: Clarity validation
            clarity_adapter = TwitterClarityAdapter()
            context = clarity_adapter.run(context)

            # Step 4: HITL decision
            hitl_adapter = TwitterHITLAdapter()
            context = hitl_adapter.run(context)

            # 6. Check if generation succeeded
            if not context.twitter_content:
                print(f"[TwitterPlugin] ERROR: Content generation failed")

                # Save failed entry to database
                failed_item = ContentQueue(
                    output_id=output.id,
                    event_title=event.title or "(Unknown Event)",
                    event_type=output.event_type,
                    event_url=event.link,
                    format=format_type,
                    thread_length=1,
                    content_text="",
                    status="failed",
                    error_message="Content generation failed - no content returned from LLM",
                    plugin_version=f"twitter-{TWITTER_PROMPT_VERSION}",
                    generation_timestamp=get_ist_now(),
                    created_at=get_ist_now(),
                    updated_at=get_ist_now()
                )
                db.add(failed_item)
                db.commit()

                return {"success": False, "error": "Content generation failed"}

            # 7. Prepare content for database
            if format_type == "SINGLE":
                content_text = json.dumps({
                    "format": "SINGLE",
                    "content": {
                        "tweet": context.twitter_content.get("tweet", "")
                    }
                })
                thread_length = 1
            else:  # THREAD
                tweets_dict = context.twitter_content.get("tweets", {})
                tweet_count = context.twitter_content.get("tweet_count", len(tweets_dict))
                tweets_list = [tweets_dict.get(f"tweet{i}", "") for i in range(1, tweet_count + 1)]
                content_text = json.dumps({
                    "format": "THREAD",
                    "content": {
                        "tweets": tweets_list
                    }
                })
                thread_length = len(tweets_list)

            # 8. Determine status based on HITL
            hitl_required = False
            hitl_risk_level = "LOW"
            suggested_verdict = "PASS"
            suggested_verdict_reason = None

            if context.twitter_hitl:
                if isinstance(context.twitter_hitl, dict):
                    hitl_required = context.twitter_hitl.get("required", False)
                    hitl_risk_level = context.twitter_hitl.get("risk_level", "LOW")
                    suggested_verdict = context.twitter_hitl.get("suggested_verdict", "PASS")
                    suggested_verdict_reason = context.twitter_hitl.get("suggested_verdict_reason")
                else:
                    hitl_required = context.twitter_hitl.required
                    hitl_risk_level = context.twitter_hitl.risk_level
                    suggested_verdict = context.twitter_hitl.suggested_verdict
                    suggested_verdict_reason = context.twitter_hitl.suggested_verdict_reason

            if hitl_required:
                status = "pending_hitl"
            else:
                status = "ready_to_schedule"

            # 9. Save to content_queue
            from services.llm_service import get_twitter_llm_service
            llm_service = get_twitter_llm_service()

            content_item = ContentQueue(
                output_id=output.id,
                event_title=event.title or "(Unknown Event)",
                event_type=output.event_type,
                event_url=event.link,
                format=format_type,
                thread_length=thread_length,
                content_text=content_text,
                hitl_required=hitl_required,
                hitl_risk_level=hitl_risk_level,
                suggested_verdict=suggested_verdict,
                suggested_verdict_reason=suggested_verdict_reason,
                status=status,
                plugin_version=f"twitter-{TWITTER_PROMPT_VERSION}",
                prompt_version=TWITTER_PROMPT_VERSION,
                model_used=llm_service.model_name if hasattr(llm_service, 'model_name') else "unknown",
                generation_timestamp=get_ist_now(),
                generation_context={
                    "event_type": output.event_type,
                    "intent": output.intent,
                    "format_reason": twitter_format.get("reason", ""),
                    "clarity_issues": getattr(context, 'twitter_clarity_issues', []),
                },
                created_at=get_ist_now(),
                updated_at=get_ist_now()
            )

            db.add(content_item)
            db.commit()

            print(f"\n{'='*60}")
            print(f"[TwitterPlugin] Content generated successfully!")
            print(f"[TwitterPlugin] Content Queue ID: {content_item.id}")
            print(f"[TwitterPlugin] Format: {format_type}")
            print(f"[TwitterPlugin] Thread Length: {thread_length}")
            print(f"[TwitterPlugin] Status: {status}")
            print(f"{'='*60}\n")

            return {
                "success": True,
                "content_queue_id": str(content_item.id),
                "format": format_type,
                "thread_length": thread_length,
                "status": status
            }

        except Exception as e:
            db.rollback()
            import traceback
            traceback.print_exc()
            print(f"[TwitterPlugin] ERROR: {str(e)}")
            return {"success": False, "error": str(e)}


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Generate Twitter content from an approved output"
    )
    parser.add_argument(
        "--output-id",
        required=True,
        help="UUID of the approved output to generate Twitter content for"
    )

    args = parser.parse_args()

    result = run_twitter_plugin(args.output_id)

    if result["success"]:
        print(f"\nSuccess! Content Queue ID: {result['content_queue_id']}")
        sys.exit(0)
    else:
        print(f"\nFailed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
