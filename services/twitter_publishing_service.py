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
            content.published_at = datetime.utcnow()
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

        except Exception as e:
            print(f"\n[TwitterPublishing] ❌ Publishing failed: {e}\n")

            # Update status to failed
            content.status = "failed"
            db.commit()

            return {
                "success": False,
                "error": str(e)
            }

    def _publish_single(self, content: ContentQueue) -> Dict:
        """
        Publish single tweet.

        Args:
            content: ContentQueue object with SINGLE format

        Returns:
            Dict with tweet_id
        """

        # Get tweet text (use edited if available, else original)
        tweet_text = content.edited_content or content.content_text

        if not tweet_text:
            raise ValueError("No content text to publish")

        print(f"[TwitterPublishing] Posting single tweet ({len(tweet_text)} chars)...")

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

        # Parse tweets from content_text (JSON array)
        try:
            tweets = json.loads(content.content_text)
        except json.JSONDecodeError:
            raise ValueError("Invalid thread content: not valid JSON")

        if not isinstance(tweets, list):
            raise ValueError("Invalid thread content: expected list of tweets")

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
