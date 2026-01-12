from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app import models, database
from app.auth import get_current_user
from pydantic import BaseModel

router = APIRouter()

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ========== Schemas ==========

class NotificationOut(BaseModel):
    id: int
    notification_type: str
    title: str
    content: str
    related_link: Optional[str]
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# ========== Endpoints ==========

@router.get("/notifications", response_model=List[NotificationOut])
def get_notifications(
    skip: int = 0, 
    limit: int = 50, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    notifications = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id
    ).order_by(models.Notification.created_at.desc()).offset(skip).limit(limit).all()
    
    return notifications

@router.get("/notifications/unread-count")
def get_unread_notification_count(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    count = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.is_read == False
    ).count()
    
    return {"count": count}

@router.put("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    notification = db.query(models.Notification).filter(
        models.Notification.id == notification_id,
        models.Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    db.commit()
    
    return {"status": "marked_read"}

@router.put("/notifications/read-all")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.is_read == False
    ).update({models.Notification.is_read: True})
    
    db.commit()
    
    return {"status": "all_marked_read"}
