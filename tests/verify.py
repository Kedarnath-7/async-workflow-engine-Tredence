import requests
import time
import json
import sys

BASE_URL = "http://localhost:8000"

def run_test():
    print("1. Creating Graph...")
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
        print(f"Graph Created: {graph_id}")
    except Exception as e:
        print(f"Failed to create graph: {e}")
        print(resp.text)
        return

    print("\n2. Running Workflow...")
    run_payload = {
        "graph_id": graph_id,
        "initial_state": {
            "code": "def terrible_function():\n    print('This is a very long function that does nothing useful but takes up space and ignores standards.')\n    a = 1\n    b = 2\n    c = 3\n    return a+b+c"
        }
    }
    
    resp = requests.post(f"{BASE_URL}/graph/run", json=run_payload)
    run_id = resp.json()["run_id"]
    print(f"Run Started: {run_id}")

    print("\n3. Polling Status...")
    for _ in range(10):
        resp = requests.get(f"{BASE_URL}/graph/state/{run_id}")
        state = resp.json()
        status = state["status"]
        current_node = state.get("current_node")
        quality = state.get("state", {}).get("quality_score", "N/A")
        print(f"Status: {status}, Node: {current_node}, Quality: {quality}")
        
        if status in ["completed", "failed"]:
            break
        time.sleep(1)

    print("\n4. Final State:")
    print(json.dumps(state, indent=2))

if __name__ == "__main__":
    # Check if server is running
    try:
        requests.get(BASE_URL)
    except requests.exceptions.ConnectionError:
        print("Server not running. Please start 'uvicorn app.main:app' in another terminal.")
        sys.exit(1)
        
    run_test()
