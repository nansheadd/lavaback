from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class Workflow(Base):
    """
    Represents a workflow definition with nodes and edges stored as JSON.
    """
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    
    # Trigger configuration
    trigger_type = Column(String, default="manual")  # manual, schedule, webhook, event
    trigger_config = Column(Text, nullable=True)  # JSON config for trigger
    
    # Graph structure (stored as JSON)
    nodes_json = Column(Text, default="[]")  # Array of WorkflowNode
    edges_json = Column(Text, default="[]")  # Array of {source, target, sourceHandle, targetHandle}
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    executions = relationship("WorkflowExecution", back_populates="workflow", cascade="all, delete-orphan")
    creator = relationship("User")


class WorkflowExecution(Base):
    """
    Represents a single execution of a workflow.
    """
    __tablename__ = "workflow_executions"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"))
    
    # Execution status
    status = Column(String, default="pending")  # pending, running, completed, failed
    
    # Input/Output data (JSON)
    input_data = Column(Text, nullable=True)
    output_data = Column(Text, nullable=True)
    
    # Execution log (JSON array of step logs)
    execution_log = Column(Text, default="[]")
    
    # Error handling
    error_message = Column(Text, nullable=True)
    current_node_id = Column(String, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    workflow = relationship("Workflow", back_populates="executions")
