# WebSocket Implementation

## Feature Summary

The WebSocket feature has been implemented to provide real-time streaming of workflow execution logs.

## Implementation Details

### 1. WebSocket Manager (`app/core/websocket_manager.py`)
- `ConnectionManager` class for managing WebSocket connections.
- Thread-safe connection management using `asyncio.Lock`.
- Methods for broadcasting logs and status updates to connected clients.

### 2. WebSocket Endpoint (`app/api/routes.py`)
- **Route**: `GET /graph/ws/run/{run_id}`
- Validates `run_id` before connection.
- Streams historical logs upon connection.
- Streams live logs during execution.
- Implements ping/pong for keep-alive.

### 3. Engine Integration (`app/core/engine.py`)
Broadcasting triggers:
- Workflow status changes (start, complete, fail).
- Execution step completion.
- Error events.

## Usage

### 1. Start Server
```bash
uvicorn app.main:app --port 8000
```

### 2. Connect Client
Clients can connect to `ws://localhost:8000/graph/ws/run/{run_id}`.

**Message Format (Log):**
```json
{
  "type": "log",
  "run_id": "...",
  "node_id": "...",
  "data": {
    "timestamp": "...",
    "duration_ms": 10.5,
    "input_state": {...},
    "output_state": {...}
  }
}
```

**Message Format (Status):**
```json
{
  "type": "status",
  "run_id": "...",
  "status": "running|completed|failed",
  "message": "Description"
}
```

## Testing

**Integration Test:**
```bash
python test_websocket.py
```
**Client Example:**
```bash
python websocket_client_example.py <run_id>
```
