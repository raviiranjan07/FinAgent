"""TwitterDirect Adapter - Direct Twitter generation from events (v2 pipeline).

Generates Twitter content directly from RSS events without going through the
400-word explanation step. Uses intent-specific prompts for better quality.

Key Features:
- Direct event → Twitter (no intermediate explanation)
- Intent-specific prompts (BREAKING_NEWS, DATA_RELEASE, DESCRIPTIVE, etc.)
- Format decision based on intent
- Saves to content_queue with pipeline_version='v2'
"""

import json
from datetime import datetime
from services.llm_service import get_twitter_llm_service
from config.twitter_prompts import (
    get_intent_specific_single_prompt,
    get_intent_specific_thread_prompt
)
from database.models import ContentQueue
from database.connection import get_db_session
from database.repository import RepositoryManager
from utils.timezone import get_ist_now


class TwitterDirectAdapter:
    """Generate Twitter content directly from events using intent-specific prompts."""

    def __init__(self):
        self.name = "TwitterDirect"
        self.llm = get_twitter_llm_service()
        self.max_tweet_length = 280

    def run(self, context):
        """
        Generate Twitter content directly from event.

        Input (from context):
        - event: Event object
        - event_type: Event classification
        - intent: Content intent (BREAKING_NEWS, DATA_RELEASE, DESCRIPTIVE, etc.)
        - db_event_id: Database event ID (from DatabaseAdapter)
        - db_output_id: (Optional) Database output ID (when called from evaluation flow)

        Output (added to context):
        - twitter_direct_content: ContentQueue object (saved to DB)
        """
        print(f"[{self.name}] Generating Twitter content directly from event...")

        event = context.event
        event_type = context.event_type
        intent = context.intent
        db_event_id = context.db_event_id
        db_output_id = getattr(context, 'db_output_id', None)  # Optional output_id

        if not event or not event_type or not intent:
            print(f"[{self.name}] Missing required context: event, event_type, or intent")
            return context

        # Skip if event type is SKIP
        if event_type == "SKIP":
            print(f"[{self.name}] Skipping SKIP event type")
            return context

        # Decide format based on intent
        format_decision = self._decide_format(event_type, intent)
        print(f"[{self.name}] Format: {format_decision['format']} - {format_decision['reason']}")

        # Generate content based on format
        if format_decision['format'] == 'SINGLE':
            content_result = self._generate_single_tweet(event, event_type, intent)
        else:
            content_result = self._generate_thread(event, event_type, intent)

        if not content_result:
            print(f"[{self.name}] Failed to generate Twitter content")
            return context

        # Save to content_queue with pipeline_version='v2'
        success = self._save_to_queue(
            event=event,
            event_type=event_type,
            intent=intent,
            format_decision=format_decision,
            content_result=content_result,
            db_event_id=db_event_id,
            db_output_id=db_output_id
        )

        if success:
            print(f"[{self.name}] Content saved to queue successfully")
        else:
            print(f"[{self.name}] Failed to save to content_queue")

        return context

    def _decide_format(self, event_type: str, intent: str) -> dict:
        """Decide SINGLE vs THREAD based on intent."""

        # THREAD intents (require explanation)
        thread_intents = ["EXPLANATORY", "POLICY"]

        if intent in thread_intents:
            return {
                "format": "THREAD",
                "reason": f"{intent} content works better in threads"
            }

        # SINGLE intents (concise updates)
        # BREAKING_NEWS, DATA_RELEASE, DESCRIPTIVE, MARKET_OPINION
        return {
            "format": "SINGLE",
            "reason": f"{intent} content works as concise tweet"
        }

    def _generate_single_tweet(self, event, event_type: str, intent: str) -> dict:
        """Generate single tweet using intent-specific prompt."""

        try:
            # Get intent-specific prompt from twitter_prompts.py
            prompt = get_intent_specific_single_prompt(
                intent=intent,
                event_title=event.title,
                poc_content=event.summary or ""
            )

            # Generate tweet
            tweet = self.llm.generate(prompt).strip()

            # Remove quotes if LLM added them
            if tweet.startswith('"') and tweet.endswith('"'):
                tweet = tweet[1:-1]
            if tweet.startswith("'") and tweet.endswith("'"):
                tweet = tweet[1:-1]

            # Enforce length limit
            if len(tweet) > self.max_tweet_length:
                print(f"[{self.name}] Tweet exceeds {self.max_tweet_length} chars, truncating")
                tweet = tweet[:277] + "..."

            print(f"[{self.name}] Single tweet generated ({len(tweet)} chars)")

            return {
                "format": "SINGLE",
                "content": tweet,
                "char_count": len(tweet)
            }

        except Exception as e:
            print(f"[{self.name}] Error generating single tweet: {e}")
            return None

    def _generate_thread(self, event, event_type: str, intent: str) -> dict:
        """Generate thread using intent-specific prompt."""

        try:
            # Get intent-specific thread prompt from twitter_prompts.py
            prompt = get_intent_specific_thread_prompt(
                intent=intent,
                event_type=event_type,
                event_title=event.title,
                poc_content=event.summary or ""
            )

            # Generate thread
            raw_output = self.llm.generate(prompt).strip()

            # Parse thread (expecting JSON array)
            try:
                thread_tweets = json.loads(raw_output)
                if not isinstance(thread_tweets, list):
                    raise ValueError("Thread output must be a JSON array")
            except json.JSONDecodeError:
                # Fallback: split by newlines if not JSON
                print(f"[{self.name}] Thread not in JSON format, splitting by lines")
                thread_tweets = [t.strip() for t in raw_output.split('\n') if t.strip()]

            # Validate and enforce length limits
            validated_tweets = []
            for i, tweet in enumerate(thread_tweets[:3]):  # Max 3 tweets
                tweet = tweet.strip()

                # Remove quotes
                if tweet.startswith('"') and tweet.endswith('"'):
                    tweet = tweet[1:-1]
                if tweet.startswith("'") and tweet.endswith("'"):
                    tweet = tweet[1:-1]

                # Enforce length
                if len(tweet) > self.max_tweet_length:
                    tweet = tweet[:277] + "..."

                validated_tweets.append(tweet)

            if not validated_tweets:
                print(f"[{self.name}] No valid tweets in thread")
                return None

            print(f"[{self.name}] Thread generated ({len(validated_tweets)} tweets)")

            return {
                "format": "THREAD",
                "content": validated_tweets,
                "thread_length": len(validated_tweets)
            }

        except Exception as e:
            print(f"[{self.name}] Error generating thread: {e}")
            return None

    def _save_to_queue(self, event, event_type: str, intent: str,
                       format_decision: dict, content_result: dict, db_event_id: str = None, db_output_id: str = None) -> bool:
        """Save generated content to content_queue with pipeline_version='v2'."""

        try:
            with get_db_session() as db:
                repo = RepositoryManager(db)

                # Prepare content_text based on format
                if format_decision['format'] == 'SINGLE':
                    content_text = content_result['content']
                else:
                    # Store thread as JSON string
                    content_text = json.dumps(content_result['content'])

                # Get model name from LLM service
                model_name = getattr(self.llm, 'model_name', 'unknown')

                # Create content queue item
                content_data = {
                    "output_id": db_output_id,  # Use output_id when available (evaluation flow)
                    "event_title": event.title,
                    "event_type": event_type,
                    "event_url": event.url,
                    "format": format_decision['format'],
                    "thread_length": content_result.get('thread_length', 1),
                    "content_text": content_text,
                    "status": 'pending_hitl',  # Content generated, pending human review
                    "hitl_required": True,  # Always require human review initially
                    "hitl_risk_level": 'MEDIUM',
                    "suggested_verdict": 'PASS',
                    "suggested_verdict_reason": 'Auto-generated content',
                    "plugin_version": 'twitter-direct-v1.0',
                    "prompt_version": f'{intent}_direct_v1.0',
                    "model_used": model_name,
                    "generation_timestamp": get_ist_now(),
                    "pipeline_version": 'v2',  # NEW: Mark as v2 pipeline
                    "source_event_id": db_event_id,  # NEW: Link directly to event
                    "generation_intent": intent,  # NEW: Store intent used for generation
                    "generation_context": {
                        'event_id': str(event.event_id) if hasattr(event, 'event_id') else str(event.id) if hasattr(event, 'id') else None,
                        'event_title': event.title,
                        'event_type': event_type,
                        'intent': intent,
                        'format': format_decision['format'],
                        'format_reason': format_decision['reason'],
                        'generated_at': datetime.now().isoformat()
                    }
                }

                # Save to database
                content_queue_item = repo.content_queue.create(content_data)
                repo.commit()

                print(f"[{self.name}] Saved to content_queue (ID: {content_queue_item.id})")
                return True

        except Exception as e:
            print(f"[{self.name}] Error saving to content_queue: {e}")
            import traceback
            traceback.print_exc()
            return False
