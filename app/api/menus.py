from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .. import schemas, models
from ..database import get_db
from ..auth import get_current_user

router = APIRouter()

# --- MENUS ---

@router.get("/apps/{project_id}/menus", response_model=List[schemas.Menu])
def get_menus(project_id: int, db: Session = Depends(get_db)):
    return db.query(models.Menu).filter(models.Menu.project_id == project_id).all()

@router.get("/apps/{project_id}/menus/{menu_name}", response_model=schemas.Menu)
def get_menu_by_name(project_id: int, menu_name: str, db: Session = Depends(get_db)):
    menu = db.query(models.Menu).filter(
        models.Menu.project_id == project_id,
        models.Menu.name == menu_name
    ).first()
    if not menu:
        raise HTTPException(status_code=404, detail="Menu not found")
    return menu

@router.post("/apps/{project_id}/menus", response_model=schemas.Menu)
def create_menu(
    project_id: int, 
    menu: schemas.MenuCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Enforce basic permissions if needed, here just checking if user is authenticated
    db_menu = models.Menu(**menu.model_dump(), project_id=project_id)
    db.add(db_menu)
    db.commit()
    db.refresh(db_menu)
    return db_menu

@router.put("/menus/{menu_id}", response_model=schemas.Menu)
def update_menu(
    menu_id: int, 
    menu_update: schemas.MenuUpdate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_menu = db.query(models.Menu).filter(models.Menu.id == menu_id).first()
    if not db_menu:
        raise HTTPException(status_code=404, detail="Menu not found")
    
    update_data = menu_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_menu, key, value)
    
    db.commit()
    db.refresh(db_menu)
    return db_menu

@router.delete("/menus/{menu_id}")
def delete_menu(
    menu_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_menu = db.query(models.Menu).filter(models.Menu.id == menu_id).first()
    if not db_menu:
        raise HTTPException(status_code=404, detail="Menu not found")
    db.delete(db_menu)
    db.commit()
    return {"message": "Menu deleted successfully"}

# --- MENU ITEMS ---

@router.post("/menus/{menu_id}/items", response_model=schemas.MenuItem)
def create_menu_item(
    menu_id: int, 
    item: schemas.MenuItemCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_menu = db.query(models.Menu).filter(models.Menu.id == menu_id).first()
    if not db_menu:
        raise HTTPException(status_code=404, detail="Menu not found")
        
    db_item = models.MenuItem(**item.model_dump(), menu_id=menu_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.put("/menu-items/{item_id}", response_model=schemas.MenuItem)
def update_menu_item(
    item_id: int, 
    item_update: schemas.MenuItemUpdate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_item = db.query(models.MenuItem).filter(models.MenuItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="MenuItem not found")
    
    update_data = item_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_item, key, value)
    
    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/menu-items/{item_id}")
def delete_menu_item(
    item_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_item = db.query(models.MenuItem).filter(models.MenuItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="MenuItem not found")
    db.delete(db_item)
    db.commit()
    return {"message": "MenuItem deleted successfully"}
