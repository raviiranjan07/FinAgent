"""
Content validation rules shared across generation and editing.
Prevents forbidden phrases and enforces Twitter constraints.
"""

import json
from typing import List, Optional
from pydantic import BaseModel

# Import from existing config
from config.prompts import FORBIDDEN_PHRASES


class ValidationIssue(BaseModel):
    """Single validation issue."""
    field: str
    code: str
    message: str
    phrase: Optional[str] = None
    position: Optional[int] = None


class ValidationResult(BaseModel):
    """Result of content validation."""
    is_valid: bool
    issues: List[ValidationIssue] = []


class ContentValidator:
    """Validator for Twitter content safety and constraints."""

    TWITTER_MAX_LENGTH = 280

    @staticmethod
    def validate_twitter_content(content: str, format: str = None) -> ValidationResult:
        """
        Validate content for Twitter constraints and safety rules.

        Handles both SINGLE tweets and THREAD formats.
        Supports wrapped format: {"format": "...", "content": {...}}
        Auto-detects format if not provided.

        Checks:
        1. Length validation (≤280 characters per tweet)
        2. Forbidden phrase detection (no investment advice)
        3. Empty content check

        Args:
            content: The content to validate (wrapped JSON or plain text)
            format: Optional format hint ("SINGLE" or "THREAD")

        Returns:
            ValidationResult with is_valid flag and list of issues
        """
        # Try to parse wrapped format first
        try:
            parsed = json.loads(content)
            # Check for wrapped format: {"format": "...", "content": {...}}
            if isinstance(parsed, dict) and "format" in parsed and "content" in parsed:
                wrapped_format = parsed.get("format")
                wrapped_content = parsed.get("content", {})

                if wrapped_format == "THREAD":
                    tweets = wrapped_content.get("tweets", [])
                    return ContentValidator._validate_thread_list(tweets)
                elif wrapped_format == "SINGLE":
                    tweet = wrapped_content.get("tweet", "")
                    return ContentValidator._validate_single(tweet)

            # Legacy format: simple JSON array for threads
            if isinstance(parsed, list):
                return ContentValidator._validate_thread_list(parsed)

        except (json.JSONDecodeError, TypeError):
            pass

        # Auto-detect format if not provided
        if format == "THREAD":
            return ContentValidator._validate_thread(content)
        else:
            return ContentValidator._validate_single(content)

    @staticmethod
    def _validate_single(content: str) -> ValidationResult:
        """Validate a single tweet."""
        issues = []

        # 1. Empty content check
        if not content.strip():
            issues.append(ValidationIssue(
                field="edited_content",
                code="empty_content",
                message="Content cannot be empty"
            ))
            return ValidationResult(is_valid=False, issues=issues)

        # 2. Length validation
        if len(content) > ContentValidator.TWITTER_MAX_LENGTH:
            issues.append(ValidationIssue(
                field="edited_content",
                code="too_long",
                message=f"Content exceeds {ContentValidator.TWITTER_MAX_LENGTH} characters (current: {len(content)})"
            ))

        # 3. Forbidden phrase detection
        content_lower = content.lower()
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in content_lower:
                position = content_lower.find(phrase.lower())
                issues.append(ValidationIssue(
                    field="edited_content",
                    code="forbidden_phrase",
                    message=f"Content contains forbidden phrase: '{phrase}'",
                    phrase=phrase,
                    position=position
                ))

        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues
        )

    @staticmethod
    def _validate_thread_list(tweets: list) -> ValidationResult:
        """Validate a thread given a list of tweets directly."""
        issues = []

        # 1. Check it's a list
        if not isinstance(tweets, list):
            issues.append(ValidationIssue(
                field="edited_content",
                code="invalid_format",
                message="Thread content must be a list of tweets"
            ))
            return ValidationResult(is_valid=False, issues=issues)

        # 2. Check not empty
        if not tweets:
            issues.append(ValidationIssue(
                field="edited_content",
                code="empty_thread",
                message="Thread cannot be empty"
            ))
            return ValidationResult(is_valid=False, issues=issues)

        # 3. Validate each tweet
        for idx, tweet in enumerate(tweets, 1):
            if not isinstance(tweet, str):
                issues.append(ValidationIssue(
                    field=f"tweet_{idx}",
                    code="invalid_type",
                    message=f"Tweet {idx}: Must be a string"
                ))
                continue

            # Empty check
            if not tweet.strip():
                issues.append(ValidationIssue(
                    field=f"tweet_{idx}",
                    code="empty_tweet",
                    message=f"Tweet {idx}: Cannot be empty"
                ))
                continue

            # Length check
            if len(tweet) > ContentValidator.TWITTER_MAX_LENGTH:
                issues.append(ValidationIssue(
                    field=f"tweet_{idx}",
                    code="too_long",
                    message=f"Tweet {idx}: Exceeds {ContentValidator.TWITTER_MAX_LENGTH} characters ({len(tweet)} chars)"
                ))

            # Forbidden phrase check
            tweet_lower = tweet.lower()
            for phrase in FORBIDDEN_PHRASES:
                if phrase.lower() in tweet_lower:
                    issues.append(ValidationIssue(
                        field=f"tweet_{idx}",
                        code="forbidden_phrase",
                        message=f"Tweet {idx}: Contains forbidden phrase: '{phrase}'",
                        phrase=phrase
                    ))

        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues
        )

    @staticmethod
    def _validate_thread(content: str) -> ValidationResult:
        """Validate a thread (JSON array of tweets)."""
        # 1. Parse JSON
        try:
            tweets = json.loads(content)
        except json.JSONDecodeError as e:
            return ValidationResult(
                is_valid=False,
                issues=[ValidationIssue(
                    field="edited_content",
                    code="invalid_json",
                    message=f"Invalid thread format: {str(e)}"
                )]
            )

        # Use the list validator
        return ContentValidator._validate_thread_list(tweets)
