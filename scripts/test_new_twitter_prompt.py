"""Test the new v2.0-educator Twitter prompt on sample events."""

import os
from database.connection import get_db_session
from database.models import Output, Event
from config.prompts import TWITTER_GENERATION_SINGLE
from services.llm_service import get_twitter_llm_service
from dotenv import load_dotenv

load_dotenv()


def test_twitter_generation(output_id=None, limit=3):
    """Generate Twitter content for PASS-verdict outputs using new prompt."""

    with get_db_session() as db:
        query = db.query(Output).join(Event).filter(Output.suggested_verdict == 'PASS')

        if output_id:
            outputs = [db.query(Output).filter(Output.id == output_id).first()]
        else:
            outputs = query.order_by(Event.created_at.desc()).limit(limit).all()

        if not outputs or outputs[0] is None:
            print("No PASS-verdict outputs found.")
            return

        print(f"\n{'='*80}")
        print(f"Testing v2.0-educator prompt on {len(outputs)} event(s)")
        print(f"{'='*80}\n")

        for i, output in enumerate(outputs, 1):
            print(f"\n{'─'*80}")
            print(f"TEST {i}/{len(outputs)}")
            print(f"{'─'*80}")
            print(f"Event: {output.event.title}")
            print(f"Source: {output.event.source}")
            print(f"Type: {output.event_type} | Intent: {output.intent}")
            print(f"\nPOC Content ({len(output.llm_output)} chars):")
            print(f"{output.llm_output[:300]}...\n")

            # Format the prompt
            prompt = TWITTER_GENERATION_SINGLE.format(
                event_title=output.event.title,
                poc_content=output.llm_output
            )

            # Get LLM client
            llm_service = get_twitter_llm_service()

            print("Generating Twitter content with v2.0-educator prompt...\n")

            try:
                # Generate content
                twitter_content = llm_service.generate(prompt).strip()

                print(f"{'='*80}")
                print("GENERATED TWITTER CONTENT:")
                print(f"{'='*80}")
                print(twitter_content)
                print(f"{'='*80}")
                print(f"Character count: {len(twitter_content)}")

                # Quick quality checks
                print(f"\n{'─'*80}")
                print("QUICK QUALITY CHECKS:")
                print(f"{'─'*80}")

                checks = {
                    "Length OK (<280)": len(twitter_content) <= 280,
                    "No hashtags": "#" not in twitter_content,
                    "Complete sentences (no ...)": not twitter_content.rstrip().endswith("..."),
                    "Has explanation (explained/means/is)": any(word in twitter_content.lower() for word in ["explained", "means", "is when", "is a", "is the"]),
                    "No forbidden words": not any(word in twitter_content.lower() for word in ["buy", "sell", "invest now", "guaranteed"]),
                }

                for check, passed in checks.items():
                    status = "✅ PASS" if passed else "❌ FAIL"
                    print(f"{status} - {check}")

                print()

            except Exception as e:
                print(f"❌ ERROR: {e}")
                import traceback
                traceback.print_exc()


if __name__ == "__main__":
    # Test on 3 PASS-verdict events
    test_twitter_generation(limit=3)
