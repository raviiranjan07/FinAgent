"""
Content validation rules shared across generation and editing.
Prevents forbidden phrases and enforces Twitter constraints.
"""

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
    def validate_twitter_content(content: str) -> ValidationResult:
        """
        Validate content for Twitter constraints and safety rules.

        Checks:
        1. Length validation (≤280 characters)
        2. Forbidden phrase detection (no investment advice)
        3. Empty content check

        Args:
            content: The content to validate

        Returns:
            ValidationResult with is_valid flag and list of issues
        """
        issues = []

        # 1. Length validation
        if len(content) > ContentValidator.TWITTER_MAX_LENGTH:
            issues.append(ValidationIssue(
                field="edited_content",
                code="too_long",
                message=f"Content exceeds {ContentValidator.TWITTER_MAX_LENGTH} characters (current: {len(content)})"
            ))

        # 2. Forbidden phrase detection
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

        # 3. Empty content check
        if not content.strip():
            issues.append(ValidationIssue(
                field="edited_content",
                code="empty_content",
                message="Content cannot be empty"
            ))

        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues
        )
