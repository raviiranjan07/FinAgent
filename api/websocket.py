"""WebSocket manager for real-time updates."""

import json
from typing import List, Dict, Any
from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept and store a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WS] Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"[WS] Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients."""
        if not self.active_connections:
            return

        message_json = json.dumps(message)
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception:
                disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    async def notify_new_event(self, event_id: str, title: str, source: str):
        """Notify clients about a new event."""
        await self.broadcast({
            "type": "NEW_EVENT",
            "data": {
                "event_id": event_id,
                "title": title,
                "source": source,
            }
        })

    async def notify_new_output(self, output_id: str, event_id: str, event_type: str):
        """Notify clients about a new output."""
        await self.broadcast({
            "type": "NEW_OUTPUT",
            "data": {
                "output_id": output_id,
                "event_id": event_id,
                "event_type": event_type,
            }
        })

    async def notify_evaluation(self, evaluation_id: str, output_id: str, verdict: str):
        """Notify clients about a new evaluation."""
        await self.broadcast({
            "type": "NEW_EVALUATION",
            "data": {
                "evaluation_id": evaluation_id,
                "output_id": output_id,
                "verdict": verdict,
            }
        })

    async def notify_stats_update(self):
        """Notify clients to refresh stats."""
        await self.broadcast({
            "type": "STATS_UPDATE",
            "data": {}
        })


# Global instance
manager = ConnectionManager()
