from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone

class EdgeDefinition(BaseModel):
    from_node: str
    to_node: str
    condition: Optional[str] = Field(None, description="Python expression to evaluate against state (e.g., 'quality_score < 5'). If true, this edge is taken.")

class NodeDefinition(BaseModel):
    id: str
    tool: str = Field(..., description="Name of the registered tool function to execute.")
    params: Dict[str, Any] = Field(default_factory=dict, description="Static parameters to pass to the tool.")

class GraphDefinition(BaseModel):
    nodes: List[NodeDefinition]
    edges: List[EdgeDefinition]
    start_node: str
    max_loops: int = Field(100, description="Safety limit for loops")

class WorkflowState(BaseModel):
    run_id: str
    graph_id: str
    status: str = "pending" # pending, running, completed, failed
    current_node: Optional[str] = None
    state: Dict[str, Any] = {}
    message: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class WorkflowStateWithLogs(WorkflowState):
    """Extended workflow state that includes execution logs."""
    logs: List['ExecutionStep'] = Field(default_factory=list)

class ExecutionStep(BaseModel):
    run_id: str
    node_id: str
    input_state: Dict[str, Any]
    output_state: Dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: float = 0.0
