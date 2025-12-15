"""
Workflow Executor - Executes workflow graphs by traversing nodes.
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from ..models.workflow import Workflow, WorkflowExecution
from .action_registry import action_registry


class WorkflowExecutor:
    """
    Executes a workflow by traversing its node graph.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.context: Dict[str, Any] = {}
        self.execution_log: List[Dict] = []
    
    async def execute(self, workflow: Workflow, input_data: Dict = None) -> WorkflowExecution:
        """
        Execute a workflow and return the execution record.
        """
        # Create execution record
        execution = WorkflowExecution(
            workflow_id=workflow.id,
            status="running",
            input_data=json.dumps(input_data or {}),
            started_at=datetime.utcnow()
        )
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        
        try:
            # Initialize context
            self.context = {
                "input": input_data or {},
                "variables": {},
                "workflow_id": workflow.id,
                "execution_id": execution.id
            }
            self.execution_log = []
            
            # Parse workflow graph
            nodes = json.loads(workflow.nodes_json or "[]")
            edges = json.loads(workflow.edges_json or "[]")
            
            # Build adjacency list
            adjacency = self._build_adjacency(edges)
            
            # Find trigger node (start point)
            trigger_node = self._find_trigger_node(nodes)
            if not trigger_node:
                raise Exception("No trigger node found in workflow")
            
            # Execute from trigger
            await self._execute_node(trigger_node, nodes, adjacency, execution)
            
            # Mark as completed
            execution.status = "completed"
            execution.output_data = json.dumps(self.context.get("variables", {}))
            execution.completed_at = datetime.utcnow()
            
        except Exception as e:
            execution.status = "failed"
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            self._log_step("error", {"message": str(e)})
        
        # Save execution log
        execution.execution_log = json.dumps(self.execution_log)
        self.db.commit()
        self.db.refresh(execution)
        
        return execution
    
    def _build_adjacency(self, edges: List[Dict]) -> Dict[str, List[Dict]]:
        """Build adjacency list from edges."""
        adjacency = {}
        for edge in edges:
            source = edge.get("source")
            if source not in adjacency:
                adjacency[source] = []
            adjacency[source].append({
                "target": edge.get("target"),
                "sourceHandle": edge.get("sourceHandle"),  # For condition nodes: "true" or "false"
                "targetHandle": edge.get("targetHandle")
            })
        return adjacency
    
    def _find_trigger_node(self, nodes: List[Dict]) -> Optional[Dict]:
        """Find the trigger/start node."""
        for node in nodes:
            if node.get("type") == "trigger":
                return node
        return None
    
    def _get_node_by_id(self, node_id: str, nodes: List[Dict]) -> Optional[Dict]:
        """Get a node by its ID."""
        for node in nodes:
            if node.get("id") == node_id:
                return node
        return None
    
    async def _execute_node(
        self, 
        node: Dict, 
        all_nodes: List[Dict], 
        adjacency: Dict, 
        execution: WorkflowExecution
    ):
        """Execute a single node and continue to connected nodes."""
        
        node_id = node.get("id")
        node_type = node.get("type")
        action_id = node.get("data", {}).get("actionId")
        config = node.get("data", {}).get("config", {})
        
        # Update current node in execution
        execution.current_node_id = node_id
        self.db.commit()
        
        self._log_step("node_start", {"node_id": node_id, "type": node_type, "action": action_id})
        
        result = {}
        
        # Handle different node types
        if node_type == "trigger":
            # Trigger just starts the flow
            result = {"triggered": True}
            
        elif node_type == "action":
            # Execute the action
            action = action_registry.get(action_id)
            if action and action.handler:
                result = await action.handler(self.context, config)
                # Store result in context
                self.context["variables"][f"_{node_id}_result"] = result
            else:
                raise Exception(f"Unknown action: {action_id}")
                
        elif node_type == "condition":
            # Condition node - evaluate and branch
            action = action_registry.get("logic.condition")
            if action and action.handler:
                result = await action.handler(self.context, config)
        
        elif node_type == "output":
            # Output node - end of workflow
            self._log_step("output", {"data": self.context.get("variables", {})})
            return
        
        self._log_step("node_complete", {"node_id": node_id, "result": result})
        
        # Find next nodes to execute
        next_edges = adjacency.get(node_id, [])
        
        for edge in next_edges:
            target_id = edge.get("target")
            target_node = self._get_node_by_id(target_id, all_nodes)
            
            if not target_node:
                continue
            
            # For condition nodes, check which branch to take
            if node_type == "condition":
                source_handle = edge.get("sourceHandle")
                condition_result = result.get("result", False)
                
                if source_handle == "true" and condition_result:
                    await self._execute_node(target_node, all_nodes, adjacency, execution)
                elif source_handle == "false" and not condition_result:
                    await self._execute_node(target_node, all_nodes, adjacency, execution)
            else:
                # Normal flow - execute next node
                await self._execute_node(target_node, all_nodes, adjacency, execution)
    
    def _log_step(self, event: str, data: Dict):
        """Add a step to the execution log."""
        self.execution_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
            "data": data
        })
