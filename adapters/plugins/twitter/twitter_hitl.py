"""TwitterHITL Adapter - Determines if Twitter content needs human review.

Uses centralized HITLService shared with POC pipeline.
"""

from services.hitl_service import HITLService


class TwitterHITLAdapter:
    """Determine if Twitter content needs human review before publishing."""

    def __init__(self):
        self.name = "TwitterHITL"

    def run(self, context):
        """
        Determine if human review is needed for Twitter content.

        Input (from context):
        - twitter_clarity_issues: Validation issues from TwitterClarityAdapter
        - event_type: Event classification from POC
        - intent: Content intent from POC
        - event: Event object (for source)
        - twitter_content: Generated Twitter content

        Output (added to context):
        - twitter_hitl: {
            required: bool,
            reasons: List[str],
            risk_level: str,
            auto_action: str,
            suggested_verdict: str,
            suggested_verdict_reason: str
          }
        """
        print(f"[{self.name}] Evaluating Twitter content for HITL...")

        # NEW: Read from plugin namespace with fallback to legacy fields
        twitter_data = context.get_plugin_data("twitter", {})
        validation_issues = twitter_data.get("clarity_issues") or getattr(context, 'twitter_clarity_issues', [])
        twitter_format = twitter_data.get("format") or context.twitter_format
        twitter_content = twitter_data.get("content") or context.twitter_content

        # Use centralized HITLService
        decision = HITLService.make_decision(
            content_type="TWITTER",
            validation_issues=validation_issues,
            event_type=context.event_type,
            event_source=context.event.source,
            intent=context.intent,
            additional_context={
                "format": twitter_format.get("format") if twitter_format else None,
                "char_count": twitter_content.get("char_count") if twitter_content else None
            }
        )

        hitl_decision = {
            "required": decision.required,
            "reasons": decision.reasons,
            "risk_level": decision.risk_level,
            "auto_action": decision.auto_action,
            "suggested_verdict": decision.suggested_verdict,
            "suggested_verdict_reason": decision.suggested_verdict_reason
        }

        # NEW: Update plugin namespace
        context.update_plugin_data("twitter", {"hitl": hitl_decision})
        # OLD: Maintain backward compatibility
        context.twitter_hitl = hitl_decision

        # Print decision
        if decision.required:
            print(f"[{self.name}] HITL Required - Risk Level: {decision.risk_level}")
            print(f"[{self.name}] Suggested Verdict: {decision.suggested_verdict}")
            if decision.suggested_verdict_reason:
                print(f"[{self.name}] Reason: {decision.suggested_verdict_reason}")
            print(f"[{self.name}] Issues:")
            for reason in decision.reasons:
                print(f"  - {reason}")
        else:
            print(f"[{self.name}] No HITL required - Content appears safe")

        return context
