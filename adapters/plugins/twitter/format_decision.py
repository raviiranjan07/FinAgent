"""FormatDecision Adapter - Decides SINGLE vs THREAD based on content characteristics.

Uses POC data directly (event_type, intent, content length) - no ImpactFraming needed.

Priority Logic:
1. Event type rules (FINANCE_POLICY, MACRO_ECONOMIC) → THREAD
2. Intent rules (EXPLANATORY) → THREAD
3. Default (DESCRIPTIVE, short) → SINGLE
"""


class FormatDecisionAdapter:
    """Decide Twitter format based on impact analysis and content characteristics."""

    def __init__(self):
        self.name = "FormatDecision"

    def run(self, context):
        """
        Decide format based on POC data (event_type, intent, content length).

        Input (from context):
        - event_type: Event classification from POC
        - intent: Content intent from POC
        - llm_output: POC content

        Output (added to context):
        - twitter_format: {
            format: "SINGLE" | "THREAD",
            thread_length: int (if THREAD),
            reason: str (decision rationale)
          }
        """
        print(f"[{self.name}] Deciding Twitter format...")

        event_type = context.event_type
        intent = context.intent
        content_length = len(context.llm_output) if context.llm_output else 0

        # Priority 1: Event type rules
        # Educational event types that benefit from thread format
        if event_type in ["FINANCE_POLICY", "MACRO_ECONOMIC", "DIGITAL_ASSETS"]:
            decision = {
                "format": "THREAD",
                "reason": f"{event_type} events need structured explanation"
            }
            print(f"[{self.name}] Decision: THREAD (event type) - LLM will decide length")

            # NEW: Use plugin namespace
            context.update_plugin_data("twitter", {"format": decision})
            # OLD: Maintain backward compatibility
            context.twitter_format = decision
            return context

        # Priority 2: Intent rules
        if intent == "EXPLANATORY":
            decision = {
                "format": "THREAD",
                "reason": "Educational content works better in threads"
            }
            print(f"[{self.name}] Decision: THREAD (explanatory intent) - LLM will decide length")

            context.update_plugin_data("twitter", {"format": decision})
            context.twitter_format = decision
            return context

        # Priority 3: Default - SINGLE for simple updates
        if intent == "DESCRIPTIVE" and content_length < 400:
            decision = {
                "format": "SINGLE",
                "reason": "Simple updates work as concise tweets"
            }
            print(f"[{self.name}] Decision: SINGLE (descriptive + short)")

            context.update_plugin_data("twitter", {"format": decision})
            context.twitter_format = decision
            return context

        # Fallback: SINGLE
        decision = {
            "format": "SINGLE",
            "reason": "Default format for general content"
        }
        print(f"[{self.name}] Decision: SINGLE (default)")

        context.update_plugin_data("twitter", {"format": decision})
        context.twitter_format = decision
        return context
