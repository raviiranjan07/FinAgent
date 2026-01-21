"""IntentAdapter - Determines content intent type."""

from typing import List
from adapters.base import BaseAdapter
from adapters.context import ExecutionContext


class IntentAdapter(BaseAdapter):
    """
    Determines content intent (EXPLANATORY, DESCRIPTIVE, MARKET_OPINION).

    As per documentation Section 4.5.2 IntentAdapter.
    """

    name = "intent_adapter"
    version = "1.0.0"
    input_keys = ["event.title", "event.summary"]
    output_keys = ["intent"]

    # Intent classification keywords
    MARKET_OPINION_KEYWORDS = [
        "hot trades", "no reason to own", "investors are betting",
        "positioning", "traders expect"
    ]

    EXPLANATORY_KEYWORDS = [
        "regulation", "act", "policy", "rules", "scheme", "guidelines"
    ]

    def run(self, context: ExecutionContext) -> ExecutionContext:
        """Classify the content intent based on title and summary."""
        combined = f"{context.event.title} {context.event.summary}".lower()

        # Check for market opinion first (more specific)
        if any(keyword in combined for keyword in self.MARKET_OPINION_KEYWORDS):
            context.intent = "MARKET_OPINION"
            return context

        # Check for explanatory content
        if any(keyword in combined for keyword in self.EXPLANATORY_KEYWORDS):
            context.intent = "EXPLANATORY"
            return context

        # Default to descriptive
        context.intent = "DESCRIPTIVE"
        return context
