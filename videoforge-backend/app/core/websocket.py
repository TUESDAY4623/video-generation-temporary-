"""WebSocket connection manager for real-time pipeline updates."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections per project."""

    def __init__(self) -> None:
        # project_id -> list of active connections
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, project_id: str, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        if project_id not in self._connections:
            self._connections[project_id] = []
        self._connections[project_id].append(websocket)
        logger.info(f"WebSocket connected for project {project_id}")

    def disconnect(self, project_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if project_id in self._connections:
            try:
                self._connections[project_id].remove(websocket)
            except ValueError:
                pass
            if not self._connections[project_id]:
                del self._connections[project_id]
        logger.info(f"WebSocket disconnected for project {project_id}")

    async def send_event(self, project_id: str, event: dict[str, Any]) -> None:
        """Send an event to all connections for a project."""
        if project_id not in self._connections:
            return

        payload = json.dumps(event, default=str)
        dead_connections: list[WebSocket] = []

        for connection in self._connections[project_id]:
            try:
                await connection.send_text(payload)
            except Exception:
                dead_connections.append(connection)

        # Clean up dead connections
        for dead in dead_connections:
            self.disconnect(project_id, dead)

    async def broadcast(self, event: dict[str, Any]) -> None:
        """Broadcast an event to ALL connected projects."""
        for project_id in list(self._connections.keys()):
            await self.send_event(project_id, event)

    def connection_count(self, project_id: str | None = None) -> int:
        """Count active connections."""
        if project_id:
            return len(self._connections.get(project_id, []))
        return sum(len(v) for v in self._connections.values())


# Global singleton
manager = ConnectionManager()
