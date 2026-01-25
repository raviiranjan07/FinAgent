"""TwitterThread Adapter - Generates 2-5 tweet threads using POC data.

Key Features:
- Uses POC data directly (event_type, intent, llm_output)
- ChatGPT-style framing: Questions narratives for MARKET_MOVEMENT
- Dynamic length: LLM decides 2-5 tweets based on complexity
- Tweet 1: Hook with key insight (🧵 emoji)
- Middle tweets: Explanation, mechanism, or context
- Last tweet: Engagement with question (hashtags)
- Targets 230-270 chars per tweet (safety buffer)
"""

from services.llm_service import get_twitter_llm_service
from config.prompts import get_twitter_thread_prompt


class TwitterThreadAdapter:
    """Generate 3-tweet threads using POC data directly."""

    def __init__(self):
        self.name = "TwitterThread"
        self.llm = get_twitter_llm_service()
        self.max_length = 280
        self.target_length = 270  # Safety buffer

    def run(self, context):
        """
        Generate 2-5 tweet thread (LLM decides length).

        Input (from context):
        - event: Event object
        - event_type: Event classification from POC
        - intent: Content intent from POC
        - llm_output: POC content
        - twitter_format: Format decision

        Output (added to context):
        - twitter_content: {
            format: "THREAD",
            tweet_count: int (2-5),
            tweets: {tweet1: str, tweet2: str, ...},
            char_counts: [int, int, ...]
          }
        """
        # Only run if format is THREAD
        if not context.twitter_format or context.twitter_format.get("format") != "THREAD":
            return context

        print(f"[{self.name}] Generating dynamic-length thread (2-5 tweets)...")

        thread = self._generate_thread(
            event=context.event,
            event_type=context.event_type,
            intent=context.intent,
            poc_content=context.llm_output
        )

        if not thread:
            print(f"[{self.name}] Failed to generate thread")

            # NEW: Use plugin namespace
            context.update_plugin_data("twitter", {"content": None})
            # OLD: Maintain backward compatibility
            context.twitter_content = None
            return context

        # Enforce length limits for all tweets
        tweet_count = len(thread)
        for i in range(1, tweet_count + 1):
            tweet_key = f"tweet{i}"
            if len(thread[tweet_key]) > self.max_length:
                print(f"[{self.name}] Tweet {i} exceeds {self.max_length} chars, truncating")
                thread[tweet_key] = thread[tweet_key][:277] + "..."

        char_counts = [len(thread[f"tweet{i}"]) for i in range(1, tweet_count + 1)]
        print(f"[{self.name}] Thread generated: {tweet_count} tweets - {', '.join(map(str, char_counts))} chars")

        content = {
            "format": "THREAD",
            "tweet_count": tweet_count,
            "tweets": thread,
            "char_counts": char_counts
        }

        # NEW: Use plugin namespace
        context.update_plugin_data("twitter", {"content": content})
        # OLD: Maintain backward compatibility
        context.twitter_content = content

        return context

    def _generate_thread(self, event, event_type: str, intent: str, poc_content: str) -> dict:
        """Generate 2-5 tweet thread using LLM with ChatGPT-style framing."""

        # Use centralized prompt from config/prompts.py
        prompt = get_twitter_thread_prompt(
            event_title=event.title,
            event_type=event_type,
            intent=intent,
            poc_content=poc_content
        )

        try:
            raw = self.llm.generate(prompt).strip()

            # Parse tweets dynamically (detect 2-5 tweets)
            tweets = {}
            for i in range(1, 6):  # Try parsing up to 5 tweets
                marker = f"TWEET{i}:"
                if marker in raw:
                    start = raw.index(marker) + len(marker)
                    # Find end (next marker or end of string)
                    next_marker = f"TWEET{i+1}:"
                    if next_marker in raw:
                        end = raw.index(next_marker)
                    else:
                        end = len(raw)

                    tweet = raw[start:end].strip()

                    # Remove quotes if LLM added them
                    if tweet.startswith('"') and tweet.endswith('"'):
                        tweet = tweet[1:-1]
                    if tweet.startswith("'") and tweet.endswith("'"):
                        tweet = tweet[1:-1]

                    tweets[f"tweet{i}"] = tweet
                else:
                    # No more tweets found, stop parsing
                    break

            # Validate tweet count (2-5 tweets)
            tweet_count = len(tweets)
            if tweet_count < 2:
                print(f"[{self.name}] Error: Thread too short ({tweet_count} tweets, minimum 2)")
                return None
            if tweet_count > 5:
                print(f"[{self.name}] Warning: Thread too long ({tweet_count} tweets, truncating to 5)")
                tweets = {k: v for k, v in list(tweets.items())[:5]}

            return tweets

        except Exception as e:
            print(f"[{self.name}] Error generating thread: {e}")
            import traceback
            traceback.print_exc()
            return None
