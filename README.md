# Async Workflow Graph Engine

A production-ready, async workflow engine built with Python (FastAPI). It supports complex graph execution, loops, conditional routing, and real-time WebSocket streaming.

## How to Run

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Configure Storage (Optional)**:
    ```bash
    # Linux/Mac: export STORAGE_TYPE=sqlite
    # Windows:    $env:STORAGE_TYPE="sqlite"
    ```
3.  **Start Server**:
    ```bash
    uvicorn app.main:app --reload
    ```
    API Docs available at: `http://localhost:8000/docs`

## Supported Features

*   **Graph Execution**: Chains nodes with conditional branching and loops.
*   **Async Core**: Non-blocking execution using `asyncio` and thread pools for sync tools.
*   **State Management**: Tracks input/output state at every step.
*   **Safe Evaluation**: Secure conditional logic without `eval()` vulnerabilities.
*   **Pluggable Storage**: InMemory (default) or SQLite persistence.
*   **Real-Time Streaming**: WebSocket endpoint for live execution logs.

## Future Improvements

With more time, I would prioritize:
*   **Distributed Execution**: Using Celery/Redis for scaling.
*   **Workflow Versioning**: To track changes to graph definitions.
*   **Visual Editor**: A UI for building graphs via drag-and-drop.
*   **Failure Recovery**: Robust retry policies and resume-from-failure logic.

---
**Documentation**:
*   [API & Examples](docs/API_REFERENCE.md)
*   [WebSocket Feature](WEBSOCKET_FEATURE.md)
