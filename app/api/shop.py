from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app import models, database
from app.auth import get_current_user

router = APIRouter()

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ========== Pydantic Schemas ==========

# Categories
class CategoryCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    icon: Optional[str] = None

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    is_active: Optional[bool] = None

class CategoryOut(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str]
    icon: Optional[str]
    is_active: bool
    
    class Config:
        from_attributes = True

# Products
class ProductCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    price: int  # cents
    currency: str = "EUR"
    product_type: str = "physical"
    category_id: Optional[int] = None
    image_url: Optional[str] = None
    stock: Optional[int] = None
    is_featured: bool = False

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    price: Optional[int] = None
    currency: Optional[str] = None
    product_type: Optional[str] = None
    category_id: Optional[int] = None
    image_url: Optional[str] = None
    stock: Optional[int] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None

class ProductOut(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str]
    price: int
    currency: str
    product_type: str
    category_id: Optional[int]
    category: Optional[CategoryOut] = None
    image_url: Optional[str]
    stock: Optional[int]
    is_active: bool
    is_featured: bool
    stripe_product_id: Optional[str]
    stripe_price_id: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# Subscription Plans
class PlanCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: int  # cents
    currency: str = "EUR"
    interval: str = "month"
    features: Optional[str] = None  # JSON string
    is_popular: bool = False
    sort_order: int = 0

class PlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[int] = None
    currency: Optional[str] = None
    interval: Optional[str] = None
    features: Optional[str] = None
    is_active: Optional[bool] = None
    is_popular: Optional[bool] = None
    sort_order: Optional[int] = None

class PlanOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price: int
    currency: str
    interval: str
    features: Optional[str]
    is_active: bool
    is_popular: bool
    sort_order: int
    stripe_product_id: Optional[str]
    stripe_price_id: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# ========== Admin Endpoints ==========

def check_admin(user: models.User):
    if user.role.name not in ["admin", "engineer"]:
        raise HTTPException(status_code=403, detail="Not authorized")

# --- Categories ---
@router.get("/admin/categories", response_model=List[CategoryOut])
def list_categories(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    check_admin(current_user)
    return db.query(models.ProductCategory).all()

@router.post("/admin/categories", response_model=CategoryOut)
def create_category(
    cat: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    check_admin(current_user)
    db_cat = models.ProductCategory(**cat.model_dump())
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    return db_cat

@router.put("/admin/categories/{cat_id}", response_model=CategoryOut)
def update_category(
    cat_id: int,
    cat: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    check_admin(current_user)
    db_cat = db.query(models.ProductCategory).filter(models.ProductCategory.id == cat_id).first()
    if not db_cat:
        raise HTTPException(status_code=404, detail="Category not found")
    
    for key, value in cat.model_dump(exclude_unset=True).items():
        setattr(db_cat, key, value)
    
    db.commit()
    db.refresh(db_cat)
    return db_cat

@router.delete("/admin/categories/{cat_id}")
def delete_category(
    cat_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    check_admin(current_user)
    db_cat = db.query(models.ProductCategory).filter(models.ProductCategory.id == cat_id).first()
    if not db_cat:
        raise HTTPException(status_code=404, detail="Category not found")
    
    db_cat.is_active = False
    db.commit()
    return {"message": "Category deactivated"}

# --- Products ---
@router.get("/admin/products", response_model=List[ProductOut])
def list_products_admin(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    check_admin(current_user)
    return db.query(models.Product).all()

@router.post("/admin/products", response_model=ProductOut)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    check_admin(current_user)
    db_product = models.Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@router.put("/admin/products/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    product: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    check_admin(current_user)
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    for key, value in product.model_dump(exclude_unset=True).items():
        setattr(db_product, key, value)
    
    db.commit()
    db.refresh(db_product)
    return db_product

@router.delete("/admin/products/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    check_admin(current_user)
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db_product.is_active = False
    db.commit()
    return {"message": "Product deactivated"}

# --- Subscription Plans ---
@router.get("/admin/plans", response_model=List[PlanOut])
def list_plans_admin(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    check_admin(current_user)
    return db.query(models.SubscriptionPlan).order_by(models.SubscriptionPlan.sort_order).all()

@router.post("/admin/plans", response_model=PlanOut)
def create_plan(
    plan: PlanCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    check_admin(current_user)
    db_plan = models.SubscriptionPlan(**plan.model_dump())
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    return db_plan

@router.put("/admin/plans/{plan_id}", response_model=PlanOut)
def update_plan(
    plan_id: int,
    plan: PlanUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    check_admin(current_user)
    db_plan = db.query(models.SubscriptionPlan).filter(models.SubscriptionPlan.id == plan_id).first()
    if not db_plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    for key, value in plan.model_dump(exclude_unset=True).items():
        setattr(db_plan, key, value)
    
    db.commit()
    db.refresh(db_plan)
    return db_plan

@router.delete("/admin/plans/{plan_id}")
def delete_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    check_admin(current_user)
    db_plan = db.query(models.SubscriptionPlan).filter(models.SubscriptionPlan.id == plan_id).first()
    if not db_plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    db_plan.is_active = False
    db.commit()
    return {"message": "Plan deactivated"}

# ========== Public Shop Endpoints ==========

@router.get("/shop/categories", response_model=List[CategoryOut])
def list_public_categories(db: Session = Depends(get_db)):
    return db.query(models.ProductCategory).filter(models.ProductCategory.is_active == True).all()

@router.get("/shop/products", response_model=List[ProductOut])
def list_public_products(
    category: Optional[str] = None,
    featured: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Product).filter(models.Product.is_active == True)
    
    if category:
        query = query.join(models.ProductCategory).filter(models.ProductCategory.slug == category)
    
    if featured:
        query = query.filter(models.Product.is_featured == True)
    
    return query.all()

@router.get("/shop/products/{slug}", response_model=ProductOut)
def get_product_by_slug(slug: str, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(
        models.Product.slug == slug,
        models.Product.is_active == True
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return product

@router.get("/shop/plans", response_model=List[PlanOut])
def list_public_plans(db: Session = Depends(get_db)):
    return db.query(models.SubscriptionPlan).filter(
        models.SubscriptionPlan.is_active == True
    ).order_by(models.SubscriptionPlan.sort_order).all()
