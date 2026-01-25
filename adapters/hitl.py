"""HITLDecisionAdapter - Determines if human review is required.

Refactored to use centralized HITLService shared with Twitter pipeline.
"""

from adapters.base import BaseAdapter
from adapters.context import ExecutionContext, HITLDecision
from services.hitl_service import HITLService


class HITLDecisionAdapter(BaseAdapter):
    """
    Determines if human review is required based on risk, ambiguity, and rule violations.

    Uses centralized HITLService for decision logic.

    Key Principle: "Humans define rules. The system decides when to ask humans."

    As per documentation Section 4.5.5 HITLDecisionAdapter and Section 4.6 HITL Adapter Interface.
    """

    name = "hitl_decision_adapter"
    version = "2.0.0"  # Updated to use centralized service
    input_keys = ["clarity_issues", "event_type", "intent"]
    output_keys = ["hitl"]

    def run(self, context: ExecutionContext) -> ExecutionContext:
        """Determine if human review is needed using centralized HITLService."""

        # Use centralized service
        decision = HITLService.make_decision(
            content_type="POC",
            validation_issues=context.clarity_issues or [],
            event_type=context.event_type,
            event_source=context.event.source,
            intent=context.intent
        )

        # Convert service decision to context HITLDecision
        context.hitl = HITLDecision(
            required=decision.required,
            reasons=decision.reasons,
            risk_level=decision.risk_level,
            auto_action=decision.auto_action,
            suggested_verdict=decision.suggested_verdict,
            suggested_verdict_reason=decision.suggested_verdict_reason
        )

        return context
