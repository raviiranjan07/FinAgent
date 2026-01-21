"""OutputAdapter - Generates LLM explanation using frozen prompt."""

import time
import requests
from adapters.base import BaseAdapter
from adapters.context import ExecutionContext
from config.settings import OLLAMA_URL, MODEL_NAME, LLM_TIMEOUT, LLM_MAX_RETRIES, LLM_RETRY_DELAY, MAX_CONTENT_LENGTH
from config.prompts import SYSTEM_PROMPT, INTENT_TASKS


class OutputAdapter(BaseAdapter):
    """
    Generates LLM explanation using the frozen system prompt.

    As per documentation Section 4.5.3 OutputAdapter.
    Includes retry logic with exponential backoff for resilience.
    """

    name = "output_adapter"
    version = "1.1.0"
    input_keys = ["event", "event_type", "intent"]
    output_keys = ["llm_output"]

    # Patterns indicating LLM refused to provide content
    REFUSAL_PATTERNS = [
        "i cannot provide",
        "i can't provide",
        "i'm unable to",
        "i am unable to",
        "is there anything else i can help",
        "can i help you with anything else",
    ]

    # Clarification prompt to use when LLM refuses
    CLARIFICATION_PROMPT = """Note: This is a factual news summary task.
You are NOT being asked to provide investment advice.
Simply summarize what happened based on the title and content provided.
If information is limited, state the facts available and note what is unclear."""

    def _is_refusal(self, response: str) -> bool:
        """Check if LLM response is a refusal to provide content."""
        lower = response.lower()
        return any(pattern in lower for pattern in self.REFUSAL_PATTERNS)

    def _call_llm_with_retry(self, payload: dict, event_id: str) -> str:
        """Call LLM with retry logic and exponential backoff."""
        last_error = None

        for attempt in range(LLM_MAX_RETRIES):
            try:
                response = requests.post(
                    OLLAMA_URL,
                    json=payload,
                    timeout=LLM_TIMEOUT
                )
                response.raise_for_status()
                return response.json()["response"]

            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < LLM_MAX_RETRIES - 1:
                    delay = LLM_RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                    print(f"    LLM attempt {attempt + 1} failed, retrying in {delay}s...")
                    time.sleep(delay)

        print(f"LLM generation failed for event {event_id} after {LLM_MAX_RETRIES} attempts: {last_error}")
        return f"Error: Could not generate explanation after {LLM_MAX_RETRIES} attempts."

    def run(self, context: ExecutionContext) -> ExecutionContext:
        """Generate explanation via LLM."""
        # Get intent-specific task
        task = INTENT_TASKS.get(context.intent, INTENT_TASKS["DESCRIPTIVE"])

        # Truncate content if too large (prevents LLM timeout on heavy data)
        content = context.event.summary
        if len(content) > MAX_CONTENT_LENGTH:
            content = content[:MAX_CONTENT_LENGTH] + "\n[Content truncated for processing]"
            print(f"    Content truncated: {len(context.event.summary)} -> {MAX_CONTENT_LENGTH} chars")

        # Build prompt
        prompt = f"""SYSTEM:
{SYSTEM_PROMPT}

EVENT TITLE:
{context.event.title}

EVENT CONTENT:
{content}

TASK:
{task}
"""

        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False
        }

        # First attempt
        llm_output = self._call_llm_with_retry(payload, context.event.event_id)

        # Check for refusal and retry with clarification if needed
        if self._is_refusal(llm_output):
            print(f"    LLM refused, retrying with clarification...")
            clarified_prompt = f"""{prompt}

{self.CLARIFICATION_PROMPT}
"""
            payload["prompt"] = clarified_prompt
            llm_output = self._call_llm_with_retry(payload, context.event.event_id)

        context.llm_output = llm_output
        return context
