"""Quick test of the workflow engine without starting a server."""
import asyncio
import sys
sys.path.insert(0, r'c:\Users\ASUS\Downloads\Tredence Assignment')

from app.core.engine import WorkflowEngine
from app.core.storage import InMemoryStorage
from app.models.schemas import GraphDefinition, NodeDefinition, EdgeDefinition

async def test_workflow():
    print("\n=== Testing Workflow Engine ===\n")
    
    # Create engine
    storage = InMemoryStorage()
    engine = WorkflowEngine(storage)
    
    # Define graph
    graph_def = GraphDefinition(
        nodes=[
            NodeDefinition(id="extract", tool="extract_functions"),
            NodeDefinition(id="complexity", tool="check_complexity"),
            NodeDefinition(id="detect", tool="detect_issues"),
            NodeDefinition(id="suggest", tool="suggest_improvements")
        ],
        edges=[
            EdgeDefinition(from_node="extract", to_node="complexity"),
            EdgeDefinition(from_node="complexity", to_node="detect"),
            EdgeDefinition(from_node="detect", to_node="suggest"),
            EdgeDefinition(
                from_node="suggest",
                to_node="detect",
                condition="state.get('quality_score', 0) < 8"
            )
        ],
        start_node="extract"
    )
    
    # Create graph
    print("1. Creating graph...")
    graph_id = await engine.create_graph(graph_def)
    print(f"   Graph ID: {graph_id}")
    
    # Run workflow
    print("\n2. Starting workflow...")
    initial_state = {
        "code": "def bad_code():\n    print('test')\n    x = 1\n    y = 2\n    return x + y"
    }
    run_id = await engine.start_run(graph_id, initial_state)
    print(f"   Run ID: {run_id}")
    
    # Poll for completion
    print("\n3. Waiting for completion...")
    for i in range(20):
        await asyncio.sleep(0.5)
        state = await storage.get_run(run_id)
        if state:
            status = state.status
            quality = state.state.get("quality_score", "N/A")
            node = state.current_node or "END"
            print(f"   Iteration {i+1}: {status} | Node: {node} | Quality: {quality}")
            
            if status in ["completed", "failed"]:
                break
    
    # Get final state
    final_state = await storage.get_run(run_id)
    print(f"\n4. Final Results:")
    print(f"   Status: {final_state.status}")
    print(f"   Quality Score: {final_state.state.get('quality_score', 'N/A')}")
    print(f"   Issue Count: {final_state.state.get('issue_count', 'N/A')}")
    print(f"   Iterations: {final_state.state.get('iteration', 'N/A')}")
    
    # Get logs
    logs = await storage.get_logs(run_id)
    print(f"\n5. Execution Logs: {len(logs)} steps")
    for i, log in enumerate(logs):
        print(f"   Step {i+1}: {log.node_id} ({log.duration_ms:.2f}ms)")
    
    # Verify success
    if final_state.status == "completed" and final_state.state.get('quality_score', 0) >= 9:
        print("\n=== ALL TESTS PASSED ===")
        return True
    else:
        print(f"\n=== TEST FAILED === Status: {final_state.status}")
        return False

if __name__ == "__main__":
    # Import tools to register them
    import app.examples.code_review
    
    result = asyncio.run(test_workflow())
    sys.exit(0 if result else 1)
