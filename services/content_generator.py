"""Content generator service for transforming raw LLM output into platform-specific format."""

import re
from typing import List, Dict, Optional, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session

from database.models import Output, ContentQueue, GeneratedContent
from database.connection import get_db_session
from services.llm_service import LLMService, get_twitter_llm_service
from config.prompts import (
    get_twitter_single_prompt,
    TWITTER_FORBIDDEN_PHRASES,
    TWITTER_ALLOWED_COMPOUNDS
)


class ContentGeneratorService:
    """
    Transforms raw LLM output into platform-specific format.

    Currently supports:
    - Twitter (single posts only, no threads for MVP)
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        Initialize content generator.

        Args:
            llm_service: LLM service instance (uses Twitter LLM config if not provided)
        """
        self.llm = llm_service or get_twitter_llm_service()

    def generate_twitter_content(
        self,
        output: Output,
        content_queue_id: UUID,
        db: Session
    ) -> GeneratedContent:
        """
        Convert raw LLM output (200-400 words) → Twitter format (≤280 chars).

        Args:
            output: Output object with raw LLM content
            content_queue_id: ID of content queue entry
            db: Database session

        Returns:
            GeneratedContent object with Twitter-formatted text

        Raises:
            ValueError: If generated content fails validation
            Exception: If LLM generation fails
        """
        # Build the prompt using centralized ChatGPT-style framing
        prompt = get_twitter_single_prompt(
            event_title=output.event.title if output.event else "Finance Event",
            event_type=output.event_type,
            intent=output.intent,
            poc_content=output.llm_output
        )

        print(f"    Generating Twitter content for output {output.id}...")

        # Retry logic with feedback for validation failures
        max_retries = 3
        twitter_text = None
        errors = []  # Initialize to avoid UnboundLocalError

        for attempt in range(max_retries):
            try:
                # Generate content
                if attempt == 0 or not errors:
                    # First attempt or previous attempt had LLM error (not validation error)
                    generation_prompt = prompt
                else:
                    # Retry with feedback about validation errors
                    generation_prompt = f"""{prompt}

IMPORTANT CORRECTION NEEDED:
Your previous attempt had these issues:
{chr(10).join(f"- {error}" for error in errors)}

Previous attempt was: {twitter_text}

Please generate a corrected version that fixes these issues while maintaining the engaging, educational tone."""

                twitter_text = self.llm.generate(generation_prompt)
                twitter_text = twitter_text.strip()

                # Clean reasoning tokens (some models add <think>, character counts, etc.)
                twitter_text = self._clean_reasoning_tokens(twitter_text)

                # Validate
                is_valid, errors = self.validate_twitter_format(twitter_text)

                if is_valid:
                    # Success!
                    if attempt > 0:
                        print(f"    ✓ Validation passed on retry {attempt + 1}")
                    break
                else:
                    # Check if only issue is character count and it's close to limit
                    char_count_only = all("Character count" in e for e in errors)
                    current_length = len(twitter_text)

                    # If within 10% of limit (280-308 chars) and only char count issue, try smart truncation
                    if char_count_only and 280 < current_length <= 308 and attempt == max_retries - 1:
                        print(f"    ⚠️ Close to limit ({current_length} chars) - attempting smart truncation")
                        twitter_text = self._smart_truncate(twitter_text, max_length=280)

                        # Re-validate after truncation
                        is_valid, errors = self.validate_twitter_format(twitter_text)
                        if is_valid:
                            print(f"    ✓ Smart truncation successful ({len(twitter_text)} chars)")
                            break
                        else:
                            print(f"    ✗ Truncation failed validation: {', '.join(errors)}")

                    # Validation failed
                    error_msg = f"Generated Twitter content failed validation: {', '.join(errors)}"
                    print(f"    Attempt {attempt + 1}/{max_retries}: {error_msg}")
                    print(f"    Generated text ({len(twitter_text)} chars): {twitter_text}")

                    if attempt == max_retries - 1:
                        # Final attempt failed
                        raise ValueError(f"Failed after {max_retries} attempts: {error_msg}")

            except Exception as e:
                if "Failed after" in str(e):
                    # Re-raise our own validation error
                    raise
                print(f"    LLM generation error on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    raise

        # Extract hashtags
        hashtags = self._extract_hashtags(twitter_text)

        # Create GeneratedContent object
        generated = GeneratedContent(
            output_id=output.id,
            content_queue_id=content_queue_id,
            platform="twitter",
            content_text=twitter_text,
            hashtags=hashtags,
            character_count=len(twitter_text),
            generated_at=datetime.utcnow()
        )

        db.add(generated)
        db.flush()

        print(f"    ✅ Twitter content generated: {len(twitter_text)} chars, {len(hashtags)} hashtags")
        return generated

    def validate_twitter_format(self, content: str) -> Tuple[bool, List[str]]:
        """
        Ensure content meets Twitter requirements.

        Args:
            content: Generated Twitter text to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check character count
        if len(content) > 280:
            errors.append(f"Character count {len(content)} exceeds 280")

        # Check for forbidden phrases (advice/predictions)
        import re
        content_lower = content.lower()

        # First, replace allowed compounds with placeholder to exclude them from checks
        content_check = content_lower
        for compound in TWITTER_ALLOWED_COMPOUNDS:
            content_check = content_check.replace(compound.lower(), "")

        # Now check for forbidden phrases in the modified content
        found_forbidden = []
        for phrase in TWITTER_FORBIDDEN_PHRASES:
            if " " not in phrase:  # Single word
                pattern = r'\b' + re.escape(phrase) + r'\b'
                if re.search(pattern, content_check):
                    found_forbidden.append(phrase)
            else:  # Multi-word phrase
                if phrase in content_check:
                    found_forbidden.append(phrase)

        if found_forbidden:
            errors.append(f"Contains forbidden phrases: {', '.join(found_forbidden)}")

        # Check for hashtags
        if "#" not in content:
            errors.append("No hashtags found")

        # Check minimum length (too short = not useful)
        if len(content) < 50:
            errors.append(f"Content too short ({len(content)} chars), minimum 50")

        return (len(errors) == 0, errors)

    def _clean_reasoning_tokens(self, text: str) -> str:
        """
        Remove reasoning tokens and metadata that some LLMs add.

        Cleans up:
        - <think> tags and content between them
        - <reasoning> tags
        - Character count metadata
        - "Let me try" statements
        - Other common artifacts

        Args:
            text: Raw LLM output

        Returns:
            Cleaned text with only the tweet content
        """
        import re

        # Remove <think> tags and everything between them (including newlines)
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)

        # Remove <reasoning> tags
        text = re.sub(r'<reasoning>.*?</reasoning>', '', text, flags=re.DOTALL | re.IGNORECASE)

        # Remove character count metadata
        text = re.sub(r'Character count:?\s*\d+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\(\d+\s*chars?\)', '', text, flags=re.IGNORECASE)

        # Remove "Let me try" statements
        text = re.sub(r'^Let me (try|craft|generate|create).*?[:.\n]', '', text, flags=re.IGNORECASE | re.MULTILINE)

        # Remove "Check character count" statements
        text = re.sub(r'^Check character count.*?[:.\n]', '', text, flags=re.IGNORECASE | re.MULTILINE)

        # Remove triple dashes (sometimes used as separators)
        text = re.sub(r'^---+\s*$', '', text, flags=re.MULTILINE)

        # Remove excess whitespace (but preserve intentional line breaks)
        text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 consecutive newlines

        return text.strip()


    def _extract_hashtags(self, text: str) -> List[str]:
        """
        Extract hashtags from text.

        Args:
            text: Text containing hashtags

        Returns:
            List of hashtags (e.g., ["#RBI", "#Finance"])
        """
        return re.findall(r'#\w+', text)

    def _smart_truncate(self, text: str, max_length: int = 280) -> str:
        """
        Intelligently truncate text to fit within character limit.

        Strategy:
        1. Extract hashtags (preserve them)
        2. Truncate main content to fit
        3. Re-append hashtags
        4. Ensure total length <= max_length

        Args:
            text: Text to truncate
            max_length: Maximum allowed characters

        Returns:
            Truncated text with hashtags preserved
        """
        if len(text) <= max_length:
            return text

        # Extract hashtags
        hashtags = re.findall(r'#\w+', text)
        hashtag_text = " ".join(hashtags) if hashtags else ""

        # Remove hashtags from text
        text_without_hashtags = re.sub(r'#\w+', '', text).strip()

        # Calculate space available for content
        space_for_content = max_length - len(hashtag_text) - (2 if hashtag_text else 0)  # 2 for "\n\n"

        if space_for_content <= 50:
            # Not enough space - just truncate without hashtags
            return text[:max_length - 3] + "..."

        # Truncate at sentence boundary if possible
        truncated = text_without_hashtags[:space_for_content]

        # Try to cut at last sentence
        last_period = truncated.rfind('.')
        last_question = truncated.rfind('?')
        last_exclamation = truncated.rfind('!')

        cut_point = max(last_period, last_question, last_exclamation)

        if cut_point > space_for_content * 0.7:  # Only use sentence boundary if we keep >70% of content
            truncated = truncated[:cut_point + 1].strip()
        else:
            # Cut at last space to avoid breaking words
            last_space = truncated.rfind(' ')
            if last_space > space_for_content * 0.8:
                truncated = truncated[:last_space].strip()

        # Recombine with hashtags
        if hashtag_text:
            final_text = f"{truncated}\n\n{hashtag_text}"
        else:
            final_text = truncated

        return final_text
