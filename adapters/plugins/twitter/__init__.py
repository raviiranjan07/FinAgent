"""Twitter Plugin Adapters.

This package contains the Twitter-specific content generation pipeline:
- FormatDecision: Decides SINGLE vs THREAD based on POC data
- TwitterSingle: Generates single tweets
- TwitterThread: Generates 3-tweet threads
- TwitterClarity: Validates Twitter-specific safety rules
- TwitterHITL: Decides if content needs human review
"""

from .format_decision import FormatDecisionAdapter
from .twitter_single import TwitterSingleAdapter
from .twitter_thread import TwitterThreadAdapter
from .twitter_clarity import TwitterClarityAdapter
from .twitter_hitl import TwitterHITLAdapter

__all__ = [
    "FormatDecisionAdapter",
    "TwitterSingleAdapter",
    "TwitterThreadAdapter",
    "TwitterClarityAdapter",
    "TwitterHITLAdapter",
]
