"""
Workflow API - CRUD operations and execution endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import json

from ..database import get_db
from ..models.workflow import Workflow, WorkflowExecution
from ..services.action_registry import action_registry
from ..services.workflow_executor import WorkflowExecutor


router = APIRouter(prefix="/workflows", tags=["workflows"])


# === Pydantic Schemas ===

class WorkflowNodeData(BaseModel):
    actionId: Optional[str] = None
    config: Optional[dict] = {}
    label: Optional[str] = None

class WorkflowNode(BaseModel):
    id: str
    type: str  # trigger, action, condition, output
    position: dict  # {x, y}
    data: WorkflowNodeData

class WorkflowEdge(BaseModel):
    id: str
    source: str
    target: str
    sourceHandle: Optional[str] = None
    targetHandle: Optional[str] = None

class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_type: Optional[str] = "manual"
    trigger_config: Optional[dict] = None
    nodes: List[WorkflowNode] = []
    edges: List[WorkflowEdge] = []

class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_config: Optional[dict] = None
    nodes: Optional[List[WorkflowNode]] = None
    edges: Optional[List[WorkflowEdge]] = None
    is_active: Optional[bool] = None

class WorkflowResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    trigger_type: str
    trigger_config: Optional[dict]
    nodes: List[dict]
    edges: List[dict]
    is_active: bool
    
    class Config:
        from_attributes = True

class WorkflowExecuteRequest(BaseModel):
    input_data: Optional[dict] = {}

class ExecutionResponse(BaseModel):
    id: int
    workflow_id: int
    status: str
    input_data: Optional[dict]
    output_data: Optional[dict]
    execution_log: List[dict]
    error_message: Optional[str]
    started_at: str
    completed_at: Optional[str]


# === API Endpoints ===

@router.get("/actions")
def list_actions():
    """List all available actions grouped by category."""
    return action_registry.list_by_category()


@router.get("/actions/all")
def list_all_actions():
    """List all available actions with full details."""
    return action_registry.list_all()


@router.get("")
def list_workflows(db: Session = Depends(get_db)):
    """List all workflows."""
    workflows = db.query(Workflow).all()
    return [
        {
            "id": w.id,
            "name": w.name,
            "description": w.description,
            "trigger_type": w.trigger_type,
            "is_active": w.is_active,
            "created_at": w.created_at.isoformat() if w.created_at else None
        }
        for w in workflows
    ]


@router.post("")
def create_workflow(workflow: WorkflowCreate, db: Session = Depends(get_db)):
    """Create a new workflow."""
    db_workflow = Workflow(
        name=workflow.name,
        description=workflow.description,
        trigger_type=workflow.trigger_type,
        trigger_config=json.dumps(workflow.trigger_config) if workflow.trigger_config else None,
        nodes_json=json.dumps([n.model_dump() for n in workflow.nodes]),
        edges_json=json.dumps([e.model_dump() for e in workflow.edges])
    )
    db.add(db_workflow)
    db.commit()
    db.refresh(db_workflow)
    
    return {
        "id": db_workflow.id,
        "name": db_workflow.name,
        "message": "Workflow created successfully"
    }


@router.get("/{workflow_id}")
def get_workflow(workflow_id: int, db: Session = Depends(get_db)):
    """Get a specific workflow with full details."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return {
        "id": workflow.id,
        "name": workflow.name,
        "description": workflow.description,
        "trigger_type": workflow.trigger_type,
        "trigger_config": json.loads(workflow.trigger_config) if workflow.trigger_config else None,
        "nodes": json.loads(workflow.nodes_json or "[]"),
        "edges": json.loads(workflow.edges_json or "[]"),
        "is_active": workflow.is_active,
        "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
        "updated_at": workflow.updated_at.isoformat() if workflow.updated_at else None
    }


@router.put("/{workflow_id}")
def update_workflow(workflow_id: int, update: WorkflowUpdate, db: Session = Depends(get_db)):
    """Update a workflow."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    if update.name is not None:
        workflow.name = update.name
    if update.description is not None:
        workflow.description = update.description
    if update.trigger_type is not None:
        workflow.trigger_type = update.trigger_type
    if update.trigger_config is not None:
        workflow.trigger_config = json.dumps(update.trigger_config)
    if update.nodes is not None:
        workflow.nodes_json = json.dumps([n.model_dump() for n in update.nodes])
    if update.edges is not None:
        workflow.edges_json = json.dumps([e.model_dump() for e in update.edges])
    if update.is_active is not None:
        workflow.is_active = update.is_active
    
    db.commit()
    db.refresh(workflow)
    
    return {"message": "Workflow updated successfully"}


@router.delete("/{workflow_id}")
def delete_workflow(workflow_id: int, db: Session = Depends(get_db)):
    """Delete a workflow."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    db.delete(workflow)
    db.commit()
    
    return {"message": "Workflow deleted successfully"}


@router.post("/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: int, 
    request: WorkflowExecuteRequest,
    db: Session = Depends(get_db)
):
    """Execute a workflow."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    if not workflow.is_active:
        raise HTTPException(status_code=400, detail="Workflow is not active")
    
    executor = WorkflowExecutor(db)
    execution = await executor.execute(workflow, request.input_data)
    
    return {
        "execution_id": execution.id,
        "status": execution.status,
        "output": json.loads(execution.output_data) if execution.output_data else None,
        "error": execution.error_message,
        "log": json.loads(execution.execution_log or "[]")
    }


@router.get("/{workflow_id}/executions")
def list_executions(workflow_id: int, limit: int = 20, db: Session = Depends(get_db)):
    """List recent executions for a workflow."""
    executions = db.query(WorkflowExecution)\
        .filter(WorkflowExecution.workflow_id == workflow_id)\
        .order_by(WorkflowExecution.started_at.desc())\
        .limit(limit)\
        .all()
    
    return [
        {
            "id": e.id,
            "status": e.status,
            "started_at": e.started_at.isoformat() if e.started_at else None,
            "completed_at": e.completed_at.isoformat() if e.completed_at else None,
            "error": e.error_message
        }
        for e in executions
    ]


@router.get("/executions/{execution_id}")
def get_execution(execution_id: int, db: Session = Depends(get_db)):
    """Get details of a specific execution."""
    execution = db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    return {
        "id": execution.id,
        "workflow_id": execution.workflow_id,
        "status": execution.status,
        "input_data": json.loads(execution.input_data) if execution.input_data else None,
        "output_data": json.loads(execution.output_data) if execution.output_data else None,
        "execution_log": json.loads(execution.execution_log or "[]"),
        "current_node_id": execution.current_node_id,
        "error_message": execution.error_message,
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None
    }
