from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.auth import get_current_user

router = APIRouter(
    prefix="/roles",
    tags=["roles"]
)

# Admin/Engineer check helper
def check_admin_access(current_user: models.User):
    if current_user.role.name not in ["admin", "engineer"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not authorized"
        )

@router.get("/", response_model=list[schemas.Role])
def read_roles(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_admin_access(current_user)
    return db.query(models.Role).all()

@router.post("/", response_model=schemas.Role)
def create_role(
    role: schemas.RoleCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    check_admin_access(current_user)
    
    existing_role = db.query(models.Role).filter(models.Role.name == role.name).first()
    if existing_role:
        raise HTTPException(status_code=400, detail="Role already exists")
    
    new_role = models.Role(name=role.name, permissions="")
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    return new_role

@router.put("/{role_id}", response_model=schemas.Role)
def update_role_permissions(
    role_id: int,
    role_update: schemas.RoleUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    check_admin_access(current_user)
    
    role = db.query(models.Role).filter(models.Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Prevent modifying system roles permissions if needed, 
    # but requirement implies flexibility. Admin/Engineer usually have * anyway.
    
    role.permissions = role_update.permissions
    db.commit()
    db.refresh(role)
    return role

@router.delete("/{role_id}")
def delete_role(
    role_id: int, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    check_admin_access(current_user)
    
    role = db.query(models.Role).filter(models.Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    if role.name in ["admin", "engineer", "user", "editor", "author"]:
        raise HTTPException(status_code=400, detail="Cannot delete system roles")
        
    db.delete(role)
    db.commit()
    return {"message": "Role deleted successfully"}
