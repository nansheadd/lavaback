from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from .. import schemas, models
from ..database import get_db
from ..auth import get_current_user

router = APIRouter()

# --- Public Endpoints ---

@router.get("/public", response_model=List[schemas.Article])
def get_public_articles(
    skip: int = 0, 
    limit: int = 10, 
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Article).filter(models.Article.status == models.ArticleStatus.PUBLISHED)
    if category:
        query = query.filter(models.Article.category == category)
    return query.order_by(models.Article.published_at.desc()).offset(skip).limit(limit).all()

@router.get("/slug/{slug}", response_model=schemas.Article)
def get_article_by_slug(slug: str, db: Session = Depends(get_db)):
    # Allow fetching by slug even if not published? Maybe for preview?
    # For now, public endpoint implies published only, or any if generic reader?
    # Let's restrict to PUBLISHED if user relies on this for public view. 
    # But for Admin/Preview we might need another way.
    # Let's just return it and let frontend handle "Not Published" warning if needed.
    article = db.query(models.Article).filter(models.Article.slug == slug).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article

# --- Protected Endpoints ---

@router.post("", response_model=schemas.Article)
def create_article(
    article: schemas.ArticleCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    # Check slug uniqueness
    existing = db.query(models.Article).filter(models.Article.slug == article.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Slug already registered")
        
    db_article = models.Article(
        **article.dict(exclude={'status'}), # Force initial status logic?
        status=models.ArticleStatus.DRAFT, # Always start as Draft
        author_id=current_user.id
    )
    db.add(db_article)
    db.commit()
    db.refresh(db_article)
    return db_article

@router.get("", response_model=List[schemas.Article])
def get_articles(
    skip: int = 0, 
    limit: int = 100, 
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.Article)
    if status:
        query = query.filter(models.Article.status == status)
    # Newest first
    return query.order_by(models.Article.created_at.desc()).offset(skip).limit(limit).all()

@router.get("/{article_id}", response_model=schemas.Article)
def get_article(
    article_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    article = db.query(models.Article).filter(models.Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article

@router.put("/{article_id}", response_model=schemas.Article)
def update_article(
    article_id: int, 
    article_update: schemas.ArticleUpdate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_article = db.query(models.Article).filter(models.Article.id == article_id).first()
    if not db_article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Check permission (Owner or Editor/Admin)
    # Assuming any authenticated user can edit for now simplicty, or enforce:
    if db_article.author_id != current_user.id and current_user.role.name not in ["admin", "editor"]:
         raise HTTPException(status_code=403, detail="Not authorized to edit this article")

    # Update fields
    update_data = article_update.dict(exclude_unset=True)
    
    # Handle Status Change logic if needed, e.g. if setting to PUBLISHED set date
    if 'status' in update_data and update_data['status'] == models.ArticleStatus.PUBLISHED:
        if not db_article.published_at:
            db_article.published_at = datetime.utcnow()
    
    for key, value in update_data.items():
        setattr(db_article, key, value)
    
    db.commit()
    db.refresh(db_article)
    return db_article

@router.post("/{article_id}/status", response_model=schemas.Article)
def update_article_status(
    article_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    article = db.query(models.Article).filter(models.Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
        
    # Logic: Only Editor/Admin can APPROVE or PUBLISH
    if status in [models.ArticleStatus.APPROVED, models.ArticleStatus.PUBLISHED]:
        if current_user.role.name not in ["admin", "editor"]:
            raise HTTPException(status_code=403, detail="Only Editors can approve or publish")
            
    article.status = status
    if status == models.ArticleStatus.PUBLISHED and not article.published_at:
        article.published_at = datetime.utcnow()
        
    db.commit()
    db.refresh(article)
    return article

@router.post("/{article_id}/reviews", response_model=schemas.ArticleReview)
def add_review(
    article_id: int,
    review: schemas.ArticleReviewBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    article = db.query(models.Article).filter(models.Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
        
    new_review = models.ArticleReview(
        article_id=article_id,
        reviewer_id=current_user.id,
        status=review.status,
        comments=review.comments
    )
    
    # Auto update article status based on review?
    if review.status == "System_Approved": # Example
        article.status = models.ArticleStatus.APPROVED

    db.add(new_review)
    db.commit()
    db.refresh(new_review)
    return new_review
