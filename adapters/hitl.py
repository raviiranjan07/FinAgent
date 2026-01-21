"""HITLDecisionAdapter - Determines if human review is required."""

from typing import List
from adapters.base import BaseAdapter
from adapters.context import ExecutionContext, HITLDecision


class HITLDecisionAdapter(BaseAdapter):
    """
    Determines if human review is required based on risk, ambiguity, and rule violations.

    Key Principle: "Humans define rules. The system decides when to ask humans."

    As per documentation Section 4.5.5 HITLDecisionAdapter and Section 4.6 HITL Adapter Interface.
    """

    name = "hitl_decision_adapter"
    version = "1.0.0"
    input_keys = ["clarity_issues", "event_type", "intent"]
    output_keys = ["hitl"]

    # High-risk event types that always require review
    HIGH_RISK_EVENT_TYPES = ["FINANCE_POLICY", "MACRO_ECONOMIC"]

    # Known sources that have been validated
    VALIDATED_SOURCES = ["RBI_PRESS", "BLOOMBERG_MARKETS"]

    def run(self, context: ExecutionContext) -> ExecutionContext:
        """Determine if human review is needed."""
        reasons = []
        risk_level = "LOW"

        # 1. Check for clarity issues
        if context.clarity_issues:
            reasons.append(f"Clarity issues detected: {len(context.clarity_issues)} issue(s)")
            risk_level = "MEDIUM"

            # Check for critical issues (forbidden language)
            if any("Forbidden language" in issue for issue in context.clarity_issues):
                risk_level = "HIGH"
                reasons.append("Critical: Forbidden language found")

        # 2. Check for high-risk event types
        if context.event_type in self.HIGH_RISK_EVENT_TYPES:
            reasons.append(f"High-risk event type: {context.event_type}")
            if risk_level == "LOW":
                risk_level = "MEDIUM"

        # 3. Check for unknown/new sources
        if context.event.source not in self.VALIDATED_SOURCES:
            reasons.append(f"New/unvalidated source: {context.event.source}")
            if risk_level == "LOW":
                risk_level = "MEDIUM"

        # 4. Check for ambiguous classification
        if context.event_type == "NON_FINANCE":
            reasons.append("Ambiguous classification: NON_FINANCE")

        # Determine if HITL is required
        required = len(reasons) > 0

        # Determine auto_action
        if risk_level == "HIGH":
            auto_action = "BLOCK"
        elif risk_level == "MEDIUM":
            auto_action = "FLAG"
        else:
            auto_action = "PROCEED"

        context.hitl = HITLDecision(
            required=required,
            reasons=reasons,
            risk_level=risk_level,
            auto_action=auto_action
        )

        return context
