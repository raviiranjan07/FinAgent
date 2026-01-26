"""
Quota Manager - Tracks LLM API quota exhaustion and reset times.

Automatically switches between Groq, Gemini, and Ollama based on quota availability.
Persists quota state to disk to survive server restarts.
"""

import json
import os
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from pathlib import Path
from utils.timezone import get_ist_now

# IST is UTC+5:30
IST_OFFSET = timedelta(hours=5, minutes=30)


class QuotaManager:
    """
    Manages quota tracking for multiple LLM APIs.

    Features:
    - Persistent storage of quota state
    - Thread-safe operations
    - Automatic reset time calculation
    - Smart mode selection based on availability
    """

    # File to persist quota state
    QUOTA_FILE = ".quota_status.json"

    # Lock for thread-safe file operations
    _file_lock = threading.Lock()

    def __init__(self, quota_file: Optional[str] = None):
        """
        Initialize QuotaManager.

        Args:
            quota_file: Path to quota status file (default: .quota_status.json in project root)
        """
        self.quota_file = quota_file or self.QUOTA_FILE
        self._ensure_quota_file()
        self._check_and_reset_expired_quotas()

    def _ensure_quota_file(self):
        """Create quota file if it doesn't exist."""
        if not os.path.exists(self.quota_file):
            initial_state = {
                "groq": {
                    "exhausted": False,
                    "reset_at": None,
                    "last_429_at": None
                },
                "gemini_primary": {
                    "exhausted": False,
                    "reset_at": None,
                    "last_429_at": None
                },
                "gemini_secondary": {
                    "exhausted": False,
                    "reset_at": None,
                    "last_429_at": None
                },
                "last_updated": get_ist_now().isoformat()
            }
            self._write_quota_state(initial_state)

    def _read_quota_state(self) -> Dict[str, Any]:
        """Read quota state from file (thread-safe)."""
        with self._file_lock:
            try:
                with open(self.quota_file, 'r') as f:
                    return json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                # File corrupted or missing, recreate
                self._ensure_quota_file()
                with open(self.quota_file, 'r') as f:
                    return json.load(f)

    def _write_quota_state(self, state: Dict[str, Any]):
        """Write quota state to file (thread-safe)."""
        with self._file_lock:
            state["last_updated"] = get_ist_now().isoformat()
            with open(self.quota_file, 'w') as f:
                json.dump(state, f, indent=2)

    def _check_and_reset_expired_quotas(self):
        """
        Check if any quotas have expired and automatically reset them.
        Called on initialization to ensure quota file is up-to-date.
        """
        state = self._read_quota_state()
        now = get_ist_now()

        for api in ["groq", "gemini_primary", "gemini_secondary"]:
            api_state = state.get(api, {})

            # Skip if not exhausted
            if not api_state.get("exhausted", False):
                continue

            # Check if reset time has passed
            reset_at_str = api_state.get("reset_at")
            if reset_at_str:
                reset_at = datetime.fromisoformat(reset_at_str)

                if now >= reset_at:
                    # Reset time has passed, mark as available
                    reset_at_ist = reset_at + IST_OFFSET
                    now_ist = now + IST_OFFSET
                    print(f"[QuotaManager] {api.upper()} quota reset time passed (was: {reset_at_ist.strftime('%Y-%m-%d %H:%M IST')}, now: {now_ist.strftime('%Y-%m-%d %H:%M IST')})")
                    self.mark_available(api)

    def mark_exhausted(self, api: str, reset_hours: float = 24.0):
        """
        Mark an API as quota exhausted.

        Args:
            api: API name ("groq", "gemini_primary", or "gemini_secondary")
            reset_hours: Hours until quota resets (default: 24.0)
                        Can be fractional (e.g., 0.017 for 1 minute)
        """
        if api not in ["groq", "gemini_primary", "gemini_secondary"]:
            raise ValueError(f"Invalid API: {api}. Must be 'groq', 'gemini_primary', or 'gemini_secondary'")

        state = self._read_quota_state()
        now = get_ist_now()
        reset_at = now + timedelta(hours=reset_hours)

        state[api]["exhausted"] = True
        state[api]["reset_at"] = reset_at.isoformat()
        state[api]["last_429_at"] = now.isoformat()

        self._write_quota_state(state)

        # Determine quota type for logging
        quota_type = "MINUTE (15 RPM)" if reset_hours < 1 else "DAY (500 RPD)"

        # Convert to IST for display
        reset_at_ist = reset_at + IST_OFFSET
        print(f"[QuotaManager] {api.upper()} {quota_type} quota exhausted. Reset at: {reset_at_ist.strftime('%Y-%m-%d %H:%M IST')}")

    def is_available(self, api: str) -> bool:
        """
        Check if an API is available (quota not exhausted).

        Args:
            api: API name ("groq", "gemini_primary", or "gemini_secondary")

        Returns:
            True if API is available, False if quota exhausted
        """
        if api not in ["groq", "gemini_primary", "gemini_secondary"]:
            return True  # Ollama always available

        state = self._read_quota_state()
        api_state = state.get(api, {})

        # Check if marked as exhausted
        if not api_state.get("exhausted", False):
            return True

        # Check if reset time has passed
        reset_at_str = api_state.get("reset_at")
        if reset_at_str:
            reset_at = datetime.fromisoformat(reset_at_str)
            now = get_ist_now()

            if now >= reset_at:
                # Reset time passed, mark as available
                self.mark_available(api)
                return True

        return False

    def mark_available(self, api: str):
        """
        Mark an API as available (quota reset).

        Args:
            api: API name ("groq", "gemini_primary", or "gemini_secondary")
        """
        if api not in ["groq", "gemini_primary", "gemini_secondary"]:
            return

        state = self._read_quota_state()
        state[api]["exhausted"] = False
        state[api]["reset_at"] = None

        self._write_quota_state(state)

        print(f"[QuotaManager] {api.upper()} quota reset - now available")

    def get_best_available_mode(self, preferred_mode: str) -> str:
        """
        Get the best available LLM mode based on quota status.

        Fallback order (for gemini mode):
        1. Gemini Primary (gemini-2.5-flash-preview-09-202)
        2. Gemini Secondary (gemini-2.5-flash)
        3. Groq
        4. Ollama

        For groq/ollama modes:
        1. Preferred mode
        2. gemini_primary → gemini_secondary → groq → ollama

        Args:
            preferred_mode: User's preferred LLM mode ("groq", "gemini", "ollama")

        Returns:
            Best available mode ("gemini_primary", "gemini_secondary", "groq", or "ollama")
        """
        # Check ollama first (always available)
        if preferred_mode == "ollama":
            return "ollama"

        # For gemini mode: Try primary → secondary → groq → ollama
        if preferred_mode == "gemini":
            if self.is_available("gemini_primary"):
                return "gemini_primary"

            print(f"[QuotaManager] Gemini Primary exhausted, trying Secondary...")
            if self.is_available("gemini_secondary"):
                return "gemini_secondary"

            print(f"[QuotaManager] Both Gemini models exhausted, trying Groq...")
            if self.is_available("groq"):
                return "groq"

            print(f"[QuotaManager] All cloud APIs exhausted, using Ollama")
            return "ollama"

        # For groq mode: Try groq → gemini_primary → gemini_secondary → ollama
        if preferred_mode == "groq":
            if self.is_available("groq"):
                return "groq"

            print(f"[QuotaManager] Groq exhausted, trying Gemini Primary...")
            if self.is_available("gemini_primary"):
                return "gemini_primary"

            print(f"[QuotaManager] Gemini Primary exhausted, trying Secondary...")
            if self.is_available("gemini_secondary"):
                return "gemini_secondary"

            print(f"[QuotaManager] All cloud APIs exhausted, using Ollama")
            return "ollama"

        # Unknown mode, default to gemini primary
        return "gemini_primary"

    def get_status(self) -> Dict[str, Any]:
        """
        Get current quota status for all APIs.

        Returns:
            Dictionary with status for each API
        """
        state = self._read_quota_state()
        now = get_ist_now()

        status = {}
        for api in ["groq", "gemini_primary", "gemini_secondary"]:
            api_state = state.get(api, {})
            reset_at_str = api_state.get("reset_at")

            available = self.is_available(api)

            if reset_at_str and not available:
                reset_at = datetime.fromisoformat(reset_at_str)
                time_until_reset = reset_at - now
                hours = int(time_until_reset.total_seconds() / 3600)
                minutes = int((time_until_reset.total_seconds() % 3600) / 60)
                time_str = f"{hours}h {minutes}m"

                # Convert to IST for display
                reset_at_ist = reset_at + IST_OFFSET
                reset_at_ist_str = reset_at_ist.strftime('%Y-%m-%d %H:%M IST')
            else:
                time_str = "N/A"
                reset_at_ist_str = None

            # Convert last_429_at to IST if exists
            last_429_at = api_state.get("last_429_at")
            if last_429_at:
                last_429_dt = datetime.fromisoformat(last_429_at)
                last_429_ist = last_429_dt + IST_OFFSET
                last_429_ist_str = last_429_ist.strftime('%Y-%m-%d %H:%M IST')
            else:
                last_429_ist_str = None

            status[api] = {
                "available": available,
                "exhausted": api_state.get("exhausted", False),
                "reset_at": reset_at_str,  # Keep UTC for internal use
                "reset_at_ist": reset_at_ist_str,  # IST for display
                "time_until_reset": time_str if not available else "Available",
                "last_429_at": last_429_at,  # Keep UTC for internal use
                "last_429_at_ist": last_429_ist_str  # IST for display
            }

        # Ollama always available
        status["ollama"] = {
            "available": True,
            "exhausted": False,
            "reset_at": None,
            "time_until_reset": "Always available",
            "last_429_at": None
        }

        return status

    def reset_all(self):
        """Reset all quota tracking (for testing/debugging)."""
        state = self._read_quota_state()
        for api in ["groq", "gemini_primary", "gemini_secondary"]:
            state[api]["exhausted"] = False
            state[api]["reset_at"] = None
        self._write_quota_state(state)
        print("[QuotaManager] All quotas reset")

    def health_check_api(self, api: str) -> bool:
        """
        Perform health check on API to verify if it's actually available.

        Makes a minimal test request to check if quota is truly exhausted.
        If request succeeds, auto-reset the quota tracking.

        Args:
            api: API name ("groq", "gemini_primary", or "gemini_secondary")

        Returns:
            True if API is healthy, False if truly exhausted
        """
        if api not in ["groq", "gemini_primary", "gemini_secondary"]:
            return True

        # Skip health check if already marked as available
        if self.is_available(api):
            return True

        print(f"[QuotaManager] Health checking {api.upper()}...")

        try:
            if api == "gemini_primary":
                return self._health_check_gemini_primary()
            elif api == "gemini_secondary":
                return self._health_check_gemini_secondary()
            elif api == "groq":
                return self._health_check_groq()
        except Exception as e:
            print(f"[QuotaManager] Health check failed: {e}")
            return False

    def _health_check_gemini_primary(self) -> bool:
        """Health check for Gemini Primary API (gemini-2.5-flash-preview-09-202)."""
        import requests
        import os

        api_key = os.getenv('GEMINI_API_KEY')
        base_url = os.getenv('GEMINI_BASE_URL', 'https://generativelanguage.googleapis.com/v1beta')
        model = os.getenv('GEMINI_PRIMARY_MODEL', 'gemini-2.5-flash-preview-09-202')

        if not api_key:
            return False

        url = f"{base_url}/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": "test"}]}],
            "generationConfig": {"maxOutputTokens": 5}
        }

        try:
            response = requests.post(url, json=payload, timeout=5)

            if response.status_code == 200:
                print(f"[QuotaManager] [OK] Gemini Primary health check passed - resetting quota tracking")
                self.mark_available("gemini_primary")
                return True
            elif response.status_code == 429:
                print(f"[QuotaManager] [X] Gemini Primary still exhausted (429)")
                return False
            else:
                print(f"[QuotaManager] ? Gemini Primary returned {response.status_code}")
                return False
        except Exception as e:
            print(f"[QuotaManager] Gemini Primary health check error: {e}")
            return False

    def _health_check_gemini_secondary(self) -> bool:
        """Health check for Gemini Secondary API (gemini-2.5-flash)."""
        import requests
        import os

        api_key = os.getenv('GEMINI_API_KEY')
        base_url = os.getenv('GEMINI_BASE_URL', 'https://generativelanguage.googleapis.com/v1beta')
        model = os.getenv('GEMINI_SECONDARY_MODEL', 'gemini-2.5-flash')

        if not api_key:
            return False

        url = f"{base_url}/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": "test"}]}],
            "generationConfig": {"maxOutputTokens": 5}
        }

        try:
            response = requests.post(url, json=payload, timeout=5)

            if response.status_code == 200:
                print(f"[QuotaManager] [OK] Gemini Secondary health check passed - resetting quota tracking")
                self.mark_available("gemini_secondary")
                return True
            elif response.status_code == 429:
                print(f"[QuotaManager] [X] Gemini Secondary still exhausted (429)")
                return False
            else:
                print(f"[QuotaManager] ? Gemini Secondary returned {response.status_code}")
                return False
        except Exception as e:
            print(f"[QuotaManager] Gemini Secondary health check error: {e}")
            return False

    def _health_check_groq(self) -> bool:
        """Health check for Groq API."""
        import requests
        import os

        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            return False

        url = "https://api.groq.com/openai/v1/models"
        headers = {"Authorization": f"Bearer {api_key}"}

        try:
            response = requests.get(url, headers=headers, timeout=5)

            if response.status_code == 200:
                print(f"[QuotaManager] [OK] Groq health check passed - resetting quota tracking")
                self.mark_available("groq")
                return True
            elif response.status_code == 429:
                print(f"[QuotaManager] [X] Groq still exhausted (429)")
                return False
            else:
                print(f"[QuotaManager] ? Groq returned {response.status_code}")
                return False
        except Exception as e:
            print(f"[QuotaManager] Groq health check error: {e}")
            return False

    def auto_heal_quotas(self):
        """
        Auto-heal quota tracking by checking if exhausted APIs are actually available.

        This should be called periodically to prevent false "exhausted" states.
        Recommended: Run every 5 minutes.
        """
        state = self._read_quota_state()

        for api in ["groq", "gemini_primary", "gemini_secondary"]:
            api_state = state.get(api, {})

            if api_state.get("exhausted", False):
                print(f"[QuotaManager] {api.upper()} marked as exhausted - performing health check")
                self.health_check_api(api)


# Global singleton instance
_quota_manager = None

def get_quota_manager() -> QuotaManager:
    """Get global QuotaManager instance (singleton)."""
    global _quota_manager
    if _quota_manager is None:
        _quota_manager = QuotaManager()
    return _quota_manager
