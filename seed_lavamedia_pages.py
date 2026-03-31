import sys
import os
import json
from datetime import datetime

# Add current directory to path so we can import app modules
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models.base_models import Project, Menu, MenuItem
from app.models.builder_page import BuilderPage

def seed_lavamedia_pages():
    print("Seeding Lavamedia Pages & Menus...")
    db = SessionLocal()

    try:
        # 1. Find or create the Lavamedia Project
        project = db.query(Project).filter(Project.title.ilike("%Lava%")).first()
        if not project:
            print("Creating Lava Media project...")
            project = Project(
                title="Lava Media V2",
                description="Revue critique d'analyse sociale et politique.",
                status="VALIDATED"
            )
            db.add(project)
            db.commit()
            db.refresh(project)
        
        print(f"Using Project: {project.title} (ID: {project.id})")

        # 2. Create Header Menu
        header_menu = db.query(Menu).filter(Menu.project_id == project.id, Menu.name == "header").first()
        if not header_menu:
            header_menu = Menu(project_id=project.id, name="header", title="Navigation Principale")
            db.add(header_menu)
            db.commit()
            db.refresh(header_menu)

        # Clear and re-add header items
        db.query(MenuItem).filter(MenuItem.menu_id == header_menu.id).delete()
        header_items = [
            {"label": "Online", "url": "home", "order": 1},
            {"label": "Magazine", "url": "revue", "order": 2},
            {"label": "Shop", "url": "shop", "order": 3},
            {"label": "Abonnements", "url": "abonnements", "order": 4},
        ]
        for i, item in enumerate(header_items):
            mi = MenuItem(menu_id=header_menu.id, label=item["label"], url=item["url"], order=item["order"])
            db.add(mi)

        # 3. Create Footer Menu with Groups
        footer_menu = db.query(Menu).filter(Menu.project_id == project.id, Menu.name == "footer").first()
        if not footer_menu:
            footer_menu = Menu(project_id=project.id, name="footer", title="Pied de Page")
            db.add(footer_menu)
            db.commit()
            db.refresh(footer_menu)

        db.query(MenuItem).filter(MenuItem.menu_id == footer_menu.id).delete()
        footer_items = [
            # Group: REVUE
            {"label": "Numéro actuel", "url": "revue", "group": "REVUE", "order": 1},
            {"label": "Archives", "url": "archives", "group": "REVUE", "order": 2},
            {"label": "Abonnements", "url": "abonnements", "group": "REVUE", "order": 3},
            # Group: ARTICLES
            {"label": "Analyse", "url": "articles?cat=analyse", "group": "ARTICLES", "order": 4},
            {"label": "Interview", "url": "articles?cat=interview", "group": "ARTICLES", "order": 5},
            {"label": "Opinion", "url": "articles?cat=opinion", "group": "ARTICLES", "order": 6},
            # Group: LAVA
            {"label": "Qui sommes-nous ?", "url": "apropos", "group": "LAVA", "order": 7},
            {"label": "Contact", "url": "contact", "group": "LAVA", "order": 8},
            {"label": "Mentions Légales", "url": "legal", "group": "LAVA", "order": 9},
            # Group: RÉSEAUX
            {"label": "Facebook", "url": "https://facebook.com", "group": "RÉSEAUX", "order": 10},
            {"label": "Instagram", "url": "https://instagram.com", "group": "RÉSEAUX", "order": 11},
        ]
        for item in footer_items:
            mi = MenuItem(
                menu_id=footer_menu.id, 
                label=item["label"], 
                url=item["url"], 
                group_name=item["group"],
                order=item["order"]
            )
            db.add(mi)
        
        db.commit()

        # 4. Create Pages
        pages_to_create = [
            {
                "name": "Articles",
                "slug": "articles",
                "widgets": [
                    {"toolId": "navbar", "x": 0, "y": 0, "w": 24, "h": 3, "data": {"projectId": project.id, "style": "lava-orange"}},
                    {"toolId": "category-nav", "x": 0, "y": 3, "w": 24, "h": 2, "data": {}},
                    {"toolId": "hero", "x": 0, "y": 5, "w": 24, "h": 8, "data": {"title": "Tous nos articles", "subtitle": "Analyses et perspectives sur le monde contemporain."}},
                    {"toolId": "article-grid", "x": 0, "y": 13, "w": 24, "h": 20, "data": {"columns": 3}},
                    {"toolId": "footer", "x": 0, "y": 33, "w": 24, "h": 10, "data": {"projectId": project.id}}
                ]
            },
            {
                "name": "La Revue",
                "slug": "revue",
                "widgets": [
                    {"toolId": "navbar", "x": 0, "y": 0, "w": 24, "h": 3, "data": {"projectId": project.id, "style": "lava-orange"}},
                    {"toolId": "magazine-section", "x": 0, "y": 3, "w": 24, "h": 14, "data": {"title": "Dernier Numéro"}},
                    {"toolId": "article-grid", "x": 0, "y": 17, "w": 24, "h": 14, "data": {"sectionTitle": "Archives de la revue", "columns": 4}},
                    {"toolId": "footer", "x": 0, "y": 31, "w": 24, "h": 10, "data": {"projectId": project.id}}
                ]
            },
            {
                "name": "À Propos",
                "slug": "apropos",
                "widgets": [
                    {"toolId": "navbar", "x": 0, "y": 0, "w": 24, "h": 3, "data": {"projectId": project.id, "style": "lava-orange"}},
                    {"toolId": "hero", "x": 0, "y": 3, "w": 24, "h": 8, "data": {"title": "Qui sommes-nous ?", "imageUrl": "https://images.unsplash.com/photo-1521737604893-d14cc237f11d?w=1400&h=600&fit=crop"}},
                    {"toolId": "text-editor", "x": 4, "y": 11, "w": 16, "h": 20, "data": {"content": "<h2>Lava : un outil d'analyse critique</h2><p>Lava est une revue belge qui propose des analyses de fond sur les enjeux sociaux, politiques et économiques...</p>"}},
                    {"toolId": "footer", "x": 0, "y": 31, "w": 24, "h": 10, "data": {"projectId": project.id}}
                ]
            }
        ]

        for p_data in pages_to_create:
            existing = db.query(BuilderPage).filter(BuilderPage.slug == p_data["slug"]).first()
            if existing:
                print(f"Updating page: {p_data['name']}")
                existing.widgets_json = json.dumps(p_data["widgets"])
            else:
                print(f"Creating page: {p_data['name']}")
                page = BuilderPage(
                    name=p_data["name"],
                    slug=p_data["slug"],
                    project_id=project.id,
                    widgets_json=json.dumps(p_data["widgets"]),
                    is_published=True
                )
                db.add(page)
        
        db.commit()
        print("Done seeding Lavamedia pages and menus.")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_lavamedia_pages()
