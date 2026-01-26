"""System control and status endpoints."""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any
import os
from pathlib import Path

from config import settings
from services.quota_manager import get_quota_manager
from utils.timezone import get_ist_now

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================

class SystemStatus(BaseModel):
    """System operational status."""
    status: str
    content_generation_enabled: bool
    publishing_enabled: bool
    prompt_version: str
    twitter_prompt_version: str
    llm_mode_configured: str
    llm_mode_active: str
    quota_status: Dict[str, Any]
    timestamp: str


class OperationResponse(BaseModel):
    """Response for control operations."""
    message: str
    requires_restart: bool = False


# =============================================================================
# Public Endpoints
# =============================================================================

@router.get("/api/system/status", response_model=SystemStatus)
def get_system_status():
    """
    Get current system operational status.

    Public endpoint - shows whether content generation and publishing are enabled,
    plus LLM quota status for all APIs.
    """
    # Get quota manager and check status
    qm = get_quota_manager()
    quota_status = qm.get_status()

    # Get active LLM mode (after quota-based fallback)
    configured_mode = settings.LLM_MODE
    active_mode = qm.get_best_available_mode(configured_mode)

    return SystemStatus(
        status="operational",
        content_generation_enabled=settings.CONTENT_GENERATION_ENABLED,
        publishing_enabled=settings.TWITTER_PUBLISHING_ENABLED,  # Use Twitter-specific setting
        prompt_version=settings.PROMPT_VERSION,
        twitter_prompt_version=settings.TWITTER_PROMPT_VERSION,
        llm_mode_configured=configured_mode,
        llm_mode_active=active_mode,
        quota_status=quota_status,
        timestamp=get_ist_now().isoformat()
    )


# =============================================================================
# Admin Control Endpoints
# =============================================================================

def verify_admin_token(token: Optional[str]) -> bool:
    """
    Verify admin authentication token.

    In production, this should validate against a secure token store.
    For now, uses ADMIN_TOKEN from environment variable.
    """
    if not token:
        return False

    admin_token = os.getenv("ADMIN_TOKEN", "")
    if not admin_token:
        # No admin token configured - reject all admin requests
        return False

    return token == admin_token


@router.post("/api/system/content-generation/disable", response_model=OperationResponse)
def disable_content_generation(authorization: Optional[str] = Header(None)):
    """
    Disable content generation system-wide.

    Requires admin authentication via Authorization header.
    After disabling, the pipeline will stop generating new content.

    Usage:
        Authorization: Bearer <ADMIN_TOKEN>
    """
    # Extract token from "Bearer <token>" format
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]

    if not verify_admin_token(token):
        raise HTTPException(status_code=401, detail="Unauthorized - Invalid or missing admin token")

    # Update the setting (in-memory)
    settings.CONTENT_GENERATION_ENABLED = False

    return OperationResponse(
        message="Content generation disabled. Pipeline will stop on next run.",
        requires_restart=False  # Takes effect immediately
    )


@router.post("/api/system/content-generation/enable", response_model=OperationResponse)
def enable_content_generation(authorization: Optional[str] = Header(None)):
    """
    Enable content generation system-wide.

    Requires admin authentication via Authorization header.
    """
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]

    if not verify_admin_token(token):
        raise HTTPException(status_code=401, detail="Unauthorized - Invalid or missing admin token")

    settings.CONTENT_GENERATION_ENABLED = True

    return OperationResponse(
        message="Content generation enabled.",
        requires_restart=False
    )


@router.post("/api/system/publishing/disable", response_model=OperationResponse)
def disable_publishing(authorization: Optional[str] = Header(None)):
    """
    Emergency stop: Disable publishing to all platforms.

    Requires admin authentication via Authorization header.
    This is the kill switch for stopping content from being published.

    Usage:
        Authorization: Bearer <ADMIN_TOKEN>
    """
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]

    if not verify_admin_token(token):
        raise HTTPException(status_code=401, detail="Unauthorized - Invalid or missing admin token")

    settings.TWITTER_PUBLISHING_ENABLED = False

    return OperationResponse(
        message="Publishing disabled immediately. No content will be published to platforms.",
        requires_restart=False
    )


@router.post("/api/system/publishing/enable", response_model=OperationResponse)
def enable_publishing(authorization: Optional[str] = Header(None)):
    """
    Enable publishing to all platforms.

    Requires admin authentication via Authorization header.
    """
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]

    if not verify_admin_token(token):
        raise HTTPException(status_code=401, detail="Unauthorized - Invalid or missing admin token")

    settings.TWITTER_PUBLISHING_ENABLED = True

    return OperationResponse(
        message="Publishing enabled.",
        requires_restart=False
    )


# =============================================================================
# Quota Management Endpoints
# =============================================================================

@router.post("/api/system/quota/reset/{api}", response_model=OperationResponse)
def reset_quota(api: str, authorization: Optional[str] = Header(None)):
    """
    Manually reset quota tracking for a specific API.

    Useful when quota tracker shows false "exhausted" state.

    Args:
        api: API name ("groq", "gemini", or "all")

    Requires admin authentication via Authorization header.
    """
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]

    if not verify_admin_token(token):
        raise HTTPException(status_code=401, detail="Unauthorized - Invalid or missing admin token")

    qm = get_quota_manager()

    if api.lower() == "all":
        qm.reset_all()
        return OperationResponse(
            message="All quota tracking reset successfully.",
            requires_restart=False
        )
    elif api.lower() in ["groq", "gemini"]:
        qm.mark_available(api.lower())
        return OperationResponse(
            message=f"{api.upper()} quota tracking reset successfully.",
            requires_restart=False
        )
    else:
        raise HTTPException(status_code=400, detail=f"Invalid API: {api}. Must be 'groq', 'gemini', or 'all'")


@router.post("/api/system/quota/health-check/{api}", response_model=OperationResponse)
def health_check_quota(api: str, authorization: Optional[str] = Header(None)):
    """
    Perform health check on API to verify if it's actually available.

    Makes a test request to check if quota is truly exhausted.
    Auto-resets quota tracking if API responds successfully.

    Args:
        api: API name ("groq", "gemini", or "all")

    Requires admin authentication via Authorization header.
    """
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]

    if not verify_admin_token(token):
        raise HTTPException(status_code=401, detail="Unauthorized - Invalid or missing admin token")

    qm = get_quota_manager()

    if api.lower() == "all":
        qm.auto_heal_quotas()
        return OperationResponse(
            message="Health check performed on all exhausted APIs.",
            requires_restart=False
        )
    elif api.lower() in ["groq", "gemini"]:
        is_healthy = qm.health_check_api(api.lower())
        if is_healthy:
            return OperationResponse(
                message=f"{api.upper()} is healthy and available.",
                requires_restart=False
            )
        else:
            return OperationResponse(
                message=f"{api.upper()} is still exhausted or unavailable.",
                requires_restart=False
            )
    else:
        raise HTTPException(status_code=400, detail=f"Invalid API: {api}. Must be 'groq', 'gemini', or 'all'")


# =============================================================================
# Ingestion Worker Endpoints
# =============================================================================

@router.get("/api/system/ingestion/health")
def get_ingestion_worker_health():
    """
    Check RSS ingestion worker health status.

    This endpoint:
    - Reads worker heartbeat file
    - Determines if worker is alive (heartbeat within last interval + 5 minutes)
    - Returns worker stats (events processed, success count, last run time)

    Returns:
        Worker health status with metrics
    """
    from datetime import timedelta

    HEARTBEAT_FILE = os.getenv("INGESTION_HEARTBEAT_FILE", "/tmp/rss_ingestion_worker_heartbeat.txt")
    INGESTION_INTERVAL_HOURS = float(os.getenv("INGESTION_INTERVAL_HOURS", 4))

    # Check if heartbeat file exists
    if not os.path.exists(HEARTBEAT_FILE):
        return {
            "is_alive": False,
            "status": "offline",
            "message": "Worker has never started (no heartbeat file)",
            "heartbeat_file": HEARTBEAT_FILE
        }

    # Read heartbeat file
    try:
        with open(HEARTBEAT_FILE, 'r') as f:
            lines = f.readlines()

        if not lines:
            return {
                "is_alive": False,
                "status": "offline",
                "message": "Heartbeat file is empty"
            }

        # Parse heartbeat data
        heartbeat_data = {}
        last_heartbeat_str = lines[0].strip()
        last_heartbeat = datetime.fromisoformat(last_heartbeat_str)

        for line in lines[1:]:
            if ':' in line:
                key, value = line.strip().split(':', 1)
                heartbeat_data[key.strip()] = value.strip()

        # Determine if worker is alive
        # Worker should update heartbeat after each run or during idle
        # Allow interval + 5 minutes grace period
        now = get_ist_now()
        max_gap = timedelta(hours=INGESTION_INTERVAL_HOURS, minutes=5)
        time_since_heartbeat = now - last_heartbeat
        is_alive = time_since_heartbeat < max_gap

        # Get status from heartbeat
        worker_status = heartbeat_data.get('status', 'unknown')

        return {
            "is_alive": is_alive,
            "status": "active" if is_alive else "stale",
            "worker_status": worker_status,
            "last_heartbeat": last_heartbeat.isoformat(),
            "time_since_heartbeat_seconds": int(time_since_heartbeat.total_seconds()),
            "success_count": int(heartbeat_data.get('success_count', 0)),
            "failure_count": int(heartbeat_data.get('failure_count', 0)),
            "events_processed": int(heartbeat_data.get('events_processed', 0)),
            "last_run_time": heartbeat_data.get('last_run_time'),
            "last_error": heartbeat_data.get('last_error'),
            "interval_hours": INGESTION_INTERVAL_HOURS
        }

    except Exception as e:
        return {
            "is_alive": False,
            "status": "error",
            "error": str(e)
        }


@router.post("/api/system/ingestion/trigger", response_model=OperationResponse)
def trigger_ingestion(authorization: Optional[str] = Header(None)):
    """
    Manually trigger RSS ingestion pipeline.

    Runs the pipeline in a background subprocess. Does not wait for completion.

    Requires admin authentication via Authorization header.

    Usage:
        Authorization: Bearer <ADMIN_TOKEN>
    """
    import subprocess
    import sys as system_module
    import threading

    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]

    if not verify_admin_token(token):
        raise HTTPException(status_code=401, detail="Unauthorized - Invalid or missing admin token")

    # Run pipeline in background thread
    def run_pipeline_subprocess():
        subprocess.run([
            system_module.executable,
            "run_pipeline.py"
        ])

    thread = threading.Thread(target=run_pipeline_subprocess, daemon=True)
    thread.start()

    return OperationResponse(
        message="RSS ingestion pipeline triggered. Running in background.",
        requires_restart=False
    )
