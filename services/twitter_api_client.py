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
from utils.timezone import get_ist_now


class TwitterAPIError(Exception):
    """Twitter API error with details."""

    def __init__(self, message: str, status_code: int = None, response_data: dict = None, retry_after: int = None, orphaned_tweet_ids: list = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        self.retry_after = retry_after  # Unix timestamp from x-rate-limit-reset header
        self.orphaned_tweet_ids = orphaned_tweet_ids or []  # Tweet IDs posted before thread failed
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
                "created_at": get_ist_now().isoformat(),
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

                print(f"[TwitterAPI] [OK] Tweet posted: {tweet_id}")

                return {
                    "id": tweet_id,
                    "text": tweet_text,
                    "created_at": get_ist_now().isoformat(),
                    "dry_run": False
                }

            elif response.status_code == 429:
                # Rate limited
                retry_after_header = response.headers.get("x-rate-limit-reset")
                retry_after_timestamp = int(retry_after_header) if retry_after_header else None
                raise TwitterAPIError(
                    f"Rate limit exceeded. Retry after: {retry_after_header}",
                    status_code=429,
                    response_data=response.json(),
                    retry_after=retry_after_timestamp
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

            print(f"[TwitterAPI] [OK] Thread posted: {thread_id} ({len(tweet_ids)} tweets)")

            return {
                "thread_id": thread_id,
                "tweet_ids": tweet_ids,
                "tweet_count": len(tweet_ids),
                "created_at": get_ist_now().isoformat(),
                "dry_run": self.dry_run
            }

        except TwitterAPIError as e:
            # If thread posting fails partway, we've already posted some tweets
            # Attach orphaned tweet IDs to the error for tracking/cleanup
            print(f"[TwitterAPI] [FAIL] Thread posting failed at tweet {len(tweet_ids)+1}")
            print(f"[TwitterAPI] Orphaned tweets: {tweet_ids}")

            # Re-raise with orphaned tweet IDs attached
            e.orphaned_tweet_ids = tweet_ids
            raise

        except Exception as e:
            # Non-TwitterAPI exception (network error, validation, etc.)
            print(f"[TwitterAPI] [FAIL] Thread posting failed at tweet {len(tweet_ids)+1}")
            print(f"[TwitterAPI] Orphaned tweets: {tweet_ids}")

            # Wrap in TwitterAPIError with orphaned tweet IDs
            raise TwitterAPIError(
                f"Thread posting failed: {str(e)}",
                orphaned_tweet_ids=tweet_ids
            )

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
                print(f"[TwitterAPI] [OK] Credentials valid (authenticated as @{username})")
                return True
            else:
                print(f"[TwitterAPI] [FAIL] Credential verification failed: {response.status_code}")
                return False

        except Exception as e:
            print(f"[TwitterAPI] [FAIL] Credential verification error: {e}")
            return False

    def delete_orphaned_tweets(self, tweet_ids: List[str]) -> Dict:
        """
        Delete orphaned tweets that were posted as part of a failed thread.

        Args:
            tweet_ids: List of tweet IDs to delete

        Returns:
            Dict with deletion results: {
                deleted: List[str],  # Successfully deleted IDs
                failed: List[str],   # Failed to delete IDs
                errors: Dict[str, str]  # Error messages by ID
            }
        """

        if not tweet_ids:
            return {"deleted": [], "failed": [], "errors": {}}

        print(f"[TwitterAPI] Deleting {len(tweet_ids)} orphaned tweet(s)...")

        deleted = []
        failed = []
        errors = {}

        for tweet_id in tweet_ids:
            try:
                if self.dry_run:
                    print(f"[TwitterAPI] DRY RUN - Would delete tweet: {tweet_id}")
                    deleted.append(tweet_id)
                    continue

                # DELETE /2/tweets/:id
                url = f"{self.BASE_URL}/tweets/{tweet_id}"
                response = self.session.delete(url, timeout=30)

                if response.status_code == 200:
                    print(f"[TwitterAPI] [OK] Deleted tweet: {tweet_id}")
                    deleted.append(tweet_id)
                else:
                    error_msg = f"HTTP {response.status_code}"
                    print(f"[TwitterAPI] [FAIL] Failed to delete tweet {tweet_id}: {error_msg}")
                    failed.append(tweet_id)
                    errors[tweet_id] = error_msg

            except Exception as e:
                print(f"[TwitterAPI] [FAIL] Error deleting tweet {tweet_id}: {e}")
                failed.append(tweet_id)
                errors[tweet_id] = str(e)

        print(f"[TwitterAPI] Deletion complete: {len(deleted)} deleted, {len(failed)} failed")

        return {
            "deleted": deleted,
            "failed": failed,
            "errors": errors
        }
