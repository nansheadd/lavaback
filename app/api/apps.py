from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import models, schemas, database
from app.auth import get_password_hash, verify_password, create_access_token
from datetime import timedelta
import json

router = APIRouter()

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Public/App Endpoints ---

@router.get("/apps/{project_id}/config")
def get_app_config(project_id: int, db: Session = Depends(get_db)):
    """
    Get public configuration for the app (theme, enabled tools).
    """
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="App not found")
    
    # Parse settings
    try:
        settings = json.loads(project.settings or "{}")
    except:
        settings = {}
        
    return {
        "id": project.id,
        "title": project.title,
        "settings": settings,
        "version": project.version
    }

@router.post("/apps/{project_id}/register", response_model=schemas.AppUser)
def register_app_user(project_id: int, user: schemas.AppUserCreate, db: Session = Depends(get_db)):
    """
    Register a new end-user for a specific app.
    """
    # Verify project exists
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="App not found")

    # Check duplicates strictly within this project
    existing_user = db.query(models.AppUser).filter(
        models.AppUser.project_id == project_id,
        models.AppUser.email == user.email
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered for this app")

    hashed_pw = get_password_hash(user.password) if user.password else None
    
    new_user = models.AppUser(
        project_id=project_id,
        email=user.email,
        username=user.username,
        password_hash=hashed_pw,
        is_guest=False
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/apps/{project_id}/reviews", response_model=schemas.ReviewThread)
def create_app_review_thread(
    project_id: int, 
    review: schemas.ReviewThreadCreate, 
    app_user_id: int | None = None, # Should be auth-protected in prod
    db: Session = Depends(get_db)
):
    """
    Create a review thread as an AppUser.
    """
    # Logic similar to main.py but possibly with app_user context
    # For now, we allow passing app_user_id directly for simulation/MVP
    # In real world: extract from JWT
    
    db_review = models.ReviewThread(**review.model_dump(), project_id=project_id)
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review

@router.post("/apps/reviews/{thread_id}/comments", response_model=schemas.ReviewComment)
def create_app_review_comment(
    thread_id: int,
    comment: schemas.ReviewCommentCreate,
    app_user_id: int, # Required for AppUser comments
    db: Session = Depends(get_db)
):
    thread = db.query(models.ReviewThread).filter(models.ReviewThread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
        
    app_user = db.query(models.AppUser).filter(models.AppUser.id == app_user_id).first()
    if not app_user:
        raise HTTPException(status_code=404, detail="App User not found")

    # Verify user belongs to the same project as the thread
    if app_user.project_id != thread.project_id:
        raise HTTPException(status_code=403, detail="User does not belong to this app")

    db_comment = models.ReviewComment(
        thread_id=thread_id,
        content=comment.content,
        app_user_id=app_user.id,
        author_name=app_user.username or "Anonymous"
    )
    
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment
