"""FastAPI application for FinAgent dashboard."""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.routes import events, outputs, evaluations, stats, selection, content, system, scheduling, twitter_content, auto_approval
from api.websocket import manager
from services.quota_manager import get_quota_manager

# APScheduler for periodic quota health checks
from apscheduler.schedulers.background import BackgroundScheduler

# Global scheduler
scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI app.
    Handles startup and shutdown events.
    """
    # Startup: Start quota auto-heal scheduler
    global scheduler
    scheduler = BackgroundScheduler()

    # Schedule auto-heal every 5 minutes
    qm = get_quota_manager()
    scheduler.add_job(
        qm.auto_heal_quotas,
        'interval',
        minutes=5,
        id='quota_auto_heal',
        name='Auto-heal quota tracking',
        replace_existing=True
    )

    scheduler.start()
    print("[FastAPI] Started quota auto-heal scheduler (runs every 5 minutes)")

    yield

    # Shutdown: Stop scheduler
    if scheduler:
        scheduler.shutdown()
        print("[FastAPI] Stopped quota auto-heal scheduler")

# Create FastAPI app
app = FastAPI(
    title="FinAgent API",
    description="API for FinAgent dashboard - content evaluation and management",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(events.router, prefix="/api/events", tags=["Events"])
app.include_router(outputs.router, prefix="/api/outputs", tags=["Outputs"])
app.include_router(evaluations.router, prefix="/api/evaluations", tags=["Evaluations"])
app.include_router(stats.router, prefix="/api/stats", tags=["Statistics"])
app.include_router(selection.router, prefix="/api", tags=["Selection"])
app.include_router(content.router, prefix="/api", tags=["Content"])
app.include_router(twitter_content.router, prefix="/api", tags=["Twitter"])
app.include_router(system.router, tags=["System"])
app.include_router(scheduling.router, prefix="/api/scheduling", tags=["Scheduling"])
app.include_router(auto_approval.router, prefix="/api/auto-approval", tags=["Auto-Approval"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "FinAgent API is running"}


@app.get("/api/health")
async def health_check():
    """Detailed health check."""
    from database.connection import check_db_connection

    db_ok = check_db_connection()
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
    }


@app.post("/internal/notify-output")
async def notify_output(data: dict):
    """
    Internal endpoint for pipeline to trigger WebSocket notifications.
    Called by DatabaseAdapter when new outputs are created.
    """
    output_id = data.get("output_id")
    event_id = data.get("event_id")
    event_type = data.get("event_type", "UNKNOWN")

    if output_id and event_id:
        await manager.notify_new_output(output_id, event_id, event_type)
        await manager.notify_stats_update()

    return {"status": "notified"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, wait for messages (ping/pong)
            data = await websocket.receive_text()
            # Echo back for ping/pong
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8001, reload=True)
