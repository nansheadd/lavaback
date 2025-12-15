"""
Builder Pages API - CRUD for App Builder pages.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import json
import re

from ..database import get_db
from ..models.builder_page import BuilderPage
from ..models.base_models import ActivityLog


router = APIRouter(prefix="/pages", tags=["pages"])


# === Pydantic Schemas ===

class PageWidget(BaseModel):
    i: str
    toolId: str
    x: int
    y: int
    w: int
    h: int
    data: dict = {}

class ThemeSettings(BaseModel):
    primaryColor: str = "#3B82F6"
    backgroundColor: str = "#FFFFFF"
    fontFamily: str = "Inter, sans-serif"
    borderRadius: str = "0.5rem"

class PageCreate(BaseModel):
    name: str
    description: Optional[str] = None
    widgets: List[PageWidget] = []
    theme: Optional[ThemeSettings] = None

class PageUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    widgets: Optional[List[PageWidget]] = None
    theme: Optional[ThemeSettings] = None
    is_published: Optional[bool] = None


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text


# === API Endpoints ===

@router.get("")
def list_pages(db: Session = Depends(get_db)):
    """List all saved pages."""
    pages = db.query(BuilderPage).order_by(BuilderPage.updated_at.desc()).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "slug": p.slug,
            "description": p.description,
            "is_published": p.is_published,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None
        }
        for p in pages
    ]


@router.post("")
def create_page(page: PageCreate, db: Session = Depends(get_db)):
    """Create a new page."""
    # Generate unique slug
    base_slug = slugify(page.name)
    slug = base_slug
    counter = 1
    while db.query(BuilderPage).filter(BuilderPage.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    db_page = BuilderPage(
        name=page.name,
        slug=slug,
        description=page.description,
        widgets_json=json.dumps([w.model_dump() for w in page.widgets]),
        theme_json=json.dumps(page.theme.model_dump()) if page.theme else None
    )
    db.add(db_page)
    db.commit()
    db.refresh(db_page)
    
    # Activity Log
    try:
        log = ActivityLog(
            action=f"Created page '{db_page.name}'",
            page_id=db_page.id,
            resource_type="page"
        )
        db.add(log)
        db.commit()
    except Exception as e:
        print(f"Failed to create activity log: {e}")
    
    return {
        "id": db_page.id,
        "name": db_page.name,
        "slug": db_page.slug,
        "message": "Page created successfully"
    }


@router.get("/{page_id}")
def get_page(page_id: int, db: Session = Depends(get_db)):
    """Get a specific page with full content."""
    page = db.query(BuilderPage).filter(BuilderPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    return {
        "id": page.id,
        "name": page.name,
        "slug": page.slug,
        "description": page.description,
        "widgets": json.loads(page.widgets_json or "[]"),
        "theme": json.loads(page.theme_json) if page.theme_json else None,
        "is_published": page.is_published,
        "created_at": page.created_at.isoformat() if page.created_at else None,
        "updated_at": page.updated_at.isoformat() if page.updated_at else None
    }


@router.get("/slug/{slug}")
def get_page_by_slug(slug: str, db: Session = Depends(get_db)):
    """Get a page by its slug (for public viewing)."""
    page = db.query(BuilderPage).filter(BuilderPage.slug == slug).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    return {
        "id": page.id,
        "name": page.name,
        "slug": page.slug,
        "widgets": json.loads(page.widgets_json or "[]"),
        "theme": json.loads(page.theme_json) if page.theme_json else None,
        "is_published": page.is_published
    }


@router.put("/{page_id}")
def update_page(page_id: int, update: PageUpdate, db: Session = Depends(get_db)):
    """Update a page."""
    page = db.query(BuilderPage).filter(BuilderPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    # Track changes for log
    changes = []
    if update.name is not None:
        if page.name != update.name:
            changes.append(f"renamed from '{page.name}' to '{update.name}'")
        page.name = update.name
    if update.description is not None:
        if page.description != update.description:
            changes.append("description updated")
        page.description = update.description
    if update.widgets is not None:
        # Compare JSON strings for simplicity, or parse and compare dicts for more granular check
        new_widgets_json = json.dumps([w.model_dump() for w in update.widgets])
        if page.widgets_json != new_widgets_json:
            changes.append("widgets updated")
        page.widgets_json = new_widgets_json
    if update.theme is not None:
        new_theme_json = json.dumps(update.theme.model_dump())
        if page.theme_json != new_theme_json:
            changes.append("theme updated")
        page.theme_json = new_theme_json
    if update.is_published is not None:
        if page.is_published != update.is_published:
            changes.append(f"published status changed to {update.is_published}")
        page.is_published = update.is_published
    
    db.commit()
    db.refresh(page)

    # Activity Log
    if changes:
        try:
            log = ActivityLog(
                action=f"Updated page '{page.name}'",
                details=", ".join(changes),
                page_id=page.id,
                resource_type="page"
            )
            db.add(log)
            db.commit()
        except Exception as e:
            print(f"Failed to create activity log: {e}")
    
    return {"message": "Page updated successfully", "slug": page.slug}


@router.delete("/{page_id}")
def delete_page(page_id: int, db: Session = Depends(get_db)):
    """Delete a page."""
    page = db.query(BuilderPage).filter(BuilderPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    db.delete(page)
    db.commit()
    
    return {"message": "Page deleted successfully"}
