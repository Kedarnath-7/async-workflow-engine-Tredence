"""WebSocket connection manager for streaming workflow execution logs."""
from typing import Dict, List
from fastapi import WebSocket
import asyncio
import json
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for workflow execution streaming."""
    
    def __init__(self):
        # Maps run_id to list of active WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, run_id: str):
        """Accept a new WebSocket connection for a specific run."""
        await websocket.accept()
        async with self._lock:
            if run_id not in self.active_connections:
                self.active_connections[run_id] = []
            self.active_connections[run_id].append(websocket)
        logger.info(f"WebSocket client connected for run_id: {run_id}")
    
    async def disconnect(self, websocket: WebSocket, run_id: str):
        """Remove a WebSocket connection."""
        async with self._lock:
            if run_id in self.active_connections:
                if websocket in self.active_connections[run_id]:
                    self.active_connections[run_id].remove(websocket)
                # Clean up empty lists
                if not self.active_connections[run_id]:
                    del self.active_connections[run_id]
        logger.info(f"WebSocket client disconnected for run_id: {run_id}")
    
    async def broadcast_log(self, run_id: str, log_data: dict):
        """Broadcast a log message to all connected clients for a run."""
        if run_id not in self.active_connections:
            return
        
        # Create a copy of connections to avoid modification during iteration
        async with self._lock:
            connections = self.active_connections.get(run_id, []).copy()
        
        # Prepare message
        message = json.dumps(log_data)
        
        # Send to all connected clients
        disconnected = []
        for connection in connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        if disconnected:
            async with self._lock:
                if run_id in self.active_connections:
                    for conn in disconnected:
                        if conn in self.active_connections[run_id]:
                            self.active_connections[run_id].remove(conn)
                    if not self.active_connections[run_id]:
                        del self.active_connections[run_id]
    
    async def broadcast_status(self, run_id: str, status: str, message: str = None):
        """Broadcast workflow status update."""
        status_data = {
            "type": "status",
            "run_id": run_id,
            "status": status,
            "message": message
        }
        await self.broadcast_log(run_id, status_data)
    
    async def get_connection_count(self, run_id: str) -> int:
        """Get number of active connections for a run."""
        async with self._lock:
            return len(self.active_connections.get(run_id, []))


# Global instance
manager = ConnectionManager()
