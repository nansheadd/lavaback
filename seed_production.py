import json
import os
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app import models

def seed_production():
    db = SessionLocal()
    try:
        # 1. Find or create Lava Project
        project = db.query(models.Project).filter(models.Project.title == "Lava Portal").first()
        if not project:
            print("Creating Lava project...")
            project = models.Project(
                title="Lava Portal",
                description="Portail de journalisme Lava",
                status=models.ProjectStatus.VALIDATED.value
            )
            db.add(project)
            db.commit()
            db.refresh(project)
        
        project_id = project.id
        print(f"Using Project ID: {project_id}")

        # 2. Seed Pages
        pages_data = [
            {
                "name": "Accueil",
                "slug": "home",
                "widgets": [
                    {
                        "id": "hero-1",
                        "type": "hero",
                        "toolId": "hero",
                        "x": 0, "y": 0, "w": 12, "h": 14,
                        "data": {
                            "title": "LAVA PORTAL",
                            "subtitle": "La plateforme de journalisme nouvelle génération.",
                            "buttonText": "REJOINDRE LA RÉDACTION",
                            "backgroundImage": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&q=80"
                        }
                    },
                    {
                        "id": "articles-1",
                        "type": "article-list",
                        "toolId": "article-list",
                        "x": 0, "y": 14, "w": 12, "h": 14,
                        "data": {
                            "title": "Derniers Articles",
                            "limit": 3,
                            "layout": "grid",
                            "detailPageSlug": "/article"
                        }
                    }
                ]
            },
            {
                "name": "Login",
                "slug": "app-login",
                "widgets": [
                    {
                        "id": "login-1",
                        "type": "login-form",
                        "toolId": "login-form",
                        "x": 3, "y": 5, "w": 6, "h": 10,
                        "data": {"title": "Connexion Portail"}
                    }
                ]
            },
            {
                "name": "Inscription",
                "slug": "app-register",
                "widgets": [
                    {
                        "id": "register-1",
                        "type": "register-form",
                        "toolId": "register-form",
                        "x": 3, "y": 5, "w": 6, "h": 12,
                        "data": {"title": "Créer un compte"}
                    }
                ]
            }
        ]

        for p_info in pages_data:
            page = db.query(models.BuilderPage).filter(
                models.BuilderPage.project_id == project_id,
                models.BuilderPage.slug == p_info["slug"]
            ).first()
            if not page:
                print(f"Creating page: {p_info['name']}")
                page = models.BuilderPage(
                    name=p_info["name"],
                    slug=p_info["slug"],
                    project_id=project_id,
                    widgets_json=json.dumps(p_info["widgets"]),
                    is_published=True
                )
                db.add(page)
            else:
                # Update widgets if needed
                page.widgets_json = json.dumps(p_info["widgets"])
                print(f"Updated page: {p_info['name']}")
        
        db.commit()

        # 3. Seed Menus
        menus = [
            {
                "name": "header",
                "items": [
                    {"label": "Accueil", "url": "home", "order": 0},
                    {"label": "Journal", "url": "article-list", "order": 1},
                    {"label": "À propos", "url": "about", "order": 2}
                ]
            },
            {
                "name": "footer",
                "items": [
                    {"label": "Mentions Légales", "url": "legal", "order": 0},
                    {"label": "Contact", "url": "contact", "order": 1},
                    {"label": "Newsletter", "url": "newsletter", "order": 2}
                ]
            }
        ]

        for m_data in menus:
            menu = db.query(models.Menu).filter(
                models.Menu.project_id == project_id,
                models.Menu.name == m_data["name"]
            ).first()
            if menu:
                db.query(models.MenuItem).filter(models.MenuItem.menu_id == menu.id).delete()
                db.delete(menu)
                db.commit()
            
            print(f"Seeding menu: {m_data['name']}")
            menu = models.Menu(name=m_data["name"], project_id=project_id, is_active=True)
            db.add(menu)
            db.commit()
            db.refresh(menu)

            for i, item_data in enumerate(m_data["items"]):
                item = models.MenuItem(
                    menu_id=menu.id,
                    label=item_data["label"],
                    url=item_data["url"],
                    order=i,
                    is_active=True
                )
                db.add(item)
        db.commit()

        # 4. Seed Articles
        articles = [
            {
                "title": "Les illusions de la souveraineté européenne",
                "slug": "illusions-souverainete-europeenne",
                "category": "POLITIQUE",
                "content": "<p>L'Union européenne est-elle vraiment l'échelle adéquate pour mener une politique au service des classes populaires ?</p>",
                "cover_image": "https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?auto=format&fit=crop&q=80"
            },
            {
                "title": "L'écologie politique face au capitalisme vert",
                "slug": "ecologie-politique-capitalisme-vert",
                "category": "ÉCOLOGIE",
                "content": "<p>Pourquoi la transition écologique nécessite une rupture radicale avec les logiques de marché.</p>",
                "cover_image": "https://images.unsplash.com/photo-1473341304170-971dccb5ac1e?auto=format&fit=crop&q=80"
            },
            {
                "title": "Pour un renouveau du syndicalisme d'action",
                "slug": "renouveau-syndicalisme-action",
                "category": "SOCIAL",
                "content": "<p>Comment reconstruire un rapport de force favorable aux travailleurs dans un monde du travail éclaté.</p>",
                "cover_image": "https://images.unsplash.com/photo-1531206715517-5c0ba140b2b8?auto=format&fit=crop&q=80"
            }
        ]

        # Get a default author
        author = db.query(models.User).filter(models.User.role_id != None).first()
        if not author:
            print("No author found, creating a default one...")
            author = models.User(username="admin_lava", email="admin@lava.be", hashed_password="hashed") # simplified
            db.add(author)
            db.commit()
            db.refresh(author)

        for a_data in articles:
            article = db.query(models.Article).filter(models.Article.slug == a_data["slug"]).first()
            if not article:
                print(f"Creating article: {a_data['title']}")
                article = models.Article(
                    title=a_data["title"],
                    slug=a_data["slug"],
                    content=a_data["content"],
                    cover_image=a_data["cover_image"],
                    category=a_data["category"],
                    status="PUBLISHED",
                    project_id=project_id,
                    author_id=author.id
                )
                db.add(article)
        db.commit()
        print("Production seeding completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding production: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_production()
