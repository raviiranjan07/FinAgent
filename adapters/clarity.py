"""ClarityAdapter - Validates output against clarity and safety rules."""

import re
from typing import List
from adapters.base import BaseAdapter
from adapters.context import ExecutionContext
from config.prompts import FORBIDDEN_PHRASES, ADVICE_PATTERNS
from utils.forbidden_words import detect_forbidden_phrases, format_forbidden_phrase_issues


class ClarityAdapter(BaseAdapter):
    """
    Validates LLM output against clarity rules and forbidden language.

    As per documentation Section 4.5.4 ClarityAdapter.
    Includes forbidden language checks from Section 6.4.
    """

    name = "clarity_adapter"
    version = "1.4.0"  # Added BREAKING_NEWS and DATA_RELEASE checks
    input_keys = ["llm_output", "event_type", "intent"]
    output_keys = ["clarity_issues"]

    # LLM refusal patterns - when LLM refuses to respond
    LLM_REFUSAL_PATTERNS = [
        "i cannot provide",
        "i can't provide",
        "i'm unable to",
        "i am unable to",
        "is there anything else i can help",
        "can i help you with anything else",
        "i'm not able to",
        "i am not able to",
        "i don't have access to",
        "i do not have access to",
        "not publicly available",
    ]

    # Context/usefulness indicators - output should have at least one
    USEFULNESS_INDICATORS = [
        "means", "indicates", "suggests", "affects", "impact",
        "because", "due to", "as a result", "therefore", "consequently",
        "relevant", "significant", "important", "context",
        "this is", "this refers to", "this involves",
        "for example", "such as", "in other words",
    ]

    def run(self, context: ExecutionContext) -> ExecutionContext:
        """Run clarity validation on LLM output."""
        issues = []
        text = context.llm_output or ""
        lower = text.lower()

        # 1. Forbidden Language Check (Instant FAIL conditions)
        # Use smart detection with boundary awareness and whitelisting
        forbidden_issues = detect_forbidden_phrases(text)
        if forbidden_issues:
            formatted_issues = format_forbidden_phrase_issues(forbidden_issues)
            issues.extend(formatted_issues)

        # 2. Advice Pattern Check (context-aware detection)
        # Catches "you should buy", "recommend selling", etc.
        # but NOT "GSK to buy Rapt" or "Treasury is risk-free"
        for pattern in ADVICE_PATTERNS:
            if re.search(pattern, lower):
                issues.append(f"Investment advice detected: pattern '{pattern}'")

        # 3. EXPLANATORY + FINANCE_POLICY specific checks
        if context.intent == "EXPLANATORY" and context.event_type == "FINANCE_POLICY":
            impact_hits = 0

            # Who is affected
            if any(k in lower for k in [
                "banks", "borrowers", "exporters", "importers",
                "investors", "businesses", "customers", "public"
            ]):
                impact_hits += 1

            # What changes
            if any(k in lower for k in [
                "will change", "new rules", "updated rules",
                "revised", "no longer", "now required"
            ]):
                impact_hits += 1

            # When it applies
            if any(k in lower for k in [
                "effective from", "starting", "from", "on january",
                "from april", "with effect from"
            ]):
                impact_hits += 1

            if impact_hits == 0:
                issues.append("Missing practical impact (who/what/when)")

        # 4. MARKET_OPINION specific checks
        if context.intent == "MARKET_OPINION":
            # Explicit advice (hard fail)
            if any(k in lower for k in [
                "you should invest", "recommended to invest",
                "buy now", "sell now", "best investment"
            ]):
                issues.append("Explicit investment advice detected")

            # Forward-looking / predictive language (soft flag)
            if any(k in lower for k in [
                "will likely", "expected to", "set to",
                "poised to", "could lead to"
            ]):
                issues.append("Forward-looking market prediction")

        # 5. DESCRIPTIVE specific checks
        if context.intent == "DESCRIPTIVE":
            word_count = len(text.split())
            if word_count > 500:  # Increased to 500 to provide adequate context for content generation
                issues.append("Too long for descriptive summary")

            if any(k in lower for k in [
                "how to participate", "submit bids",
                "competitive bidding", "non-competitive bidding",
                "payment must be made", "settlement date"
            ]):
                issues.append("Too procedural for descriptive content")

        # 5a. BREAKING_NEWS specific checks
        if context.intent == "BREAKING_NEWS":
            word_count = len(text.split())
            # Breaking news should be concise
            if word_count > 300:
                issues.append("Breaking news should be concise (under 300 words)")

            # Breaking news should report facts, not predictions
            if any(k in lower for k in [
                "will likely", "expected to", "may cause",
                "could lead to", "might result in", "probably"
            ]):
                issues.append("Breaking news should report facts, not predictions")

        # 5b. DATA_RELEASE specific checks
        if context.intent == "DATA_RELEASE":
            # Data release should contain specific numbers/percentages
            has_numbers = bool(re.search(r'\d+\.?\d*\s*%', text))  # Percentage
            has_figures = bool(re.search(r'\d{2,}', text))  # Numbers with 2+ digits

            if not has_numbers and not has_figures:
                issues.append("Data release should include specific numbers or percentages")

            # Should compare to expectations or previous data
            has_comparison = any(k in lower for k in [
                "vs", "versus", "compared to", "from", "previous",
                "expected", "estimate", "forecast", "prior", "last"
            ])
            if not has_comparison:
                issues.append("Data release should compare to expectations or previous data")

        # 6. Universal safety checks
        if any(k in lower for k in [
            "guaranteed returns", "risk-free profit"
        ]):
            issues.append("Misleading financial claim")

        # 7. Placeholder Hallucination Detection
        # LLM sometimes outputs template placeholders instead of admitting uncertainty
        placeholder_patterns = [
            r"\[insert\s+[^\]]+\]",           # [insert specific action...]
            r"\[date\]",                       # [date]
            r"\[list\s+of\s+[^\]]+\]",        # [list of ...]
            r"\[e\.g\.,?\s+[^\]]+\]",         # [e.g., "to maintain..."]
            r"\[specific\s+[^\]]+\]",         # [specific details...]
            r"\[add\s+[^\]]+\]",              # [add relevant...]
            r"\[include\s+[^\]]+\]",          # [include ...]
            r"\[your\s+[^\]]+\]",             # [your name here]
        ]
        for pattern in placeholder_patterns:
            if re.search(pattern, lower):
                issues.append("Placeholder hallucination detected")
                break

        # 8. Chatbot Language Detection
        # LLM should not prompt for follow-up conversation
        chatbot_phrases = [
            "let me know if you'd like",
            "let me know if you would like",
            "feel free to ask",
            "if you have any questions",
            "happy to help",
            "i'd be happy to",
            "would you like me to",
            "shall i explain",
            "do you want me to",
        ]
        for phrase in chatbot_phrases:
            if phrase in lower:
                issues.append("Chatbot language detected")
                break

        # 9. LLM Refusal Detection
        # Detect when LLM refuses to respond instead of providing content
        for pattern in self.LLM_REFUSAL_PATTERNS:
            if pattern in lower:
                issues.append("LLM refusal detected - no useful content provided")
                break

        # 10. Usefulness Check (context/explanation present)
        # For DESCRIPTIVE and MARKET_INFRASTRUCTURE, ensure output explains meaning
        if context.intent == "DESCRIPTIVE" or context.event_type == "MARKET_INFRASTRUCTURE":
            word_count = len(text.split())
            # Only check usefulness if output is substantial (>20 words)
            if word_count > 20:
                has_context = any(indicator in lower for indicator in self.USEFULNESS_INDICATORS)
                if not has_context:
                    issues.append("Missing context - output lacks explanation of meaning or relevance")

        context.clarity_issues = issues
        return context
