from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models.base_models import ActivityLog

from pydantic import BaseModel
from datetime import datetime

router = APIRouter(
    prefix="/activity",
    tags=["activity"],
    responses={404: {"description": "Not found"}},
)

class ActivityLogOut(BaseModel):
    id: int
    user_id: Optional[int]
    project_id: Optional[int]
    page_id: Optional[int]
    action: str
    details: Optional[str]
    resource_type: str
    timestamp: datetime
    
    # Optionally include user name if needed (simple for now)

    class Config:
        orm_mode = True

@router.get("/", response_model=List[ActivityLogOut])
def get_activity_logs(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """
    Get global activity logs, ordered by timestamp desc.
    """
    logs = db.query(ActivityLog).order_by(ActivityLog.timestamp.desc()).offset(skip).limit(limit).all()
    return logs

@router.get("/page/{page_id}", response_model=List[ActivityLogOut])
def get_page_activity(page_id: int, db: Session = Depends(get_db)):
    """
    Get activity for a specific page.
    """
    logs = db.query(ActivityLog).filter(ActivityLog.page_id == page_id).order_by(ActivityLog.timestamp.desc()).all()
    return logs
