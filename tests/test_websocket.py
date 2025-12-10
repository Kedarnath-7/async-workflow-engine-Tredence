"""
Integrated WebSocket Test - Creates a workflow and streams logs in real-time.

This test demonstrates the full WebSocket functionality by:
1. Creating a workflow graph
2. Starting workflow execution
3. Connecting via WebSocket to stream live logs
4. Verifying all logs are received
"""
import asyncio
import websockets
import requests
import json
import sys
import time


BASE_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000"


async def test_websocket_streaming():
    """Test WebSocket log streaming with a real workflow."""
    
    print("Running WebSocket Streaming Test...")
    
    # Step 1: Create graph
    print("[1/5] Creating workflow graph...")
    graph_def = {
        "nodes": [
            {"id": "extract", "tool": "extract_functions"},
            {"id": "complexity", "tool": "check_complexity"},
            {"id": "detect", "tool": "detect_issues"},
            {"id": "suggest", "tool": "suggest_improvements"}
        ],
        "edges": [
            {"from_node": "extract", "to_node": "complexity"},
            {"from_node": "complexity", "to_node": "detect"},
            {"from_node": "detect", "to_node": "suggest"},
            {
                "from_node": "suggest",
                "to_node": "detect",
                "condition": "state.get('quality_score', 0) < 8"
            }
        ],
        "start_node": "extract"
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/graph/create", json=graph_def)
        resp.raise_for_status()
        graph_id = resp.json()["graph_id"]
        print(f"      Graph created: {graph_id}")
    except Exception as e:
        print(f"[FAIL] Failed to create graph: {e}")
        return False
    
    # Step 2: Start workflow
    print("[2/5] Starting workflow execution...")
    run_payload = {
        "graph_id": graph_id,
        "initial_state": {
            "code": "def test():\n    print('hello')\n    x = 1\n    return x"
        }
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/graph/run", json=run_payload)
        resp.raise_for_status()
        run_id = resp.json()["run_id"]
        print(f"      Run started: {run_id}")
    except Exception as e:
        print(f"[FAIL] Failed to start workflow: {e}")
        return False
    
    # Step 3: Connect WebSocket and stream logs
    print("[3/5] Connecting to WebSocket...")
    uri = f"{WS_URL}/graph/ws/run/{run_id}"
    
    logs_received = []
    statuses_received = []
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"      Connected to {uri}")
            print("[4/5] Streaming execution logs...")
            
            async for message in websocket:
                data = json.loads(message)
                msg_type = data.get("type")
                
                if msg_type == "log":
                    node_id = data.get("node_id")
                    logs_received.append(node_id)
                    # print(f"      Log received: {node_id}")
                
                elif msg_type == "status":
                    status = data.get("status")
                    statuses_received.append(status)
                    # print(f"      Status update: {status}")
                    
                    if status in ["completed", "failed"]:
                        break
    
    except Exception as e:
        print(f"[FAIL] WebSocket error: {e}")
        return False
    
    # Step 4: Verify results
    print("[5/5] Verifying results...")
    
    # Check if we got all expected logs
    expected_nodes = ["extract", "complexity", "detect", "suggest"]
    all_nodes_present = all(node in logs_received for node in expected_nodes)
    
    if all_nodes_present and "completed" in statuses_received:
        print("[PASS] WebSocket Test Passed")
        return True
    else:
        print("[FAIL] WebSocket Test Failed")
        print(f"      Logs: {logs_received}")
        print(f"      Statuses: {statuses_received}")
        return False


async def main():
    """Main entry point."""
    # Check if server is running
    try:
        resp = requests.get(BASE_URL, timeout=2)
        if resp.status_code != 200:
            raise Exception("Server not responding correctly")
    except Exception as e:
        print(f"\n✗ Error: Cannot connect to server at {BASE_URL}")
        print("Please start the server first:")
        print("  uvicorn app.main:app --reload --port 8000")
        sys.exit(1)
    
    # Run the test
    success = await test_websocket_streaming()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(1)
