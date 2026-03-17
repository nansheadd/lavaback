from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import models, schemas, database
from app.auth import get_current_user, get_password_hash, verify_password
from app.database import get_db

router = APIRouter()

@router.get("/me", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@router.patch("/me", response_model=schemas.User)
def update_profile(
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Check if username/email is taken by another user
    if user_update.username:
        existing_user = db.query(models.User).filter(
            models.User.username == user_update.username,
            models.User.id != current_user.id
        ).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")
        current_user.username = user_update.username

    if user_update.email:
        existing_email = db.query(models.User).filter(
            models.User.email == user_update.email,
            models.User.id != current_user.id
        ).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already exists")
        current_user.email = user_update.email

    db.commit()
    db.refresh(current_user)
    return current_user

@router.post("/me/password", status_code=status.HTTP_200_OK)
def change_password(
    password_data: schemas.PasswordChange,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if not verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect old password")

    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(status_code=400, detail="New passwords do not match")

    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    
    return {"message": "Password updated successfully"}

class UserPublic(schemas.BaseModel):
    id: int
    username: str
    role_name: str | None = None
    
    class Config:
        from_attributes = True

@router.get("/search", response_model=list[UserPublic])
def search_users(
    q: str = "",
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.User).filter(models.User.is_active == True)
    if q:
        query = query.filter(models.User.username.ilike(f"%{q}%"))
    
    users = query.limit(limit).all()
    
    # Map role_name manually if needed or via schema if eager loaded
    result = []
    for u in users:
        result.append({
            "id": u.id,
            "username": u.username,
            "role_name": u.role.name if u.role else None
        })
        
    return result
