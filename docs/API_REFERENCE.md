# API & Feature Reference

## API Endpoints

### Graph Management
- **POST** `/graph/create` - Create a new workflow graph
- **GET** `/graph/{graph_id}` - Retrieve graph definition
- **POST** `/graph/run` - Execute a workflow
- **GET** `/graph/state/{run_id}` - Get workflow execution status
- **GET** `/graph/state/{run_id}?include_logs=true` - Get status with execution logs
- **GET** `/graph/logs/{run_id}` - Get detailed execution logs
- **GET** `/tools` - List all registered tools

### Real-Time Streaming
- **WebSocket** `/graph/ws/run/{run_id}` - Stream execution logs in real-time

---

## Example Usage: Code Review Agent

### 1. Create a Graph
**POST** `/graph/create`
```json
{
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
```

### 2. Run Workflow
**POST** `/graph/run`
```json
{
  "graph_id": "<returned_graph_id>",
  "initial_state": {
    "code": "def hello():\n    print('world')\n    return True"
  }
}
```

---

## Technical Details

### How Conditions Work
Edges can have optional conditions evaluated using **safe expression evaluation**:

- **Supported**: `state['key']`, comparisons (`<`, `>`, `==`), boolean logic (`and`, `or`), arithmetic, and basic math functions (`len`, `max`).
- **Blocked**: `import`, `eval`, file operations.

### Edge Evaluation Order
1. **Conditional edges** first (in order).
2. **Unconditional edges** fallback.
3. No match = **Termination**.

### Custom Tools
Register tools using the decorator:

```python
@ToolRegistry.register()
def my_tool(state: Dict[str, Any]) -> Dict[str, Any]:
    return {"output": state.get("input") * 2}
```
