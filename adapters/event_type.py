"""EventTypeAdapter - Classifies events into finance categories."""

import re
from typing import List
from adapters.base import BaseAdapter
from adapters.context import ExecutionContext


class EventTypeAdapter(BaseAdapter):
    """
    Classifies events into one of 6 event types.

    As per documentation Section 4.5.1 EventTypeAdapter.
    """

    name = "event_type_adapter"
    version = "1.2.0"
    input_keys = ["event.title", "event.summary"]
    output_keys = ["event_type"]

    # Patterns that indicate content should be skipped (administrative/legal)
    SKIP_PATTERNS = [
        r"appeal\s+no\.\s*\d+",           # "Appeal No. 6674 of 2026"
        r"appeal\s+nos?\.\s*\d+",         # "Appeal Nos. 6670 & 6671"
        r"filed\s+by\s+[A-Z][a-z]+",      # "filed by Murali krishna"
        r"order\s+in\s+the\s+matter\s+of", # SEBI enforcement orders
    ]

    # Classification keywords
    KEYWORDS = {
        "FINANCE_POLICY": [
            "rbi", "sebi", "regulation", "policy", "act", "scheme",
            "federal reserve", "enforcement action", "ecb", "central bank"
        ],
        "MARKET_INFRASTRUCTURE": [
            "exchange", "bond", "treasury", "bill", "auction", "mou", "clearing"
        ],
        "MARKET_MOVEMENT": [
            "stocks", "shares", "markets", "selloff", "sink", "rally",
            "risk sentiment", "trades"
        ],
        "MACRO_ECONOMIC": [
            "inflation", "gdp", "interest rate", "liquidity", "money supply",
            "fomc", "federal open market", "discount rate", "federal funds",
            "monetary policy", "rate decision", "basis points"
        ],
        "GEO_FINANCIAL": [
            "tariff", "sanction", "trade war", "oil", "energy supply", "conflict"
        ]
    }

    def run(self, context: ExecutionContext) -> ExecutionContext:
        """Classify the event type based on title and summary."""
        combined = f"{context.event.title} {context.event.summary}".lower()

        # Check for skip patterns first (administrative/legal content)
        for pattern in self.SKIP_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                context.event_type = "SKIP"
                return context

        for event_type, keywords in self.KEYWORDS.items():
            if any(keyword in combined for keyword in keywords):
                context.event_type = event_type
                return context

        # Default fallback
        context.event_type = "NON_FINANCE"
        return context
