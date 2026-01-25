"""Forbidden word detection with boundary awareness and whitelisting.

This module provides smart detection of forbidden financial advice phrases
while avoiding false positives from technical terms.
"""

import re
from typing import List, Tuple

# Forbidden patterns with word boundaries
# Format: {pattern: description}
FORBIDDEN_PATTERNS = {
    r'\bbuy\b': "buy",
    r'\bbought\b': "bought",
    r'\bbuying\b': "buying",
    r'\bsell\b': "sell",
    r'\bsold\b': "sold",
    r'\bselling\b': "selling",
    r'\bhold\b': "hold",
    r'\bholding\b': "holding",
    r'\binvest now\b': "invest now",
    r'\byou should\b': "you should",
    r'\byou must\b': "you must",
    r'\bmust act\b': "must act",
    r'\bbest time\b': "best time",
    r'\bguaranteed\b': "guaranteed",
    r'\brisk-free\b': "risk-free",
    r'\briskfree\b': "riskfree",
    r'\bcertain profit\b': "certain profit",
    r'\brecommended to\b': "recommended to",
    r'\bact now\b': "act now",
}

# Whitelist: specific terms that contain forbidden words but are OK
# Format: {compound_term: forbidden_word_it_contains}
WHITELIST_TERMS = {
    "buyback": "buy",
    "buy-back": "buy",
    "buybacks": "buy",
    "buydown": "buy",
    "buydowns": "buy",
    "buy back": "buy",  # "Company announces share buy back" is OK
    "debt buyback": "buy",
    "resell": "sell",
    "bestseller": "sell",
    "wholesale": "sell",
    "sell-off": "sell",  # "Market sell-off" is a factual description
    "sell off": "sell",
    "selloff": "sell",
    "household": "hold",
    "shareholder": "hold",
    "stakeholder": "hold",
    "threshold": "hold",
    "behold": "hold",
    "withhold": "hold",
    "foothold": "hold",
    "stronghold": "hold",
}


def is_whitelisted(text: str, match_start: int, match_end: int, forbidden_word: str) -> bool:
    """
    Check if a matched forbidden word is part of a whitelisted compound term.

    Args:
        text: Full text being checked
        match_start: Start index of the match
        match_end: End index of the match
        forbidden_word: The forbidden word that was matched

    Returns:
        True if the match is whitelisted, False otherwise
    """
    text_lower = text.lower()

    # Check compound terms that contain this forbidden word
    for compound, forbidden in WHITELIST_TERMS.items():
        if forbidden != forbidden_word:
            continue

        # Look for the compound term around the match position
        # Check a window of ±20 characters around the match
        window_start = max(0, match_start - 20)
        window_end = min(len(text), match_end + 20)
        window = text_lower[window_start:window_end]

        if compound in window:
            # Verify the compound term actually contains our match
            compound_pos = window.find(compound)
            if compound_pos != -1:
                # Calculate absolute position
                abs_compound_start = window_start + compound_pos
                abs_compound_end = abs_compound_start + len(compound)

                # Check if our match is within the compound term
                if abs_compound_start <= match_start < abs_compound_end:
                    return True

    return False


def detect_forbidden_phrases(text: str) -> List[Tuple[str, str]]:
    """
    Detect forbidden phrases in text with boundary awareness and whitelisting.

    Args:
        text: Text to check

    Returns:
        List of tuples: [(matched_phrase, context_snippet), ...]
        Empty list if no forbidden phrases found
    """
    if not text:
        return []

    text_lower = text.lower()
    issues = []

    for pattern, description in FORBIDDEN_PATTERNS.items():
        matches = list(re.finditer(pattern, text_lower, re.IGNORECASE))

        for match in matches:
            matched_word = match.group()
            match_start = match.start()
            match_end = match.end()

            # Check if this match is whitelisted
            if is_whitelisted(text, match_start, match_end, description):
                continue

            # Extract context (30 chars before and after)
            context_start = max(0, match_start - 30)
            context_end = min(len(text), match_end + 30)
            context = text[context_start:context_end].strip()

            # Add ellipsis if truncated
            if context_start > 0:
                context = "..." + context
            if context_end < len(text):
                context = context + "..."

            issues.append((matched_word, context))

    return issues


def format_forbidden_phrase_issues(issues: List[Tuple[str, str]]) -> List[str]:
    """
    Format forbidden phrase issues for display.

    Args:
        issues: List of (phrase, context) tuples from detect_forbidden_phrases

    Returns:
        List of formatted error messages
    """
    formatted = []
    for phrase, context in issues:
        formatted.append(f"Contains forbidden phrase '{phrase}': ...{context}...")
    return formatted
