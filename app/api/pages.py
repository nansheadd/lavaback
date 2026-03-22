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
    project_id: Optional[int] = None # Added
    # Access Control
    access_level: str = "public"
    allowed_roles: List[str] = []

class PageUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    widgets: Optional[List[PageWidget]] = None
    theme: Optional[ThemeSettings] = None
    is_published: Optional[bool] = None
    project_id: Optional[int] = None # Added
    # Access Control
    access_level: Optional[str] = None
    allowed_roles: Optional[List[str]] = None


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text


# === API Endpoints ===

@router.get("")
def list_pages(project_id: Optional[int] = None, db: Session = Depends(get_db)):
    """List all saved pages, optionally filtered by project_id."""
    query = db.query(BuilderPage)
    if project_id:
        query = query.filter(BuilderPage.project_id == project_id)
    pages = query.order_by(BuilderPage.updated_at.desc()).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "slug": p.slug,
            "description": p.description,
            "project_id": p.project_id,
            "is_published": p.is_published,
            "access_level": p.access_level,
            "allowed_roles": json.loads(p.allowed_roles or "[]"),
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
        project_id=page.project_id,

        description=page.description,
        widgets_json=json.dumps([w.model_dump() for w in page.widgets]),
        theme_json=json.dumps(page.theme.model_dump()) if page.theme else None,
        access_level=page.access_level,
        allowed_roles=json.dumps(page.allowed_roles)
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
        "project_id": page.project_id,
        "description": page.description,
        "widgets": json.loads(page.widgets_json or "[]"),
        "theme": json.loads(page.theme_json) if page.theme_json else None,
        "is_published": page.is_published,
        "access_level": page.access_level,
        "allowed_roles": json.loads(page.allowed_roles or "[]"),
        "created_at": page.created_at.isoformat() if page.created_at else None,
        "updated_at": page.updated_at.isoformat() if page.updated_at else None
    }


@router.get("/slug/{slug}")
def get_page_by_slug(slug: str, db: Session = Depends(get_db)):
    """Get a page by its slug (for public viewing)."""
    page = db.query(BuilderPage).filter(BuilderPage.slug == slug).first()
    
    if not page and slug == "home":
        # Auto-seed the home page with Premium Lava layout
        print("Auto-seeding default home page for Lava")
        default_widgets = [
            {
                "i": "hero-1",
                "toolId": "hero",
                "x": 0, "y": 0, "w": 24, "h": 12,
                "data": {
                    "title": "Lava - Revue d'analyse sociale et politique",
                    "subtitle": "Décrypter avec rigueur et engagement les grands enjeux de notre époque. Un journalisme indépendant, sans publicité.",
                    "buttonText": "Découvrir la revue",
                    "imageUrl": "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?ixlib=rb-4.0.3&auto=format&fit=crop&w=1350&q=80"
                }
            },
            {
                "i": "features-1",
                "toolId": "features",
                "x": 0, "y": 12, "w": 24, "h": 10,
                "data": {
                    "title": "Notre Ligne Éditoriale",
                    "features": [
                        {"title": "Analyse Critique", "desc": "Prendre de la hauteur pour comprendre les dynamiques structurelles de notre société."},
                        {"title": "Indépendance", "desc": "Une information libre de toute pression financière et commerciale, sans publicités."},
                        {"title": "Engagement", "desc": "Contribuer aux débats pour une transition sociale, démocratique et écologique juste."}
                    ]
                }
            },
            {
                "i": "articles-1",
                "toolId": "article-list",
                "x": 0, "y": 22, "w": 24, "h": 14,
                "data": {
                    "title": "Derniers Articles",
                    "limit": 3,
                    "layout": "grid",
                    "detailPageSlug": "/article"
                }
            },
            {
                "i": "newsletter-1",
                "toolId": "newsletter-form",
                "x": 0, "y": 36, "w": 24, "h": 6,
                "data": {
                    "title": "Restez informés, abonnez-vous à notre infolettre",
                    "placeholder": "Votre adresse email...",
                    "buttonText": "S'inscrire"
                }
            }
        ]
        
        page = BuilderPage(
            name="Accueil",
            slug="home",
            description="Page d'accueil par défaut de Lava",
            widgets_json=json.dumps(default_widgets),
            theme_json=json.dumps({
                "primaryColor": "#f04e23", 
                "secondaryColor": "#1e2257",
                "backgroundColor": "#ffffff", 
                "fontFamily": "Inter, sans-serif", 
                "borderRadius": "0"
            }),
            is_published=True,
            access_level="public"
        )
        db.add(page)
        db.commit()
        db.refresh(page)

    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    return {
        "id": page.id,
        "name": page.name,
        "slug": page.slug,
        "project_id": page.project_id,
        "widgets": json.loads(page.widgets_json or "[]"),
        "theme": json.loads(page.theme_json) if page.theme_json else None,
        "is_published": page.is_published,
        "access_level": page.access_level,
        "allowed_roles": json.loads(page.allowed_roles or "[]")
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
    
    if update.slug is not None:
        new_slug = slugify(update.slug)
        if page.slug != new_slug:
            # Check for uniqueness
            existing = db.query(BuilderPage).filter(BuilderPage.slug == new_slug).first()
            if existing and existing.id != page.id:
                raise HTTPException(status_code=400, detail="Slug already in use")
            
            changes.append(f"slug changed from '{page.slug}' to '{new_slug}'")
            page.slug = new_slug

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
    
    if update.access_level is not None:
        if page.access_level != update.access_level:
            changes.append(f"access level changed to {update.access_level}")
        page.access_level = update.access_level

    if update.allowed_roles is not None:
        new_roles_json = json.dumps(update.allowed_roles)
        if page.allowed_roles != new_roles_json:
            changes.append("allowed roles updated")
        page.allowed_roles = new_roles_json
    
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
