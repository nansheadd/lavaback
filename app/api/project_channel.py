
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app import database, models
from app.auth import get_current_user
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

router = APIRouter()

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Schemas ---

class ProjectStepCreate(BaseModel):
    title: str
    order: int = 0

class ProjectStepUpdate(BaseModel):
    title: Optional[str] = None
    is_validated: Optional[bool] = None
    order: Optional[int] = None

class ProjectStepOut(BaseModel):
    id: int
    title: str
    is_validated: bool
    order: int
    project_id: int
    created_at: datetime
    # We might want linked reviews count or IDs

class LinkReviewSchema(BaseModel):
    step_id: int

# --- Endpoints ---

@router.post("/projects/{project_id}/channel")
def get_or_create_project_channel(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Check project
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check existing channel
    channel = db.query(models.ChatChannel).filter(models.ChatChannel.project_id == project_id).first()
    if channel:
        # Check membership and add if not present
        member = db.query(models.ChannelMember).filter(
            models.ChannelMember.channel_id == channel.id,
            models.ChannelMember.user_id == current_user.id
        ).first()

        if not member:
            new_member = models.ChannelMember(
                channel_id=channel.id,
                user_id=current_user.id,
                role=models.MemberRole.MEMBER.value
            )
            db.add(new_member)
            db.commit()

        return {"id": channel.id, "slug": channel.slug, "name": channel.name}

    # Create Channel
    base_slug = f"project-{project.title.lower().replace(' ', '-')}-{project_id}"
    # Ensure unique slug (simple check)
    slug = base_slug
    
    new_channel = models.ChatChannel(
        name=f"Salons: {project.title}",
        slug=slug,
        description=f"Canal général pour le projet {project.title}",
        channel_type=models.ChannelType.PROJECT.value,
        project_id=project_id,
        created_by=current_user.id
    )
    db.add(new_channel)
    db.commit()
    db.refresh(new_channel)
    
    # Add creator as member
    member = models.ChannelMember(
        channel_id=new_channel.id,
        user_id=current_user.id,
        role=models.MemberRole.OWNER.value
    )
    db.add(member)
    db.commit()

    return {"id": new_channel.id, "slug": new_channel.slug, "name": new_channel.name}

@router.get("/projects/{project_id}/steps", response_model=List[ProjectStepOut])
def get_project_steps(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    steps = db.query(models.ProjectStep).filter(
        models.ProjectStep.project_id == project_id
    ).order_by(models.ProjectStep.order.asc()).all()
    return list(steps) # Pydantic conversion

@router.post("/projects/{project_id}/steps", response_model=ProjectStepOut)
def create_project_step(
    project_id: int,
    step_in: ProjectStepCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    step = models.ProjectStep(
        project_id=project_id,
        title=step_in.title,
        order=step_in.order
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step

@router.put("/steps/{step_id}", response_model=ProjectStepOut)
def update_project_step(
    step_id: int,
    updates: ProjectStepUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    step = db.query(models.ProjectStep).filter(models.ProjectStep.id == step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
        
    if updates.title is not None:
        step.title = updates.title
    if updates.is_validated is not None:
        step.is_validated = updates.is_validated
    if updates.order is not None:
        step.order = updates.order
        
    db.commit()
    db.refresh(step)
    return step

@router.delete("/steps/{step_id}")
def delete_project_step(
    step_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    step = db.query(models.ProjectStep).filter(models.ProjectStep.id == step_id).first()
    if step:
        db.delete(step)
        db.commit()
    return {"status": "deleted"}

@router.post("/reviews/{thread_id}/link")
def link_thread_to_step(
    thread_id: int,
    link_data: LinkReviewSchema,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    thread = db.query(models.ReviewThread).filter(models.ReviewThread.id == thread_id).first()
    if not thread:
         raise HTTPException(status_code=404, detail="Thread not found")
         
    step = db.query(models.ProjectStep).filter(models.ProjectStep.id == link_data.step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
        
    # Validation: Ensure they belong to same project?
    if thread.project_id != step.project_id:
        raise HTTPException(status_code=400, detail="Project mismatch")
        
    thread.step_id = step.id
    db.commit()
    return {"status": "linked", "thread_id": thread.id, "step_id": step.id}
