"""LLM service for generating content via Ollama or API (Groq)."""

import time
import requests
import threading
from typing import Optional
from groq import Groq
from config.settings import (
    LLM_MODE,
    OLLAMA_URL,
    OLLAMA_MODEL,
    GROQ_API_KEY,
    GROQ_MODEL,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_BASE_URL,
    LLM_TIMEOUT,
    LLM_MAX_RETRIES,
    LLM_RETRY_DELAY,
    LLM_ENABLE_GEMINI_FALLBACK,
    LLM_ENABLE_OLLAMA_FALLBACK,
)
from services.quota_manager import get_quota_manager


class LLMService:
    """Reusable LLM service supporting both Ollama and Groq API."""

    # Class-level rate limiting for Groq API (shared across all instances, thread-safe)
    _last_groq_call = 0.0
    _groq_rate_limit = 4.0  # Conservative: 15 RPM = 4 seconds minimum between calls
    _groq_lock = threading.Lock()  # Thread-safe access to rate limiter

    # Class-level rate limiting for Gemini Primary (shared across all instances, thread-safe)
    _last_gemini_primary_call = 0.0
    _gemini_primary_rate_limit = 5.0  # 15 RPM with safety buffer = 5 seconds minimum (12 RPM actual)
    _gemini_primary_lock = threading.Lock()  # Thread-safe access to rate limiter

    # Class-level rate limiting for Gemini Secondary (shared across all instances, thread-safe)
    _last_gemini_secondary_call = 0.0
    _gemini_secondary_rate_limit = 5.0  # 15 RPM with safety buffer = 5 seconds minimum (12 RPM actual)
    _gemini_secondary_lock = threading.Lock()  # Thread-safe access to rate limiter

    # Request timestamp tracking for quota detection (thread-safe) - shared for both Gemini models
    _gemini_request_timestamps = []  # List of successful request timestamps
    _gemini_timestamps_lock = threading.Lock()  # Thread-safe access to timestamps

    def __init__(
        self,
        mode: Optional[str] = None,
        model_name: Optional[str] = None,
        max_retries: Optional[int] = None,
        timeout: Optional[int] = None
    ):
        """
        Initialize LLM service.

        Args:
            mode: "ollama", "groq", or "gemini" (default: from LLM_MODE setting)
            model_name: Model to use (default: from settings based on mode)
            max_retries: Max retry attempts (default: from settings)
            timeout: Request timeout in seconds (default: from settings)
        """
        # Get quota manager
        self.quota_manager = get_quota_manager()

        # Determine best available mode based on quota status
        preferred_mode = (mode or LLM_MODE).lower()
        self.mode = self.quota_manager.get_best_available_mode(preferred_mode)

        self.max_retries = max_retries or LLM_MAX_RETRIES
        self.timeout = timeout or LLM_TIMEOUT

        # Set model based on mode
        if self.mode == "ollama":
            self.model_name = model_name or OLLAMA_MODEL
            self.base_url = OLLAMA_URL
        elif self.mode == "groq":
            self.model_name = model_name or GROQ_MODEL
            self.api_key = GROQ_API_KEY
            if not self.api_key:
                raise ValueError("GROQ_API_KEY is required when LLM_MODE=groq")
        elif self.mode in ["gemini_primary", "gemini_secondary"]:
            # Import model names from settings
            from config.settings import GEMINI_PRIMARY_MODEL, GEMINI_SECONDARY_MODEL

            if self.mode == "gemini_primary":
                self.model_name = model_name or GEMINI_PRIMARY_MODEL
            else:  # gemini_secondary
                self.model_name = model_name or GEMINI_SECONDARY_MODEL

            self.base_url = GEMINI_BASE_URL
            self.api_key = GEMINI_API_KEY
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY is required for Gemini models")
        else:
            raise ValueError(f"Invalid LLM_MODE: {self.mode}. Must be 'ollama', 'groq', 'gemini_primary', or 'gemini_secondary'")

        print(f"[LLM] Initialized in {self.mode.upper()} mode with model: {self.model_name}")

    def _clean_model_output(self, text: str) -> str:
        """
        Clean model-specific artifacts from LLM output.

        This handles model quirks at the service layer, keeping prompts model-independent.

        Removes:
        - <think> tags (Qwen reasoning tokens)
        - Character count notes: "(258 characters...)"
        - Metadata annotations: "(Neutral, factual framing...)"
        - Draft markers and revision notes

        Args:
            text: Raw text from LLM

        Returns:
            Cleaned text ready for application use
        """
        import re

        if not text:
            return text

        original_length = len(text)

        # Remove <think> tags and their content (Qwen models)
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)

        # Remove character count annotations: "(258 characters...)" or "(257 chars)"
        text = re.sub(r'\(\s*\d+\s*(?:characters?|chars?).*?\)', '', text, flags=re.IGNORECASE)

        # Remove metadata/style annotations in parentheses at end of text
        # Examples: "(Neutral, factual framing...)", "(Calm analysis with data)"
        text = re.sub(r'\([^)]*(?:neutral|factual|framing|analysis|calm|skepticism|data|context).*?\)\s*$',
                     '', text, flags=re.IGNORECASE)

        # Remove emoji-only annotations at end: "🔄" or "📊"
        text = re.sub(r'\s+[🔄📊💡⚠️✓❌]+\s*$', '', text)

        # Remove multiple blank lines (normalize whitespace)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

        # Strip leading/trailing whitespace
        text = text.strip()

        # Log if cleaning removed content
        if len(text) < original_length:
            removed = original_length - len(text)
            print(f"    [LLM-Clean] Removed {removed} chars of model artifacts ({original_length} → {len(text)})")

        return text

    def _count_gemini_requests_in_last_minute(self) -> int:
        """Count Gemini API requests made in the last 60 seconds (thread-safe)."""
        with LLMService._gemini_timestamps_lock:
            now = time.time()
            cutoff = now - 60.0  # 60 seconds ago

            # Remove timestamps older than 60 seconds
            LLMService._gemini_request_timestamps = [
                ts for ts in LLMService._gemini_request_timestamps if ts >= cutoff
            ]

            return len(LLMService._gemini_request_timestamps)

    def _track_gemini_request(self):
        """Record timestamp of successful Gemini API request (thread-safe)."""
        with LLMService._gemini_timestamps_lock:
            LLMService._gemini_request_timestamps.append(time.time())

    def _determine_quota_reset_time(self, response) -> float:
        """
        Determine whether we hit minute quota or day quota based on 429 response.

        Gemini API quotas (Free Tier):
        - RPM: 15 requests per minute → resets in 60 seconds (0.017 hours)
        - RPD: 1500 requests per day → resets at midnight Pacific Time (08:00 UTC)

        Args:
            response: The 429 error response from Gemini API

        Returns:
            Hours until reset
        """
        print(f"    [QuotaDetect] === GEMINI QUOTA DETECTION ===")

        try:
            # STEP 1: PARSE JSON RESPONSE BODY FOR SPECIFIC QUOTA TYPE
            # Don't use hasattr() - it can trigger encoding errors
            # Just try to access the attributes directly
            if response:
                print(f"    [QuotaDetect] Response status: {response.status_code}")
                print(f"    [QuotaDetect] Response type: {type(response)}")

                try:
                    import json
                    # Try to get response text
                    response_text = response.text
                    print(f"    [QuotaDetect] Response text length: {len(response_text)}")

                    response_body = json.loads(response_text)

                    # Log error structure (handle encoding issues for Windows console)
                    error_str = json.dumps(response_body, indent=2, ensure_ascii=True)
                    print(f"    [QuotaDetect] Full error response:")
                    print(f"{error_str}")

                    # Convert to lowercase for keyword matching
                    error_message = error_str.lower()

                    # Check for specific quota type in error details
                    # Gemini returns: "GenerateContentRequestsPerMinute-FreeTier" or "GenerateContentRequestsPerDay-FreeTier"
                    if 'generatecontentrequestsperminute' in error_message or 'requestsperminute' in error_message:
                        print(f"    [QuotaDetect] ✓ RPM quota hit (15 requests/minute)")
                        print(f"    [QuotaDetect] → Reset in 60 seconds")
                        return 0.017  # 60 seconds = 0.0167 hours

                    if 'generatecontentrequestsperday' in error_message or 'requestsperday' in error_message:
                        # RPD limit - calculate time until midnight Pacific (08:00 UTC)
                        from datetime import datetime, timedelta, timezone

                        now_utc = datetime.now(timezone.utc)
                        # Midnight Pacific Time = 08:00 UTC
                        next_reset_utc = now_utc.replace(hour=8, minute=0, second=0, microsecond=0)

                        # If past 08:00 UTC today, reset is tomorrow
                        if now_utc.hour >= 8:
                            next_reset_utc += timedelta(days=1)

                        hours_until_reset = (next_reset_utc - now_utc).total_seconds() / 3600.0
                        print(f"    [QuotaDetect] ✓ RPD quota hit (1500 requests/day)")
                        print(f"    [QuotaDetect] → Reset at {next_reset_utc.strftime('%Y-%m-%d %H:%M UTC')} ({hours_until_reset:.1f}h)")
                        return hours_until_reset

                    # STEP 2: CHECK FOR retryDelay FIELD
                    if 'error' in response_body and isinstance(response_body['error'], dict):
                        error_details = response_body['error']

                        if 'retryDelay' in error_details:
                            retry_delay_str = error_details['retryDelay']
                            # Parse "30s" or "1h" format
                            if retry_delay_str.endswith('s'):
                                retry_seconds = int(retry_delay_str[:-1])
                                retry_hours = retry_seconds / 3600.0
                                print(f"    [QuotaDetect] ✓ retryDelay: {retry_delay_str} ({retry_hours:.2f}h)")
                                return max(retry_hours, 0.017)
                            elif retry_delay_str.endswith('h'):
                                retry_hours = float(retry_delay_str[:-1])
                                print(f"    [QuotaDetect] ✓ retryDelay: {retry_delay_str}")
                                return retry_hours

                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    print(f"    [QuotaDetect] JSON parse failed: {e}")
                    print(f"    [QuotaDetect] Raw response text (first 1000 chars):")
                    try:
                        print(f"{response.text[:1000]}")
                    except:
                        print(f"    (Could not print response text)")
                except Exception as e:
                    print(f"    [QuotaDetect] Unexpected error accessing response: {e}")
                    print(f"    [QuotaDetect] Error type: {type(e)}")
                    import traceback
                    traceback.print_exc()

            # STEP 3: CHECK RETRY-AFTER HEADER
            if response:
                retry_after = response.headers.get('Retry-After')
                if retry_after:
                    try:
                        retry_seconds = int(retry_after)
                        retry_hours = retry_seconds / 3600.0
                        print(f"    [QuotaDetect] ✓ Retry-After header: {retry_seconds}s ({retry_hours:.2f}h)")
                        return max(retry_hours, 0.017)
                    except ValueError:
                        pass

            # STEP 4: KEYWORD SEARCH IN RESPONSE TEXT
            if response:
                response_text = response.text.lower()

                if 'minute' in response_text or 'rpm' in response_text:
                    print(f"    [QuotaDetect] ✓ Keyword: MINUTE quota (15 RPM)")
                    return 0.017

                if 'day' in response_text or 'daily' in response_text or 'rpd' in response_text:
                    from datetime import datetime, timedelta, timezone
                    now_utc = datetime.now(timezone.utc)
                    next_reset_utc = now_utc.replace(hour=8, minute=0, second=0, microsecond=0)
                    if now_utc.hour >= 8:
                        next_reset_utc += timedelta(days=1)
                    hours_until_reset = (next_reset_utc - now_utc).total_seconds() / 3600.0
                    print(f"    [QuotaDetect] ✓ Keyword: DAY quota (1500 RPD) → reset in {hours_until_reset:.1f}h")
                    return hours_until_reset

            # STEP 5: HEURISTIC - DEFAULT TO RPM (CONSERVATIVE)
            recent_requests = self._count_gemini_requests_in_last_minute()
            print(f"    [QuotaDetect] Heuristic: {recent_requests} requests in last 60s")

            # FIXED LOGIC: Always default to RPM unless we have explicit evidence of RPD
            # Rationale:
            # - RPM limit (15 req/min) is hit frequently during pipeline runs
            # - After waiting 61+ seconds, request counter resets to 0
            # - We should NOT interpret "0 recent requests" as daily quota exhaustion
            # - Safer to assume short reset (1 min) than long reset (24 hours)
            # - If it's really RPD, we'll get 429 again after 1 minute and can retry

            print(f"    [QuotaDetect] ⚠️ No explicit quota type found - defaulting to RPM (safer)")
            print(f"    [QuotaDetect] → Reset in 60 seconds (will retry after)")
            return 0.017  # 1 minute reset - conservative default

        except Exception as e:
            print(f"    [QuotaDetect] Error during detection: {e}")

        # Final fallback: DEFAULT TO RPM (CONSERVATIVE)
        # If all detection methods fail, assume short reset (1 minute) rather than long reset (24 hours)
        # This prevents incorrectly marking API as exhausted for a full day due to detection failures
        print(f"    [QuotaDetect] ⚠️ All detection methods failed - defaulting to RPM (1 minute)")
        return 0.017  # 1 minute reset

    def generate(self, prompt: str, stream: bool = False) -> str:
        """
        Generate text using LLM with retry logic and automatic fallback.

        Fallback chains:
        - LLM_MODE=groq: Groq → Gemini Primary → Gemini Secondary → Ollama
        - LLM_MODE=gemini: Gemini Primary → Gemini Secondary → Groq → Ollama
        - LLM_MODE=ollama: Ollama only

        Args:
            prompt: The prompt to send to LLM
            stream: Whether to stream response (default: False)

        Returns:
            Generated text from LLM

        Raises:
            Exception: If all retry attempts and fallbacks fail
        """
        if self.mode == "ollama":
            return self._generate_ollama(prompt, stream)
        elif self.mode == "groq":
            return self._generate_groq(prompt)
        elif self.mode in ["gemini", "gemini_primary", "gemini_secondary"]:
            return self._generate_gemini(prompt)
        else:
            raise ValueError(f"Invalid mode: {self.mode}")

    def _generate_ollama(self, prompt: str, stream: bool = False) -> str:
        """Generate text using Ollama API."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": stream
        }

        last_error = None
        start_time = time.time()

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
                result = response.json()["response"]

                api_time = time.time() - start_time
                print(f"    [LLM-Ollama] Generated response in {api_time:.2f}s")

                # Clean model-specific artifacts before returning
                return self._clean_model_output(result)

            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = LLM_RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                    print(f"    [Ollama] Attempt {attempt + 1} failed, retrying in {delay}s...")
                    time.sleep(delay)

        # All retries failed
        error_msg = f"Ollama generation failed after {self.max_retries} attempts: {last_error}"
        print(f"    {error_msg}")
        raise Exception(error_msg)

    def _generate_ollama_fallback(self, prompt: str, stream: bool = False) -> str:
        """
        Generate text using Ollama as fallback when OpenRouter fails.

        Uses llama3 model by default (or OLLAMA_MODEL from config).
        """
        url = f"{OLLAMA_URL}/api/generate"
        fallback_model = OLLAMA_MODEL or "llama3"

        payload = {
            "model": fallback_model,
            "prompt": prompt,
            "stream": stream
        }

        last_error = None
        start_time = time.time()

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()

                if stream:
                    # Collect streaming response
                    full_response = ""
                    for line in response.iter_lines():
                        if line:
                            json_response = line.decode('utf-8')
                            import json
                            data = json.loads(json_response)
                            if "response" in data:
                                full_response += data["response"]
                    ollama_time = time.time() - start_time
                    print(f"    [Ollama-Fallback] Generated response in {ollama_time:.2f}s (model: {fallback_model})")

                    # Clean model-specific artifacts before returning
                    return self._clean_model_output(full_response)
                else:
                    # Non-streaming response
                    result = response.json()
                    content = result.get("response", "")
                    ollama_time = time.time() - start_time
                    print(f"    [Ollama-Fallback] Generated response in {ollama_time:.2f}s (model: {fallback_model})")

                    # Clean model-specific artifacts before returning
                    return self._clean_model_output(content)

            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = LLM_RETRY_DELAY * (2 ** attempt)
                    print(f"    [Ollama-Fallback] Attempt {attempt + 1} failed, retrying in {delay}s...")
                    time.sleep(delay)

        # All retries failed
        error_msg = f"Ollama fallback failed after {self.max_retries} attempts: {last_error}"
        print(f"    {error_msg}")
        raise Exception(error_msg)

    def _generate_groq_fallback(self, prompt: str) -> str:
        """
        Generate text using Groq API as fallback when Gemini fails.

        Uses the configured GROQ_MODEL from config.
        """
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not configured - cannot use Groq fallback")

        last_error = None
        start_time = time.time()

        for attempt in range(self.max_retries):
            try:
                # Initialize Groq client
                client = Groq(api_key=GROQ_API_KEY)

                # Make API call using Groq SDK
                completion = client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=1,
                    max_completion_tokens=8192,
                    top_p=1,
                    stream=False,
                    stop=None
                )

                # Extract content from response
                if completion.choices and len(completion.choices) > 0:
                    content = completion.choices[0].message.content
                    api_time = time.time() - start_time
                    print(f"    [Groq-Fallback] Generated response in {api_time:.2f}s (model: {GROQ_MODEL})")

                    # Clean model-specific artifacts before returning
                    return self._clean_model_output(content)
                else:
                    raise ValueError(f"Unexpected Groq response format: {completion}")

            except Exception as e:
                last_error = e

                # Check if it's a rate limit error (429)
                error_str = str(e).lower()
                if '429' in error_str or 'rate limit' in error_str:
                    print(f"    [!]  Groq rate limit hit (429) during fallback!")
                    self.quota_manager.mark_exhausted("groq", reset_hours=24)
                    break  # Exit retry loop immediately

                if attempt < self.max_retries - 1:
                    delay = LLM_RETRY_DELAY * (2 ** attempt)
                    print(f"    [Groq-Fallback] Attempt {attempt + 1} failed, retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    print(f"    [Groq-Fallback] Error: {e}")

        # All retries failed
        error_msg = f"Groq fallback failed after {self.max_retries} attempts: {last_error}"
        print(f"    {error_msg}")
        raise Exception(error_msg)

    def _generate_gemini_fallback(self, prompt: str) -> str:
        """
        Generate text using Google Gemini API as fallback when OpenRouter fails.

        Uses gemini-2.0-flash-exp model by default (or GEMINI_MODEL from config).
        Free tier: 15 RPM, 1M tokens/min, 1500 requests/day
        """
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not configured - cannot use Gemini fallback")

        fallback_model = GEMINI_MODEL or "gemini-2.0-flash-exp"
        url = f"{GEMINI_BASE_URL}/models/{fallback_model}:generateContent?key={GEMINI_API_KEY}"

        headers = {
            "Content-Type": "application/json",
        }

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }

        last_error = None
        start_time = time.time()

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )
                response.raise_for_status()

                result = response.json()

                # Extract content from Gemini response
                # Response format: {"candidates": [{"content": {"parts": [{"text": "..."}]}}]}
                if "candidates" in result and len(result["candidates"]) > 0:
                    candidate = result["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        parts = candidate["content"]["parts"]
                        if len(parts) > 0 and "text" in parts[0]:
                            content = parts[0]["text"]

                            # Track successful request for quota detection
                            self._track_gemini_request()

                            gemini_time = time.time() - start_time
                            print(f"    [Gemini-Fallback] Generated response in {gemini_time:.2f}s (model: {fallback_model})")

                            # Clean model-specific artifacts before returning
                            return self._clean_model_output(content)

                raise ValueError(f"Unexpected Gemini response format: {result}")

            except requests.exceptions.RequestException as e:
                last_error = e

                # SMART DETECTION: If 429 on first attempt, immediately fallback (don't retry)
                if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
                    print(f"    [!]  Gemini fallback rate limit hit (429) - immediately switching to Ollama!")
                    # Determine quota type and mark as exhausted
                    reset_hours = self._determine_quota_reset_time(e.response)
                    self.quota_manager.mark_exhausted(self.mode, reset_hours=reset_hours)
                    break  # Exit retry loop immediately

                if attempt < self.max_retries - 1:
                    delay = LLM_RETRY_DELAY * (2 ** attempt)
                    print(f"    [Gemini] Attempt {attempt + 1} failed, retrying in {delay}s...")
                    time.sleep(delay)
            except (KeyError, ValueError) as e:
                last_error = e
                print(f"    [Gemini] Response parsing error: {e}")
                if attempt < self.max_retries - 1:
                    delay = LLM_RETRY_DELAY * (2 ** attempt)
                    print(f"    Retrying in {delay}s...")
                    time.sleep(delay)

        # All retries failed - mark quota as exhausted if 429 error
        is_rate_limit = (hasattr(last_error, 'response') and
                        last_error.response is not None and
                        last_error.response.status_code == 429)

        if is_rate_limit:
            # Determine quota type from response
            reset_hours = self._determine_quota_reset_time(last_error.response)
            self.quota_manager.mark_exhausted(self.mode, reset_hours=reset_hours)

        error_msg = f"Gemini fallback failed after {self.max_retries} attempts: {last_error}"
        print(f"    {error_msg}")
        raise Exception(error_msg)

    def _generate_gemini(self, prompt: str) -> str:
        """Generate text using Google Gemini API as primary (with Ollama fallback)."""
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not configured")

        # Thread-safe rate limiting: enforce minimum delay between API calls (separate for each model)
        if self.mode == "gemini_primary":
            lock = LLMService._gemini_primary_lock
            last_call_attr = '_last_gemini_primary_call'
            rate_limit = LLMService._gemini_primary_rate_limit
            model_label = "Gemini Primary"
        else:  # gemini_secondary
            lock = LLMService._gemini_secondary_lock
            last_call_attr = '_last_gemini_secondary_call'
            rate_limit = LLMService._gemini_secondary_rate_limit
            model_label = "Gemini Secondary"

        with lock:
            last_call = getattr(LLMService, last_call_attr)
            time_since_last_call = time.time() - last_call
            if time_since_last_call < rate_limit:
                sleep_time = rate_limit - time_since_last_call
                print(f"    [{model_label}] Rate limiting: waiting {sleep_time:.1f}s before API call...")
                time.sleep(sleep_time)

            # Update timestamp before making call (inside lock to prevent race conditions)
            setattr(LLMService, last_call_attr, time.time())

        url = f"{GEMINI_BASE_URL}/models/{self.model_name}:generateContent?key={GEMINI_API_KEY}"

        headers = {
            "Content-Type": "application/json",
        }

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }

        last_error = None
        start_time = time.time()

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )
                response.raise_for_status()

                result = response.json()

                # Extract content from Gemini response
                if "candidates" in result and len(result["candidates"]) > 0:
                    candidate = result["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        parts = candidate["content"]["parts"]
                        if len(parts) > 0 and "text" in parts[0]:
                            content = parts[0]["text"]

                            # Track successful request for quota detection
                            self._track_gemini_request()

                            gemini_time = time.time() - start_time
                            print(f"    [LLM-Gemini] Generated response in {gemini_time:.2f}s (model: {self.model_name})")

                            # Clean model-specific artifacts before returning
                            return self._clean_model_output(content)

                raise ValueError(f"Unexpected Gemini response format: {result}")

            except requests.exceptions.RequestException as e:
                last_error = e

                # SMART DETECTION: If 429 on first attempt, immediately fallback (don't retry)
                if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
                    print(f"    [!]  Gemini rate limit hit (429) - immediately switching to fallback!")
                    # Determine quota type and mark as exhausted
                    reset_hours = self._determine_quota_reset_time(e.response)
                    self.quota_manager.mark_exhausted(self.mode, reset_hours=reset_hours)
                    break  # Exit retry loop immediately

                if attempt < self.max_retries - 1:
                    delay = LLM_RETRY_DELAY * (2 ** attempt)
                    print(f"    [Gemini] Attempt {attempt + 1} failed, retrying in {delay}s...")
                    time.sleep(delay)
            except (KeyError, ValueError) as e:
                last_error = e
                print(f"    [Gemini] Response parsing error: {e}")
                if attempt < self.max_retries - 1:
                    delay = LLM_RETRY_DELAY * (2 ** attempt)
                    print(f"    Retrying in {delay}s...")
                    time.sleep(delay)

        # All retries failed - try fallback chain: OpenRouter → Ollama
        is_rate_limit = (hasattr(last_error, 'response') and
                        last_error.response is not None and
                        last_error.response.status_code == 429)

        # Note: Quota already marked as exhausted in smart detection above (on first 429)

        if is_rate_limit:
            print(f"    [!]  Gemini rate limit exhausted after {self.max_retries} attempts!")

            # Try Groq first (if enabled and configured)
            if LLM_ENABLE_GEMINI_FALLBACK and GROQ_API_KEY:
                print(f"    [>>] Falling back to Groq (API)...")
                try:
                    return self._generate_groq_fallback(prompt)
                except Exception as groq_error:
                    print(f"    [X] Groq fallback failed: {groq_error}")

                    # If Groq fails, try Ollama as final fallback
                    if LLM_ENABLE_OLLAMA_FALLBACK:
                        print(f"    [>>] Falling back to Ollama (local LLM) as final fallback...")
                        try:
                            return self._generate_ollama_fallback(prompt, stream=False)
                        except Exception as ollama_error:
                            print(f"    [X] Ollama fallback also failed: {ollama_error}")
                            print(f"    [i] Make sure Ollama is running: ollama serve")
                            error_msg = f"All LLM services failed: Gemini (rate limit), Groq ({groq_error}), Ollama ({ollama_error})"
                            raise Exception(error_msg)

                    # Groq failed but Ollama fallback disabled
                    error_msg = f"Gemini rate limit and Groq fallback failed: {groq_error}"
                    raise Exception(error_msg)

            # Groq not available, try Ollama directly
            elif LLM_ENABLE_OLLAMA_FALLBACK:
                print(f"    [>>] Falling back to Ollama (local LLM)...")
                try:
                    return self._generate_ollama_fallback(prompt, stream=False)
                except Exception as ollama_error:
                    print(f"    [X] Ollama fallback also failed: {ollama_error}")
                    print(f"    [i] Make sure Ollama is running: ollama serve")
                    error_msg = f"Both Gemini (rate limit) and Ollama (fallback) failed. Ollama error: {ollama_error}"
                    raise Exception(error_msg)

        else:
            # Not a rate limit error - try Ollama fallback if enabled
            if LLM_ENABLE_OLLAMA_FALLBACK:
                print(f"    [!]  Gemini failed after {self.max_retries} attempts!")
                print(f"    [>>] Falling back to Ollama (local LLM)...")
                try:
                    return self._generate_ollama_fallback(prompt, stream=False)
                except Exception as ollama_error:
                    print(f"    [X] Ollama fallback also failed: {ollama_error}")
                    print(f"    [i] Make sure Ollama is running: ollama serve")
                    error_msg = f"Both Gemini and Ollama failed. Gemini: {last_error}, Ollama: {ollama_error}"
                    raise Exception(error_msg)

        # No fallback enabled
        error_msg = f"Gemini generation failed after {self.max_retries} attempts: {last_error}"
        print(f"    {error_msg}")
        raise Exception(error_msg)

    def _generate_groq(self, prompt: str) -> str:
        """Generate text using Groq API with thread-safe rate limiting."""
        # Thread-safe rate limiting: enforce minimum delay between API calls
        with LLMService._groq_lock:
            time_since_last_call = time.time() - LLMService._last_groq_call
            if time_since_last_call < LLMService._groq_rate_limit:
                sleep_time = LLMService._groq_rate_limit - time_since_last_call
                print(f"    [Groq] Rate limiting: waiting {sleep_time:.1f}s before API call...")
                time.sleep(sleep_time)

            # Update timestamp before making call (inside lock to prevent race conditions)
            LLMService._last_groq_call = time.time()

        last_error = None
        start_time = time.time()

        for attempt in range(self.max_retries):
            try:
                # Initialize Groq client
                client = Groq(api_key=self.api_key)

                # Make API call using Groq SDK
                completion = client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=1,
                    max_completion_tokens=8192,
                    top_p=1,
                    stream=False,
                    stop=None
                )

                # Extract content from Groq response
                if completion.choices and len(completion.choices) > 0:
                    content = completion.choices[0].message.content

                    api_time = time.time() - start_time
                    print(f"    [LLM-Groq] Generated response in {api_time:.2f}s (model: {self.model_name})")

                    # Clean model-specific artifacts before returning
                    return self._clean_model_output(content)
                else:
                    raise ValueError(f"Unexpected Groq response format: {completion}")

            except Exception as e:
                last_error = e

                # SMART DETECTION: If 429 on first attempt, immediately fallback (don't retry)
                error_str = str(e).lower()
                if '429' in error_str or 'rate limit' in error_str:
                    print(f"    [!]  Groq rate limit hit (429) - immediately switching to fallback!")
                    # Mark as exhausted and break to fallback logic
                    self.quota_manager.mark_exhausted("groq", reset_hours=24)
                    break  # Exit retry loop immediately

                if attempt < self.max_retries - 1:
                    delay = LLM_RETRY_DELAY * (2 ** attempt)  # Exponential backoff for other errors
                    print(f"    [Groq] Attempt {attempt + 1} failed, retrying in {delay}s...")
                    time.sleep(delay)
                    # Update timestamp after retry delay to prevent immediate subsequent calls
                    with LLMService._groq_lock:
                        LLMService._last_groq_call = time.time()
                else:
                    print(f"    [Groq] Error: {e}")

        # All retries failed - check if we should fallback
        is_rate_limit = '429' in str(last_error).lower() or 'rate limit' in str(last_error).lower()

        # Note: Quota already marked as exhausted in smart detection above (on first 429)

        if is_rate_limit:
            # Try Gemini fallback first (if enabled)
            if LLM_ENABLE_GEMINI_FALLBACK:
                print(f"    [>>] Falling back to Google Gemini (free tier)...")
                try:
                    return self._generate_gemini_fallback(prompt)
                except Exception as gemini_error:
                    print(f"    [X] Gemini fallback failed: {gemini_error}")

                    # If Gemini fails, try Ollama as final fallback
                    if LLM_ENABLE_OLLAMA_FALLBACK:
                        print(f"    [>>] Falling back to Ollama (local LLM) as final fallback...")
                        try:
                            return self._generate_ollama_fallback(prompt, stream=False)
                        except Exception as ollama_error:
                            print(f"    [X] Ollama fallback also failed: {ollama_error}")
                            print(f"    [i] Make sure Ollama is running: ollama serve")
                            error_msg = f"All LLM services failed: Groq (rate limit), Gemini ({gemini_error}), Ollama ({ollama_error})"
                            raise Exception(error_msg)

                    # Gemini failed but Ollama fallback disabled
                    error_msg = f"Groq rate limit and Gemini fallback failed: {gemini_error}"
                    raise Exception(error_msg)

            # Gemini fallback disabled, try Ollama directly
            elif LLM_ENABLE_OLLAMA_FALLBACK:
                print(f"    [>>] Automatically falling back to Ollama (local LLM)...")
                try:
                    return self._generate_ollama_fallback(prompt, stream=False)
                except Exception as ollama_error:
                    print(f"    [X] Ollama fallback also failed: {ollama_error}")
                    print(f"    [i] Make sure Ollama is running: ollama serve")
                    error_msg = f"Both Groq (rate limit) and Ollama (fallback) failed. Ollama error: {ollama_error}"
                    raise Exception(error_msg)

        # No fallback or not a rate limit error - raise original error
        error_msg = f"Groq generation failed after {self.max_retries} attempts: {last_error}"
        print(f"    {error_msg}")
        raise Exception(error_msg)


def get_llm_service(mode: Optional[str] = None, **kwargs) -> LLMService:
    """
    Factory function to get LLM service instance.

    Args:
        mode: "ollama", "groq", or "gemini" (default: from LLM_MODE setting)
        **kwargs: Additional arguments to pass to LLMService

    Returns:
        LLMService instance configured for the specified mode
    """
    return LLMService(mode=mode, **kwargs)


def get_twitter_llm_service(**kwargs) -> LLMService:
    """
    Factory function to get LLM service configured for Twitter content generation.

    Uses TWITTER_CONTENT_* configuration if set, otherwise falls back to main pipeline config.
    This allows using different (cheaper/faster) models for Twitter vs main pipeline.

    Args:
        **kwargs: Additional arguments to pass to LLMService (will override Twitter config)

    Returns:
        LLMService instance configured for Twitter content generation
    """
    from config.settings import (
        TWITTER_CONTENT_MODE,
        TWITTER_CONTENT_MODEL,
        TWITTER_LLM_TIMEOUT,
        TWITTER_LLM_MAX_RETRIES,
        GROQ_MODEL,
        GEMINI_MODEL,
        OLLAMA_MODEL,
    )

    # Determine mode for Twitter content generation
    twitter_mode = kwargs.pop('mode', TWITTER_CONTENT_MODE)

    # Select model name if not provided
    if 'model_name' not in kwargs:
        if TWITTER_CONTENT_MODEL:
            # Use Twitter-specific model if configured
            kwargs['model_name'] = TWITTER_CONTENT_MODEL
        else:
            # Fall back to main pipeline model based on mode
            if twitter_mode == "ollama":
                kwargs['model_name'] = OLLAMA_MODEL
            elif twitter_mode == "groq":
                kwargs['model_name'] = GROQ_MODEL
            elif twitter_mode == "gemini":
                kwargs['model_name'] = GEMINI_MODEL

    # Use Twitter LLM settings if not overridden
    if 'timeout' not in kwargs:
        kwargs['timeout'] = TWITTER_LLM_TIMEOUT
    if 'max_retries' not in kwargs:
        kwargs['max_retries'] = TWITTER_LLM_MAX_RETRIES

    return LLMService(mode=twitter_mode, **kwargs)
