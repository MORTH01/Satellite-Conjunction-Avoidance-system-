"""
WebSocket connection manager for real-time alerts.
"""
import json
import logging
from typing import Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        if not self.active_connections:
            return
        data = json.dumps(message, default=str)
        dead = set()
        for ws in self.active_connections.copy():
            try:
                await ws.send_text(data)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.active_connections.discard(ws)

    async def send_personal(self, websocket: WebSocket, message: dict):
        data = json.dumps(message, default=str)
        try:
            await websocket.send_text(data)
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")


manager = ConnectionManager()
