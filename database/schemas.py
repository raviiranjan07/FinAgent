"""Pydantic schemas for structured data validation.

This module defines schemas for JSON fields stored in the database
to ensure data integrity and prevent malformed content.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
import json


# =============================================================================
# Twitter Content Schemas
# =============================================================================

class TwitterSingleContent(BaseModel):
    """Schema for SINGLE format Twitter content.

    Validates that a single tweet is properly formatted.
    """
    tweet: str = Field(..., min_length=1, max_length=280)

    @validator('tweet')
    def tweet_not_empty(cls, v):
        """Ensure tweet is not just whitespace."""
        if not v.strip():
            raise ValueError("Tweet cannot be empty or whitespace only")
        return v.strip()

    def to_db_format(self) -> str:
        """Convert to database storage format (plain string)."""
        return self.tweet

    @classmethod
    def from_db_format(cls, db_value: str):
        """Load from database storage format."""
        return cls(tweet=db_value)


class TwitterThreadContent(BaseModel):
    """Schema for THREAD format Twitter content.

    Validates that a thread has exactly 3 tweets, each properly formatted.
    """
    tweets: List[str] = Field(..., min_items=3, max_items=3)

    @validator('tweets')
    def validate_tweets(cls, tweets):
        """Validate each tweet in the thread."""
        if len(tweets) != 3:
            raise ValueError(f"Thread must have exactly 3 tweets, got {len(tweets)}")

        for i, tweet in enumerate(tweets, 1):
            # Check not empty
            if not tweet or not tweet.strip():
                raise ValueError(f"Tweet {i} cannot be empty")

            # Check length
            if len(tweet) > 280:
                raise ValueError(f"Tweet {i} exceeds 280 characters ({len(tweet)} chars)")

        return [t.strip() for t in tweets]

    def to_db_format(self) -> str:
        """Convert to database storage format (JSON array)."""
        return json.dumps(self.tweets)

    @classmethod
    def from_db_format(cls, db_value: str):
        """Load from database storage format."""
        tweets = json.loads(db_value)
        return cls(tweets=tweets)


class TwitterContent(BaseModel):
    """Unified schema for Twitter content (SINGLE or THREAD).

    Provides a single interface for validating and storing Twitter content.
    """
    format: str = Field(..., pattern="^(SINGLE|THREAD)$")
    content: Any  # Will be TwitterSingleContent or TwitterThreadContent

    @validator('content', pre=True, always=True)
    def validate_content(cls, v, values):
        """Validate content based on format."""
        format_type = values.get('format')

        if format_type == 'SINGLE':
            if isinstance(v, str):
                return TwitterSingleContent(tweet=v)
            elif isinstance(v, TwitterSingleContent):
                return v
            elif isinstance(v, dict) and 'tweet' in v:
                return TwitterSingleContent(**v)
            else:
                raise ValueError(f"Invalid SINGLE content: {type(v)}")

        elif format_type == 'THREAD':
            if isinstance(v, list):
                return TwitterThreadContent(tweets=v)
            elif isinstance(v, TwitterThreadContent):
                return v
            elif isinstance(v, dict) and 'tweets' in v:
                return TwitterThreadContent(**v)
            else:
                raise ValueError(f"Invalid THREAD content: {type(v)}")

        return v

    def to_db_format(self) -> str:
        """Convert to database storage format."""
        return self.content.to_db_format()

    @classmethod
    def from_db_format(cls, format_type: str, db_value: str):
        """Load from database storage format.

        Args:
            format_type: "SINGLE" or "THREAD"
            db_value: Raw string from database

        Returns:
            TwitterContent instance
        """
        if format_type == 'SINGLE':
            content = TwitterSingleContent.from_db_format(db_value)
        elif format_type == 'THREAD':
            content = TwitterThreadContent.from_db_format(db_value)
        else:
            raise ValueError(f"Unknown format: {format_type}")

        return cls(format=format_type, content=content)


# =============================================================================
# Impact Framing Schema
# =============================================================================

class ImpactFraming(BaseModel):
    """Schema for impact framing analysis (if used).

    Validates the structure of impact analysis data.
    """
    primary_angle: Optional[str] = None
    what_this_is_not: Optional[str] = None
    why_it_matters: Optional[str] = None
    reader_lens: Optional[str] = None
    discussion_hook: Optional[str] = None

    def to_db_format(self) -> str:
        """Convert to database storage format (JSON)."""
        return self.json()

    @classmethod
    def from_db_format(cls, db_value: str):
        """Load from database storage format."""
        return cls.parse_raw(db_value)


# =============================================================================
# Helper Functions
# =============================================================================

def validate_twitter_content(format_type: str, content_text: str) -> bool:
    """
    Validate Twitter content against schema.

    Args:
        format_type: "SINGLE" or "THREAD"
        content_text: Raw content from database

    Returns:
        True if valid, raises ValidationError if not
    """
    try:
        TwitterContent.from_db_format(format_type, content_text)
        return True
    except Exception as e:
        raise ValueError(f"Invalid Twitter content: {e}")


def safe_load_twitter_content(format_type: str, content_text: str) -> Optional[TwitterContent]:
    """
    Safely load Twitter content with error handling.

    Args:
        format_type: "SINGLE" or "THREAD"
        content_text: Raw content from database

    Returns:
        TwitterContent instance or None if invalid
    """
    try:
        return TwitterContent.from_db_format(format_type, content_text)
    except Exception as e:
        print(f"[Schema] Failed to parse Twitter content: {e}")
        return None
