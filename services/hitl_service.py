"""Centralized HITL (Human-in-the-Loop) Decision Service.

Used by both POC pipeline and Twitter plugin to determine if content needs human review.

Key Principle: "Humans define rules. The system decides when to ask humans."
"""

from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class HITLDecision:
    """HITL decision result."""
    required: bool
    reasons: List[str]
    risk_level: str  # LOW, MEDIUM, HIGH
    auto_action: str  # PROCEED, FLAG, BLOCK
    suggested_verdict: str  # PASS, FAIL
    suggested_verdict_reason: Optional[str] = None


class HITLService:
    """Centralized HITL decision logic shared by POC and Twitter pipelines."""

    # High-risk event types that always require review
    HIGH_RISK_EVENT_TYPES = ["FINANCE_POLICY", "MACRO_ECONOMIC"]

    # Known sources that have been validated
    VALIDATED_SOURCES = ["RBI_PRESS", "BLOOMBERG_MARKETS"]

    @classmethod
    def make_decision(
        cls,
        content_type: str,  # "POC" or "TWITTER"
        validation_issues: List[str],
        event_type: str,
        event_source: str,
        intent: Optional[str] = None,
        additional_context: Optional[Dict] = None
    ) -> HITLDecision:
        """
        Make HITL decision based on validation issues and context.

        Args:
            content_type: Type of content ("POC" or "TWITTER")
            validation_issues: List of validation issues from clarity/safety checks
            event_type: Event classification
            event_source: Source of the event
            intent: Content intent (optional)
            additional_context: Additional context for decision (optional)

        Returns:
            HITLDecision with verdict and reasoning
        """
        reasons = []
        risk_level = "LOW"

        # 1. Check for validation issues
        if validation_issues:
            reasons.append(f"Validation issues detected: {len(validation_issues)} issue(s)")
            risk_level = "MEDIUM"

            # Check for critical issues (forbidden language, advice)
            critical_keywords = ["Forbidden language", "advice", "prediction", "Character count"]
            if any(keyword in issue for keyword in critical_keywords for issue in validation_issues):
                risk_level = "HIGH"

                # Be more specific about what triggered HIGH risk
                if any("Forbidden language" in issue for issue in validation_issues):
                    reasons.append("Critical: Forbidden language found")
                if any("advice" in issue.lower() for issue in validation_issues):
                    reasons.append("Critical: Investment advice detected")
                if content_type == "TWITTER" and any("Character count" in issue for issue in validation_issues):
                    reasons.append("Critical: Twitter character limit exceeded")

        # 2. Check for high-risk event types
        if event_type in cls.HIGH_RISK_EVENT_TYPES:
            reasons.append(f"High-risk event type: {event_type}")
            if risk_level == "LOW":
                risk_level = "MEDIUM"

        # 3. Check for unknown/new sources (POC only)
        if content_type == "POC" and event_source not in cls.VALIDATED_SOURCES:
            reasons.append(f"New/unvalidated source: {event_source}")
            if risk_level == "LOW":
                risk_level = "MEDIUM"

        # 4. Check for ambiguous classification
        if event_type == "NON_FINANCE":
            reasons.append("Ambiguous classification: NON_FINANCE")

        # 5. Twitter-specific checks
        if content_type == "TWITTER":
            # Check if character limit issues
            if any("exceeds 280" in issue.lower() or "character count" in issue.lower()
                   for issue in validation_issues):
                reasons.append("Twitter character limit violation")
                risk_level = "HIGH"

        # Determine if HITL is required
        required = len(reasons) > 0

        # Determine auto_action
        if risk_level == "HIGH":
            auto_action = "BLOCK"
        elif risk_level == "MEDIUM":
            auto_action = "FLAG"
        else:
            auto_action = "PROCEED"

        # Generate suggested verdict and reason
        suggested_verdict = "PASS"
        suggested_verdict_reason = None

        # FAIL conditions (in order of severity)
        if any("Forbidden language" in issue for issue in validation_issues):
            suggested_verdict = "FAIL"
            suggested_verdict_reason = "ADVICE_DETECTED"
        elif risk_level == "HIGH":
            suggested_verdict = "FAIL"
            suggested_verdict_reason = "HIGH_RISK_CONTENT"
        elif len(validation_issues) >= 3:
            suggested_verdict = "FAIL"
            suggested_verdict_reason = "MULTIPLE_VALIDATION_ISSUES"
        elif event_type == "NON_FINANCE":
            suggested_verdict = "FAIL"
            suggested_verdict_reason = "OFF_TOPIC_CONTENT"
        elif content_type == "TWITTER" and any("exceeds 280" in issue.lower()
                                                 for issue in validation_issues):
            suggested_verdict = "FAIL"
            suggested_verdict_reason = "CHARACTER_LIMIT_EXCEEDED"

        return HITLDecision(
            required=required,
            reasons=reasons,
            risk_level=risk_level,
            auto_action=auto_action,
            suggested_verdict=suggested_verdict,
            suggested_verdict_reason=suggested_verdict_reason
        )
