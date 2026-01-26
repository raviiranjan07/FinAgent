"""Twitter Publishing Service.

High-level service for publishing tweets from content_queue to Twitter.
Handles both single tweets and threads, with error handling and retry logic.
"""

import json
from datetime import datetime
from typing import Dict, Optional
from sqlalchemy.orm import Session

from database.models import ContentQueue
from services.twitter_api_client import TwitterAPIClient, TwitterAPIError
from config.settings import TWITTER_PUBLISHING_ENABLED
from utils.timezone import get_ist_now


def parse_single_content(content: str) -> str:
    """Parse single tweet content from wrapped format.

    Handles both wrapped format {"format":"SINGLE","content":{"tweet":"..."}}
    and plain text.
    """
    try:
        parsed = json.loads(content)
        # Handle wrapped format
        if isinstance(parsed, dict) and parsed.get("content", {}).get("tweet"):
            return parsed["content"]["tweet"]
    except (json.JSONDecodeError, TypeError):
        pass
    return content


def parse_thread_content(content: str) -> list:
    """Parse thread content from wrapped format.

    Handles both wrapped format {"format":"THREAD","content":{"tweets":[...]}}
    and simple array format [...].
    """
    try:
        parsed = json.loads(content)
        # Handle wrapped format
        if isinstance(parsed, dict) and parsed.get("content", {}).get("tweets"):
            return parsed["content"]["tweets"]
        # Handle simple array format (legacy)
        if isinstance(parsed, list):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    raise ValueError("Invalid thread content format")


class TwitterPublishingService:
    """Service for publishing tweets to Twitter from content_queue."""

    def __init__(self):
        """Initialize Twitter publishing service."""
        self.client = TwitterAPIClient()
        self.enabled = TWITTER_PUBLISHING_ENABLED

        if not self.enabled:
            print("[TwitterPublishing] Service initialized but publishing is DISABLED")
            print("[TwitterPublishing] Set TWITTER_PUBLISHING_ENABLED=true in .env to enable")

    def publish_content(
        self,
        content_queue_id: str,
        db: Session
    ) -> Dict:
        """
        Publish content from content_queue to Twitter.

        Args:
            content_queue_id: UUID of content_queue item
            db: Database session

        Returns:
            Dict with publishing result: {
                success: bool,
                tweet_id: str (or thread_id for threads),
                tweet_ids: List[str] (for threads),
                published_at: str,
                error: str (if failed)
            }

        Raises:
            ValueError: If content not found or invalid
            TwitterAPIError: If Twitter API fails
        """

        # Fetch content from database
        content = db.query(ContentQueue).filter(
            ContentQueue.id == content_queue_id
        ).first()

        if not content:
            raise ValueError(f"Content not found: {content_queue_id}")

        # Check if already published
        if content.twitter_post_id:
            raise ValueError(
                f"Content already published: {content.twitter_post_id}"
            )

        # Check if publishing is enabled
        if not self.enabled and not self.client.dry_run:
            raise RuntimeError(
                "Twitter publishing is disabled. "
                "Set TWITTER_PUBLISHING_ENABLED=true in .env to enable"
            )

        print(f"\n{'='*70}")
        print(f"[TwitterPublishing] Publishing content: {content_queue_id}")
        print(f"  Format: {content.format}")
        print(f"  Event: {content.event_title}")
        print(f"{'='*70}\n")

        try:
            # Publish based on format
            if content.format == "SINGLE":
                result = self._publish_single(content)
            elif content.format == "THREAD":
                result = self._publish_thread(content)
            else:
                raise ValueError(f"Unknown format: {content.format}")

            # Update database
            content.twitter_post_id = result["tweet_id"]
            content.status = "published"
            content.published_at = get_ist_now()
            db.commit()

            print(f"\n[TwitterPublishing] ✅ Published successfully")
            print(f"  Tweet ID: {result['tweet_id']}")
            print(f"  URL: https://twitter.com/i/web/status/{result['tweet_id']}\n")

            return {
                "success": True,
                "tweet_id": result["tweet_id"],
                "tweet_ids": result.get("tweet_ids"),
                "published_at": content.published_at.isoformat(),
                "twitter_url": f"https://twitter.com/i/web/status/{result['tweet_id']}"
            }

        except TwitterAPIError as e:
            print(f"\n[TwitterPublishing] ❌ Publishing failed: {e}\n")

            # Update status to failed
            content.status = "failed"

            # Extract rate limit reset timestamp if present (429 error)
            if e.retry_after:
                # Convert Unix timestamp to IST datetime (naive, for database storage)
                from datetime import datetime
                from utils.timezone import IST
                rate_limit_reset_dt = datetime.fromtimestamp(e.retry_after, tz=IST).replace(tzinfo=None)
                content.rate_limit_reset = rate_limit_reset_dt
                print(f"[TwitterPublishing] Rate limit reset: {rate_limit_reset_dt.isoformat()}")

            # Extract orphaned tweet IDs if thread failed mid-posting
            if e.orphaned_tweet_ids:
                content.orphaned_tweet_ids = e.orphaned_tweet_ids
                print(f"[TwitterPublishing] Orphaned tweets: {e.orphaned_tweet_ids}")
                print(f"[TwitterPublishing] WARNING: {len(e.orphaned_tweet_ids)} tweet(s) posted but thread incomplete")

            db.commit()

            return {
                "success": False,
                "error": str(e),
                "orphaned_tweet_ids": e.orphaned_tweet_ids
            }

        except Exception as e:
            print(f"\n[TwitterPublishing] ❌ Publishing failed: {e}\n")

            # Update status to failed
            content.status = "failed"
            db.commit()

            return {
                "success": False,
                "error": str(e),
                "orphaned_tweet_ids": []  # Non-TwitterAPIError exceptions have no orphaned tweets
            }

    def _publish_single(self, content: ContentQueue) -> Dict:
        """
        Publish single tweet.

        Args:
            content: ContentQueue object with SINGLE format

        Returns:
            Dict with tweet_id
        """

        # Get raw content (use edited if available, else original)
        raw_content = content.edited_content or content.content_text

        # Debug: Show which content source is being used
        if content.edited_content:
            print(f"[TwitterPublishing] Using EDITED content ({len(content.edited_content)} chars)")
        else:
            print(f"[TwitterPublishing] Using ORIGINAL content ({len(content.content_text)} chars)")

        if not raw_content:
            raise ValueError("No content text to publish")

        # Parse wrapped format to get actual tweet text
        tweet_text = parse_single_content(raw_content)

        print(f"[TwitterPublishing] Posting single tweet ({len(tweet_text)} chars)...")
        print(f"[TwitterPublishing] Content preview: {tweet_text[:100]}...")

        # Post to Twitter
        result = self.client.post_tweet(tweet_text)

        return {
            "tweet_id": result["id"],
            "tweet_ids": [result["id"]]
        }

    def _publish_thread(self, content: ContentQueue) -> Dict:
        """
        Publish thread (multiple tweets).

        Args:
            content: ContentQueue object with THREAD format

        Returns:
            Dict with thread_id and tweet_ids
        """

        # Use edited_content if available, else original content_text
        # (Same logic as SINGLE format for consistency)
        content_source = content.edited_content or content.content_text

        if not content_source:
            raise ValueError("No content text to publish")

        # Parse wrapped format to get tweets array
        tweets = parse_thread_content(content_source)

        if not tweets:
            raise ValueError("Thread has no tweets")

        print(f"[TwitterPublishing] Posting thread ({len(tweets)} tweets)...")

        # Post thread to Twitter
        result = self.client.post_thread(tweets)

        return {
            "tweet_id": result["thread_id"],
            "tweet_ids": result["tweet_ids"]
        }

    def retry_failed(
        self,
        content_queue_id: str,
        db: Session,
        max_retries: int = 3
    ) -> Dict:
        """
        Retry publishing failed content.

        Args:
            content_queue_id: UUID of content_queue item
            db: Database session
            max_retries: Maximum retry attempts

        Returns:
            Dict with publishing result
        """

        content = db.query(ContentQueue).filter(
            ContentQueue.id == content_queue_id
        ).first()

        if not content:
            raise ValueError(f"Content not found: {content_queue_id}")

        if content.status != "failed":
            raise ValueError(
                f"Content status is '{content.status}', not 'failed'"
            )

        print(f"[TwitterPublishing] Retrying failed content: {content_queue_id}")

        # Reset status to ready_to_schedule for retry
        content.status = "ready_to_schedule"
        db.commit()

        # Attempt publish
        return self.publish_content(content_queue_id, db)

    def verify_published(
        self,
        content_queue_id: str,
        db: Session
    ) -> bool:
        """
        Verify that published content exists on Twitter.

        Args:
            content_queue_id: UUID of content_queue item
            db: Database session

        Returns:
            True if tweet exists on Twitter, False otherwise
        """

        content = db.query(ContentQueue).filter(
            ContentQueue.id == content_queue_id
        ).first()

        if not content or not content.twitter_post_id:
            return False

        try:
            tweet = self.client.get_tweet(content.twitter_post_id)
            return tweet is not None
        except TwitterAPIError:
            return False

    def cleanup_orphaned_tweets(
        self,
        content_queue_id: str,
        db: Session
    ) -> Dict:
        """
        Delete orphaned tweets from a failed thread.

        Args:
            content_queue_id: UUID of content_queue item with orphaned tweets
            db: Database session

        Returns:
            Dict with cleanup results: {
                success: bool,
                deleted_count: int,
                failed_count: int,
                errors: dict
            }
        """

        content = db.query(ContentQueue).filter(
            ContentQueue.id == content_queue_id
        ).first()

        if not content:
            raise ValueError(f"Content not found: {content_queue_id}")

        if not content.orphaned_tweet_ids:
            return {
                "success": True,
                "deleted_count": 0,
                "failed_count": 0,
                "message": "No orphaned tweets to clean up"
            }

        print(f"[TwitterPublishing] Cleaning up {len(content.orphaned_tweet_ids)} orphaned tweet(s)...")

        # Delete orphaned tweets via Twitter API
        result = self.client.delete_orphaned_tweets(content.orphaned_tweet_ids)

        # Update database
        if result["deleted"]:
            # Successfully deleted - clear orphaned_tweet_ids
            content.orphaned_tweet_ids = None
            db.commit()

        return {
            "success": len(result["failed"]) == 0,
            "deleted_count": len(result["deleted"]),
            "failed_count": len(result["failed"]),
            "errors": result["errors"]
        }
