"""System control and status endpoints."""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any
import os
from pathlib import Path

from config import settings
from services.quota_manager import get_quota_manager

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
        timestamp=datetime.utcnow().isoformat()
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
