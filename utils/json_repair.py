"""JSON repair utilities for fixing common LLM JSON generation errors."""

import json
import re


def repair_json(json_str: str) -> str:
    """
    Attempt to repair common JSON formatting errors from LLMs.

    Common issues fixed:
    - Missing commas between fields
    - Extra commas before closing braces
    - Unescaped quotes in strings
    - Missing quotes around keys
    - Trailing commas

    Args:
        json_str: Potentially malformed JSON string

    Returns:
        Repaired JSON string (no guarantee it's valid)
    """
    # Remove any leading/trailing whitespace
    json_str = json_str.strip()

    # Fix 1: Add missing commas between fields
    # Pattern: }"key" or }"\nkey should have comma
    json_str = re.sub(r'"\s*\n\s*"', '",\n"', json_str)

    # Fix 2: Remove trailing commas before }
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)

    # Fix 3: Fix common newline issues in string values
    # This is tricky - we need to preserve intentional newlines but fix broken ones

    # Fix 4: Ensure keys are quoted (if they're not already)
    # Pattern: { word: or , word: should be { "word": or , "word":
    json_str = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_str)

    return json_str


def parse_json_with_repair(json_str: str, max_attempts: int = 3) -> dict:
    """
    Try to parse JSON, attempting repairs if initial parse fails.

    Args:
        json_str: JSON string to parse
        max_attempts: Maximum number of repair attempts

    Returns:
        Parsed JSON as dict

    Raises:
        json.JSONDecodeError: If all repair attempts fail
    """
    # Attempt 1: Parse as-is
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        original_error = e

    # Attempt 2: Apply repairs
    for attempt in range(max_attempts):
        try:
            repaired = repair_json(json_str)
            return json.loads(repaired)
        except json.JSONDecodeError:
            # Try more aggressive repairs
            if attempt == 0:
                # Add more aggressive comma fixing
                json_str = re.sub(r'"\s+"', '",\n"', json_str)
            elif attempt == 1:
                # Try to fix string values that span multiple lines
                json_str = re.sub(r':\s*"([^"]*)\n([^"]*)"', r': "\1 \2"', json_str)

    # All repair attempts failed - raise original error
    raise original_error


def extract_json_from_text(text: str) -> str:
    """
    Extract JSON object from text that may contain extra content.

    Useful when LLM outputs explanatory text before/after JSON.

    Args:
        text: Text containing JSON

    Returns:
        Extracted JSON string
    """
    # Try to find JSON object between { and }
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0)

    # Try to find JSON array between [ and ]
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        return match.group(0)

    # No JSON found, return original
    return text
