from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, WebSocket, WebSocketDisconnect
from typing import Dict, Any, List, Optional
import logging
from app.models.schemas import GraphDefinition, WorkflowState, WorkflowStateWithLogs, ExecutionStep
from app.core.engine import WorkflowEngine
from app.core.storage import BaseStorage, InMemoryStorage, SQLiteStorage
from app.core.websocket_manager import manager as ws_manager

logger = logging.getLogger(__name__)

router = APIRouter()

import os

# Storage Factory
_storage_instance = None

def get_storage() -> BaseStorage:
    global _storage_instance
    if _storage_instance:
        return _storage_instance
    
    storage_type = os.getenv("STORAGE_TYPE", "memory").lower()
    
    if storage_type == "sqlite":
        db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./workflow.db")
        _storage_instance = SQLiteStorage(db_url)
    else:
        _storage_instance = InMemoryStorage()
    
    return _storage_instance

def get_engine():
    return WorkflowEngine(get_storage())

@router.post("/create", response_model=Dict[str, str])
async def create_graph(definition: GraphDefinition, engine: WorkflowEngine = Depends(get_engine)):
    try:
        graph_id = await engine.create_graph(definition)
        return {"graph_id": graph_id, "message": "Graph created successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/run", response_model=Dict[str, str])
async def run_graph(
    payload: Dict[str, Any], 
    engine: WorkflowEngine = Depends(get_engine)
):
    """
    Payload expects:
    {
        "graph_id": "...",
        "initial_state": {}
    }
    """
    graph_id = payload.get("graph_id")
    initial_state = payload.get("initial_state", {})
    
    if not graph_id:
        raise HTTPException(status_code=400, detail="graph_id is required")

    try:
        run_id = await engine.start_run(graph_id, initial_state)
        return {"run_id": run_id, "status": "started"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/state/{run_id}")
async def get_state(
    run_id: str, 
    include_logs: Optional[bool] = Query(False, description="Include execution logs in response"),
    engine: WorkflowEngine = Depends(get_engine)
):
    """Get workflow state, optionally including execution logs."""
    state = await engine.storage.get_run(run_id)
    if not state:
        raise HTTPException(status_code=404, detail="Run not found")
    
    if include_logs:
        logs = await engine.storage.get_logs(run_id)
        # Return WorkflowStateWithLogs
        return WorkflowStateWithLogs(**state.model_dump(), logs=logs)
    
    return state

@router.get("/logs/{run_id}", response_model=List[ExecutionStep])
async def get_logs(run_id: str, engine: WorkflowEngine = Depends(get_engine)):
    """Get execution logs for a specific workflow run."""
    logs = await engine.storage.get_logs(run_id)
    if not logs:
        # Check if run exists
        run = await engine.storage.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        # Run exists but no logs yet
        return []
    return logs

@router.get("/{graph_id}", response_model=GraphDefinition)
async def get_graph(graph_id: str, engine: WorkflowEngine = Depends(get_engine)):
    """Get graph definition by ID."""
    graph = await engine.storage.get_graph(graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")
    return graph

@router.websocket("/ws/run/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str, engine: WorkflowEngine = Depends(get_engine)):
    """
    WebSocket endpoint for streaming workflow execution logs in real-time.
    
    Connect to ws://localhost:8000/graph/ws/run/{run_id} to receive:
    - Execution step logs as they happen
    - Status updates (running, completed, failed)
    - Real-time workflow progress
    
    Message format:
    {
        "type": "log" | "status",
        "run_id": "...",
        "node_id": "...",  # for type=log
        "status": "...",   # for type=status
        "data": {...}      # execution step data or state
    }
    """
    # Accept connection first
    await ws_manager.connect(websocket, run_id)
    
    # Check if run exists
    run = await engine.storage.get_run(run_id)
    if not run:
        await ws_manager.disconnect(websocket, run_id)
        await websocket.close(code=1008, reason="Run not found")
        return
    
    try:
        # Send initial status
        await ws_manager.broadcast_status(
            run_id, 
            run.status, 
            f"Connected to workflow {run_id}"
        )
        
        # Send existing logs if any
        logs = await engine.storage.get_logs(run_id)
        for log in logs:
            await ws_manager.broadcast_log(run_id, {
                "type": "log",
                "run_id": run_id,
                "node_id": log.node_id,
                "data": log.model_dump(mode="json")
            })
        
        # Keep connection alive and listen for client messages
        while True:
            try:
                # Receive any client messages (e.g., ping/pong)
                data = await websocket.receive_text()
                # Echo back or handle client requests if needed
                if data == "ping":
                    await websocket.send_text("pong")
            except WebSocketDisconnect:
                break
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    
    finally:
        await ws_manager.disconnect(websocket, run_id)

