"""OutputAdapter - Generates LLM explanation using frozen prompt."""

import hashlib
import time
from datetime import datetime
from adapters.base import BaseAdapter
from adapters.context import ExecutionContext
from config.settings import MAX_CONTENT_LENGTH, PROMPT_VERSION
from config.prompts import SYSTEM_PROMPT, INTENT_TASKS
from services.llm_service import LLMService
from utils.timezone import get_ist_now


class OutputAdapter(BaseAdapter):
    """
    Generates LLM explanation using the frozen system prompt.

    As per documentation Section 4.5.3 OutputAdapter.
    Includes retry logic with exponential backoff for resilience.

    Version History:
    - v1.0.0: Initial implementation with frozen prompt
    - v1.1.0: Added refusal detection and clarification retry
    - v1.2.0: Added CRITICAL OUTPUT FORMAT (v1.6-notoken) to prevent
              reasoning token output from qwen models (<think> tags)
    - v1.3.0: Added output_embedding generation for similarity search
    - v1.4.0: Moved <think> tag filtering to post-processing (from prompt)
              to avoid suppressing output length
    """

    name = "output_adapter"
    version = "1.5.0"  # Fixed: Reuse EmbeddingService instance instead of creating new one each call
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

    def __init__(self):
        """Initialize adapter with LLM service and lazy-loaded embedding service."""
        super().__init__()
        self.llm = LLMService()
        self._embedding_service = None  # Lazy-loaded to avoid loading model if not needed

    def _get_embedding_service(self):
        """Get or create embedding service (lazy initialization)."""
        if self._embedding_service is None:
            from utils.embeddings import EmbeddingService
            self._embedding_service = EmbeddingService()
        return self._embedding_service

    def _is_refusal(self, response: str) -> bool:
        """Check if LLM response is a refusal to provide content."""
        lower = response.lower()
        return any(pattern in lower for pattern in self.REFUSAL_PATTERNS)

    def _clean_output(self, response: str) -> str:
        """
        Clean LLM output by removing reasoning tokens and metadata.

        This post-processing removes:
        - <think> tags and their content
        - Character count annotations
        - Draft markers and meta-commentary
        """
        import re

        # Remove <think>...</think> tags and their content
        cleaned = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL | re.IGNORECASE)

        # Remove character count annotations like "(258 characters)" or "(safe under 270)"
        cleaned = re.sub(r'\(\d+\s*characters?\)', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\(safe under \d+\)', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\(within limit\)', '', cleaned, flags=re.IGNORECASE)

        # Remove draft markers like "Attempt 1:", "Final draft:", etc.
        cleaned = re.sub(r'^(Attempt|Draft|Final|Revised)\s*\d*:?\s*', '', cleaned, flags=re.MULTILINE | re.IGNORECASE)

        # Strip leading/trailing whitespace
        cleaned = cleaned.strip()

        return cleaned

    def _call_llm_with_retry(self, prompt: str, event_id: str) -> str:
        """Call LLM with retry logic (handled by LLMService)."""
        try:
            return self.llm.generate(prompt)
        except Exception as e:
            print(f"LLM generation failed for event {event_id}: {e}")
            return f"Error: Could not generate explanation - {str(e)}"

    def run(self, context: ExecutionContext) -> ExecutionContext:
        """Generate explanation via LLM."""
        # Start timing
        start_time = time.time()

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

        # First attempt
        llm_output = self._call_llm_with_retry(prompt, context.event.event_id)

        # Check for refusal and retry with clarification if needed
        if self._is_refusal(llm_output):
            print(f"    LLM refused, retrying with clarification...")
            clarified_prompt = f"""{prompt}

            {self.CLARIFICATION_PROMPT}
            """
            llm_output = self._call_llm_with_retry(clarified_prompt, context.event.event_id)

        # Clean output - remove <think> tags and metadata (post-processing)
        llm_output = self._clean_output(llm_output)

        # Calculate generation duration
        generation_duration_ms = int((time.time() - start_time) * 1000)

        # Store model name for database column (top-level field for easy querying)
        context.llm_model = self.llm.model_name

        # Capture generation metadata for audit trail
        context.generation_metadata = {
            # Model information
            "model": self.llm.model_name,
            "provider": self.llm.mode,  # "ollama" or "api"

            # Prompt configuration
            "prompt_version": PROMPT_VERSION,
            "system_prompt_hash": hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),

            # Generation parameters (LLMService doesn't expose these, use defaults)
            "temperature": 0.7,  # Default from LLM service
            "max_tokens": 512,   # Default from LLM service

            # Adapter versions (for reproducibility)
            "adapter_versions": {
                "output": self.version,
            },

            # Timing and context
            "generated_at": get_ist_now().isoformat(),
            "generation_duration_ms": generation_duration_ms,
            "event_type": context.event_type,
            "intent": context.intent,
            "source": context.event.source,
        }

        context.llm_output = llm_output

        # Generate embedding for the output text (for similarity search/deduplication)
        try:
            embedding_service = self._get_embedding_service()
            context.output_embedding = embedding_service.encode(llm_output)  # Already returns list
            print(f"    Generated output embedding ({len(context.output_embedding)}-dim)")
        except Exception as e:
            print(f"    [OUTPUT] Warning: Failed to generate output embedding: {e}")
            context.output_embedding = None

        return context
