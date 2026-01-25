"""Twitter API v2 Client for posting tweets and threads.

Uses OAuth 1.0a User Context authentication for write operations.
Supports both single tweets and threaded tweets.
"""

import requests
from requests_oauthlib import OAuth1Session
from typing import List, Dict, Optional
import time
from datetime import datetime

from config.settings import (
    TWITTER_API_KEY,
    TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_TOKEN_SECRET,
    TWITTER_DRY_RUN,
    validate_twitter_credentials
)


class TwitterAPIError(Exception):
    """Twitter API error with details."""

    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(self.message)


class TwitterAPIClient:
    """Twitter API v2 client for posting tweets."""

    BASE_URL = "https://api.twitter.com/2"

    def __init__(self):
        """Initialize Twitter API client with OAuth 1.0a."""

        # Validate credentials
        if not validate_twitter_credentials():
            raise ValueError(
                "Twitter API credentials not configured. "
                "Please set TWITTER_API_KEY, TWITTER_API_SECRET, "
                "TWITTER_ACCESS_TOKEN, and TWITTER_ACCESS_TOKEN_SECRET in .env"
            )

        # Create OAuth1Session
        self.session = OAuth1Session(
            client_key=TWITTER_API_KEY,
            client_secret=TWITTER_API_SECRET,
            resource_owner_key=TWITTER_ACCESS_TOKEN,
            resource_owner_secret=TWITTER_ACCESS_TOKEN_SECRET
        )

        self.dry_run = TWITTER_DRY_RUN

        print(f"[TwitterAPI] Initialized (dry_run={self.dry_run})")

    def post_tweet(self, text: str, reply_to_id: Optional[str] = None) -> Dict:
        """
        Post a single tweet.

        Args:
            text: Tweet text (max 280 characters for Free tier)
            reply_to_id: Optional tweet ID to reply to (for threading)

        Returns:
            Dict with tweet data: {id, text, created_at}

        Raises:
            TwitterAPIError: If posting fails
        """

        if len(text) > 280:
            raise ValueError(f"Tweet exceeds 280 characters: {len(text)}")

        # Dry run mode - simulate success
        if self.dry_run:
            print(f"[TwitterAPI] DRY RUN - Would post tweet:")
            print(f"  Text: {text[:100]}...")
            print(f"  Reply to: {reply_to_id or 'None'}")

            return {
                "id": f"dry_run_{int(time.time())}",
                "text": text,
                "created_at": datetime.utcnow().isoformat(),
                "dry_run": True
            }

        # Build request payload
        payload = {"text": text}

        if reply_to_id:
            payload["reply"] = {"in_reply_to_tweet_id": reply_to_id}

        # POST to Twitter API v2
        url = f"{self.BASE_URL}/tweets"

        try:
            print(f"[TwitterAPI] Posting tweet ({len(text)} chars)...")
            response = self.session.post(url, json=payload, timeout=30)

            # Handle response
            if response.status_code == 201:
                data = response.json()
                tweet_id = data["data"]["id"]
                tweet_text = data["data"]["text"]

                print(f"[TwitterAPI] ✅ Tweet posted: {tweet_id}")

                return {
                    "id": tweet_id,
                    "text": tweet_text,
                    "created_at": datetime.utcnow().isoformat(),
                    "dry_run": False
                }

            elif response.status_code == 429:
                # Rate limited
                retry_after = response.headers.get("x-rate-limit-reset")
                raise TwitterAPIError(
                    f"Rate limit exceeded. Retry after: {retry_after}",
                    status_code=429,
                    response_data=response.json()
                )

            else:
                # Other error
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("detail", "Unknown error")

                raise TwitterAPIError(
                    f"Twitter API error: {error_msg}",
                    status_code=response.status_code,
                    response_data=error_data
                )

        except requests.exceptions.RequestException as e:
            raise TwitterAPIError(f"Network error: {str(e)}")

    def post_thread(self, tweets: List[str]) -> Dict:
        """
        Post a threaded tweet (multiple tweets in sequence).

        Args:
            tweets: List of tweet texts (each max 280 chars)

        Returns:
            Dict with thread data: {
                thread_id: str (first tweet ID),
                tweet_ids: List[str],
                tweet_count: int
            }

        Raises:
            TwitterAPIError: If posting fails
        """

        if not tweets:
            raise ValueError("No tweets provided")

        if len(tweets) > 25:
            raise ValueError(f"Thread too long: {len(tweets)} tweets (max 25)")

        # Validate all tweet lengths
        for i, text in enumerate(tweets):
            if len(text) > 280:
                raise ValueError(f"Tweet {i+1} exceeds 280 characters: {len(text)}")

        print(f"[TwitterAPI] Posting thread ({len(tweets)} tweets)...")

        tweet_ids = []
        reply_to_id = None

        try:
            for i, text in enumerate(tweets):
                print(f"[TwitterAPI] Posting tweet {i+1}/{len(tweets)}...")

                # Post tweet (replies to previous if not first)
                result = self.post_tweet(text, reply_to_id=reply_to_id)

                tweet_ids.append(result["id"])
                reply_to_id = result["id"]

                # Rate limit protection - wait between tweets
                if i < len(tweets) - 1:  # Don't wait after last tweet
                    time.sleep(1)  # 1 second between tweets

            thread_id = tweet_ids[0]

            print(f"[TwitterAPI] ✅ Thread posted: {thread_id} ({len(tweet_ids)} tweets)")

            return {
                "thread_id": thread_id,
                "tweet_ids": tweet_ids,
                "tweet_count": len(tweet_ids),
                "created_at": datetime.utcnow().isoformat(),
                "dry_run": self.dry_run
            }

        except Exception as e:
            # If thread posting fails partway, we've already posted some tweets
            # Log which tweets were posted for cleanup/tracking
            print(f"[TwitterAPI] ❌ Thread posting failed at tweet {len(tweet_ids)+1}")
            print(f"[TwitterAPI] Posted tweets: {tweet_ids}")
            raise

    def get_tweet(self, tweet_id: str) -> Dict:
        """
        Get tweet details by ID.

        Args:
            tweet_id: Twitter tweet ID

        Returns:
            Dict with tweet data
        """

        if self.dry_run:
            return {
                "id": tweet_id,
                "text": "Dry run mode - tweet not actually posted",
                "dry_run": True
            }

        url = f"{self.BASE_URL}/tweets/{tweet_id}"

        try:
            response = self.session.get(url, timeout=30)

            if response.status_code == 200:
                return response.json()["data"]
            else:
                raise TwitterAPIError(
                    f"Failed to fetch tweet: {response.status_code}",
                    status_code=response.status_code
                )

        except requests.exceptions.RequestException as e:
            raise TwitterAPIError(f"Network error: {str(e)}")

    def verify_credentials(self) -> bool:
        """
        Verify Twitter API credentials are valid.

        Returns:
            True if credentials are valid, False otherwise
        """

        if self.dry_run:
            print("[TwitterAPI] Dry run mode - skipping credential verification")
            return True

        url = f"{self.BASE_URL}/users/me"

        try:
            response = self.session.get(url, timeout=30)

            if response.status_code == 200:
                data = response.json()
                username = data["data"]["username"]
                print(f"[TwitterAPI] ✅ Credentials valid (authenticated as @{username})")
                return True
            else:
                print(f"[TwitterAPI] ❌ Credential verification failed: {response.status_code}")
                return False

        except Exception as e:
            print(f"[TwitterAPI] ❌ Credential verification error: {e}")
            return False
