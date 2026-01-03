#!/usr/bin/env python3
"""
WebSocket Manager - Real-time Scanner Updates
Manages concurrent WebSocket connections for live option updates
"""

import logging
import json
from typing import Set, Dict, Any, List, Optional
from datetime import datetime
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage WebSocket connections and broadcast updates"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.connection_metadata[websocket] = {
            "connected_at": datetime.utcnow().isoformat(),
            "filters": {},
        }
        logger.info(
            f"WebSocket connected. Total connections: {len(self.active_connections)}"
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove disconnected WebSocket"""
        self.active_connections.discard(websocket)
        self.connection_metadata.pop(websocket, None)
        logger.info(
            f"WebSocket disconnected. Total connections: {len(self.active_connections)}"
        )

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return

        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                disconnected.add(connection)

        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_opportunities(
        self, opportunities: List[Dict[str, Any]], scan_metadata: Dict[str, Any] = None
    ) -> None:
        """Broadcast option opportunities to all clients"""
        message = {
            "type": "opportunities",
            "timestamp": datetime.utcnow().isoformat(),
            "count": len(opportunities),
            "opportunities": opportunities,
            "metadata": scan_metadata or {},
        }
        await self.broadcast(message)

    async def broadcast_status(
        self, status: str, details: Dict[str, Any] = None
    ) -> None:
        """Broadcast scanner status update"""
        message = {
            "type": "status",
            "timestamp": datetime.utcnow().isoformat(),
            "status": status,
            "details": details or {},
        }
        await self.broadcast(message)

    async def broadcast_error(self, error_msg: str, error_type: str = "error") -> None:
        """Broadcast error message to all clients"""
        message = {
            "type": error_type,
            "timestamp": datetime.utcnow().isoformat(),
            "message": error_msg,
        }
        await self.broadcast(message)

    async def send_personal_message(
        self, websocket: WebSocket, message: Dict[str, Any]
    ) -> None:
        """Send message to specific connection"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)

    def get_all_filters(self) -> List[Dict[str, Any]]:
        """Get filters from all connected clients"""
        return [
            {"filters": meta.get("filters", {})}
            for meta in self.connection_metadata.values()
        ]

    def set_client_filters(self, websocket: WebSocket, filters: Dict[str, Any]) -> None:
        """Store filters for specific client"""
        if websocket in self.connection_metadata:
            self.connection_metadata[websocket]["filters"] = filters


# Global instance
ws_manager = ConnectionManager()
