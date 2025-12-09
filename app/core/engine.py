import asyncio
import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from simpleeval import simple_eval, NameNotDefined
from app.models.schemas import GraphDefinition, WorkflowState, ExecutionStep, NodeDefinition
from app.core.registry import ToolRegistry
from app.core.storage import BaseStorage

logger = logging.getLogger(__name__)

class WorkflowEngine:
    def __init__(self, storage: BaseStorage):
        self.storage = storage

    async def validate_graph(self, definition: GraphDefinition):
        """Validates the graph definition."""
        # 1. Check tools exist
        for node in definition.nodes:
            if not ToolRegistry.exists(node.tool):
                raise ValueError(f"Tool '{node.tool}' not found in registry (Node: {node.id}).")

        # 2. Check edges point to valid nodes
        node_ids = {n.id for n in definition.nodes}
        if definition.start_node not in node_ids:
            raise ValueError(f"Start node '{definition.start_node}' does not exist in nodes.")
        
        for edge in definition.edges:
            if edge.from_node not in node_ids:
                raise ValueError(f"Edge source '{edge.from_node}' does not exist.")
            if edge.to_node not in node_ids:
                raise ValueError(f"Edge target '{edge.to_node}' does not exist.")

        # 3. Validation passed

    async def create_graph(self, definition: GraphDefinition) -> str:
        await self.validate_graph(definition)
        graph_id = str(uuid.uuid4())
        await self.storage.save_graph(graph_id, definition)
        return graph_id

    async def start_run(self, graph_id: str, initial_state: Dict[str, Any]) -> str:
        graph = await self.storage.get_graph(graph_id)
        if not graph:
            raise ValueError(f"Graph {graph_id} not found.")

        run_id = str(uuid.uuid4())
        state = WorkflowState(
            run_id=run_id,
            graph_id=graph_id,
            status="running",
            current_node=graph.start_node,
            state=initial_state
        )
        await self.storage.save_run(state)
        
        # Start execution in background (fire and forget or monitored externally)
        # For this async implementation, we'll return run_id immediately and let the caller 
        # await the execution or spawn a task. 
        # Ideally, we spawn a background task here.
        asyncio.create_task(self._execute_workflow(run_id, graph, state))
        
        return run_id

    async def _execute_workflow(self, run_id: str, graph: GraphDefinition, run_state: WorkflowState):
        # Import here to avoid circular dependency
        from app.core.websocket_manager import manager as ws_manager
        
        try:
            # Small delay to allow WebSocket clients to connect before execution starts
            await asyncio.sleep(0.1)
            
            # Broadcast workflow started
            await ws_manager.broadcast_status(run_id, "running", "Workflow execution started")
            
            loop_counters: Dict[str, int] = {} # Track node visits for loop updates if needed, primarily for infinite loop protection

            while run_state.current_node:
                # 1. Get Node
                node_def = next((n for n in graph.nodes if n.id == run_state.current_node), None)
                if not node_def:
                    raise ValueError(f"Node {run_state.current_node} definition missing during execution.")

                # 2. Execute Tool
                tool_func = ToolRegistry.get_tool(node_def.tool)
                if not tool_func:
                    raise ValueError(f"Tool {node_def.tool} missing.")

                # Capture input state before execution
                input_snapshot = run_state.state.copy()
                start_time = datetime.now(timezone.utc)
                
                # Combine state and params. State keys overwrite params if collision (or vice-versa depending on design).
                # Here: Pass 'state' as a generic argument, or unpack? 
                # Requirement: "modify a shared state".
                # Let's pass the state dict to the function. 
                # NOTE: Tools should accept 'state' and optionally other params.
                
                try:
                    # Execute tool
                    # Support both async and sync tools
                    # Production fix: Run sync tools in thread pool to avoid blocking the event loop
                    if asyncio.iscoroutinefunction(tool_func):
                        result = await tool_func(run_state.state, **node_def.params)
                    else:
                        result = await asyncio.get_running_loop().run_in_executor(
                            None, 
                            lambda: tool_func(run_state.state, **node_def.params)
                        )
                    
                    # Update state
                    if isinstance(result, dict):
                        run_state.state.update(result)
                    
                except Exception as e:
                    run_state.status = "failed"
                    run_state.message = f"Error in node {node_def.id}: {str(e)}"
                    await self.storage.save_run(run_state)
                    await ws_manager.broadcast_status(run_id, "failed", run_state.message)
                    return

                end_time = datetime.now(timezone.utc)
                duration = (end_time - start_time).total_seconds() * 1000

                # 3. Log Step
                log = ExecutionStep(
                    run_id=run_id,
                    node_id=node_def.id,
                    input_state=input_snapshot,
                    output_state=run_state.state.copy(), # Snapshot
                    timestamp=end_time,
                    duration_ms=duration
                )
                await self.storage.add_log(log)
                
                # Broadcast log to WebSocket clients
                await ws_manager.broadcast_log(run_id, {
                    "type": "log",
                    "run_id": run_id,
                    "node_id": node_def.id,
                    "data": log.model_dump(mode="json")
                })

                # 4. Determine Next Node (Routing)
                next_node_id = None
                
                # Find edges from current node
                edges = [e for e in graph.edges if e.from_node == run_state.current_node]
                
                for edge in edges:
                    if edge.condition:
                        # Safe Evaluation using simpleeval (no access to __builtins__, imports, etc.)
                        try:
                            # simpleeval provides safe evaluation without access to dangerous functions
                            # Allowed: Basic comparisons, arithmetic, dict/list access
                            # Blocked: imports, file operations, exec, eval, __builtins__
                            names = {"state": run_state.state}
                            functions = {"len": len, "max": max, "min": min, "abs": abs, "sum": sum}
                            
                            result = simple_eval(edge.condition, names=names, functions=functions)
                            if result:
                                next_node_id = edge.to_node
                                break
                        except (NameNotDefined, SyntaxError, KeyError, Exception) as e:
                            logger.error(f"Condition evaluation failed for edge {edge.from_node}->{edge.to_node}: {e}")
                            continue # Try next edge
                    else:
                        # Unconditional edge (default)
                        next_node_id = edge.to_node
                        break # Take first unconditional edge found
                
                # Loop safety
                loop_counters[run_state.current_node] = loop_counters.get(run_state.current_node, 0) + 1
                if loop_counters[run_state.current_node] > graph.max_loops:
                    run_state.status = "failed"
                    run_state.message = f"Max loops exceeded at node {run_state.current_node}"
                    await self.storage.save_run(run_state)
                    await ws_manager.broadcast_status(run_id, "failed", run_state.message)
                    return

                # Transition
                if next_node_id:
                    run_state.current_node = next_node_id
                    # Save intermediate state? Optional, but good for "GET state".
                    await self.storage.save_run(run_state)
                else:
                    # No outgoing edges -> End of workflow
                    run_state.current_node = None
                    run_state.status = "completed"
                    await self.storage.save_run(run_state)
                    await ws_manager.broadcast_status(run_id, "completed", "Workflow completed successfully")
                    break
                    
        except Exception as e:
            logger.exception("Workflow execution failed")
            run_state.status = "failed"
            run_state.message = str(e)
            await self.storage.save_run(run_state)
            await ws_manager.broadcast_status(run_id, "failed", str(e))
