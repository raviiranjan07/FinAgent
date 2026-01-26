"""TwitterClarity Adapter - Validates Twitter content for safety and quality.

Validation Rules:
1. Length constraints (≤280 chars per tweet)
2. No advice/prediction language
3. No generic phrases (low PED)
4. Proper formatting
5. Safety guardrails

Key Difference from Main Clarity:
- Main Clarity: Validates POC content (1500 chars)
- Twitter Clarity: Validates platform-specific content (280 chars)
- Stricter enforcement for public-facing content
"""

from config.prompts import TWITTER_FORBIDDEN_PHRASES, TWITTER_ALLOWED_COMPOUNDS
from utils.forbidden_words import detect_forbidden_phrases


class TwitterClarityAdapter:
    """Validate Twitter content for safety, quality, and platform constraints."""

    # Generic phrases that signal low Perceived Edge Density
    GENERIC_PHRASES = [
        "markets are interconnected",
        "this shows how",
        "global events can impact",
        "important to note",
        "it remains to be seen",
        "time will tell",
        "markets react to",
        "investors should watch",
        "stay tuned"
    ]

    def __init__(self):
        self.name = "TwitterClarity"
        self.max_length = 280

    def run(self, context):
        """
        Validate Twitter content.

        Input (from context):
        - twitter_content: Generated content (SINGLE or THREAD)

        Output (added to context):
        - twitter_clarity_issues: List of validation issues
        - twitter_clarity_passed: Boolean
        """
        # NEW: Read from plugin namespace with fallback to legacy field
        twitter_data = context.get_plugin_data("twitter", {})
        twitter_content = twitter_data.get("content") or context.twitter_content

        if not twitter_content:
            print(f"[{self.name}] No Twitter content to validate")

            # NEW: Update plugin namespace
            context.update_plugin_data("twitter", {"clarity_issues": [], "clarity_passed": True})
            # OLD: Maintain backward compatibility
            context.twitter_clarity_issues = []
            context.twitter_clarity_passed = True
            return context

        print(f"[{self.name}] Validating Twitter content...")

        issues = []

        # Extract tweets based on format
        if twitter_content["format"] == "SINGLE":
            tweets = [twitter_content["tweet"]]
        else:  # THREAD (2-5 tweets, dynamic length)
            tweet_count = twitter_content.get("tweet_count", 3)
            tweets = []
            for i in range(1, tweet_count + 1):
                tweet_key = f"tweet{i}"
                if tweet_key in twitter_content.get("tweets", {}):
                    tweets.append(twitter_content["tweets"][tweet_key])
                else:
                    print(f"[{self.name}] Warning: Missing {tweet_key} in thread content")

        # Validate each tweet
        for idx, tweet in enumerate(tweets, 1):
            tweet_issues = self._validate_tweet(tweet, idx)
            issues.extend(tweet_issues)

        # Overall validation
        if issues:
            print(f"[{self.name}] Validation FAILED - {len(issues)} issue(s) found:")
            for issue in issues:
                print(f"  - {issue}")
            clarity_passed = False
        else:
            print(f"[{self.name}] Validation PASSED")
            clarity_passed = True

        # NEW: Update plugin namespace
        context.update_plugin_data("twitter", {"clarity_issues": issues, "clarity_passed": clarity_passed})
        # OLD: Maintain backward compatibility
        context.twitter_clarity_issues = issues
        context.twitter_clarity_passed = clarity_passed

        return context

    def _validate_tweet(self, tweet: str, tweet_num: int) -> list:
        """Validate a single tweet and return list of issues."""
        issues = []
        tweet_lower = tweet.lower()

        # 1. Length check
        if len(tweet) > self.max_length:
            issues.append(f"Tweet {tweet_num}: Exceeds {self.max_length} chars ({len(tweet)} chars)")

        # 2. Empty check
        if not tweet.strip():
            issues.append(f"Tweet {tweet_num}: Empty content")
            return issues  # No point checking further

        # 3. Forbidden phrases check (advice/prediction language)
        # Use smart detection with boundary awareness and whitelisting
        forbidden_issues = detect_forbidden_phrases(tweet)
        for phrase, context in forbidden_issues:
            issues.append(f"Tweet {tweet_num}: Contains forbidden phrase '{phrase}'")

        # 4. Generic phrases check (low PED)
        for phrase in self.GENERIC_PHRASES:
            if phrase in tweet_lower:
                issues.append(f"Tweet {tweet_num}: Contains generic phrase '{phrase}' (low insight density)")

        # 5. Certainty language check (not in forbidden list but still risky)
        certainty_phrases = ["definitely", "certainly", "guaranteed", "always", "never", "100%"]
        for phrase in certainty_phrases:
            if phrase in tweet_lower:
                issues.append(f"Tweet {tweet_num}: Contains certainty language '{phrase}'")

        return issues
