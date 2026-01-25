"""TwitterSingle Adapter - Generates single 280-character tweets.

Key Features:
- Uses POC data directly (event_type, intent, llm_output)
- ChatGPT-style framing: Questions narratives instead of explaining them
- Targets 240-260 chars (leaves safety buffer)
- Maintains safety guardrails (no advice/predictions)
"""

from services.llm_service import get_twitter_llm_service
from config.prompts import get_twitter_single_prompt


class TwitterSingleAdapter:
    """Generate single Twitter posts using POC data directly."""

    def __init__(self):
        self.name = "TwitterSingle"
        self.llm = get_twitter_llm_service()
        self.max_length = 280
        self.target_length = 260  # Safety buffer

    def run(self, context):
        """
        Generate single tweet.

        Input (from context):
        - event: Event object
        - event_type: Event classification from POC
        - intent: Content intent from POC
        - llm_output: POC content
        - twitter_format: Format decision

        Output (added to context):
        - twitter_content: {
            format: "SINGLE",
            tweet: str,
            char_count: int
          }
        """
        # Only run if format is SINGLE
        if not context.twitter_format or context.twitter_format.get("format") != "SINGLE":
            return context

        print(f"[{self.name}] Generating single tweet...")

        tweet = self._generate_tweet(
            event=context.event,
            event_type=context.event_type,
            intent=context.intent,
            poc_content=context.llm_output
        )

        if not tweet:
            print(f"[{self.name}] Failed to generate tweet")

            # NEW: Use plugin namespace
            context.update_plugin_data("twitter", {"content": None})
            # OLD: Maintain backward compatibility
            context.twitter_content = None
            return context

        # Enforce length limit
        if len(tweet) > self.max_length:
            print(f"[{self.name}] Tweet exceeds {self.max_length} chars, truncating")
            tweet = tweet[:277] + "..."

        print(f"[{self.name}] Tweet generated ({len(tweet)} chars)")

        content = {
            "format": "SINGLE",
            "tweet": tweet,
            "char_count": len(tweet)
        }

        # NEW: Use plugin namespace
        context.update_plugin_data("twitter", {"content": content})
        # OLD: Maintain backward compatibility
        context.twitter_content = content

        return context

    def _generate_tweet(self, event, event_type: str, intent: str, poc_content: str) -> str:
        """Generate single tweet using LLM with ChatGPT-style framing."""

        # Use centralized prompt from config/prompts.py
        prompt = get_twitter_single_prompt(
            event_title=event.title,
            event_type=event_type,
            intent=intent,
            poc_content=poc_content
        )

        try:
            tweet = self.llm.generate(prompt).strip()

            # Remove quotes if LLM added them
            if tweet.startswith('"') and tweet.endswith('"'):
                tweet = tweet[1:-1]
            if tweet.startswith("'") and tweet.endswith("'"):
                tweet = tweet[1:-1]

            return tweet

        except Exception as e:
            print(f"[{self.name}] Error generating tweet: {e}")
            return None
