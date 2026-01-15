import sys
import os
import json
import uuid
from datetime import datetime

# Add current directory to path so we can import app modules
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models.base_models import Role, User
from app.models.article import Article, ArticleStatus
from app.models.builder_page import BuilderPage
from app.auth import get_password_hash

def seed_home_v2():
    print("Seeding Home V2 Data...")
    db = SessionLocal()

    try:
        # 1. Ensure Roles (simplified check)
        author_role = db.query(Role).filter(Role.name == "author").first()
        if not author_role:
            print("Creating author role...")
            author_role = Role(name="author", permissions=json.dumps(["view:own_content", "edit:own_content"]))
            db.add(author_role)
            db.commit()

        # 2. Create Demo Author
        demo_author = db.query(User).filter(User.email == "alice@writer.com").first()
        if not demo_author:
            print("Creating demo author...")
            hashed_pwd = get_password_hash("password")
            demo_author = User(
                username="AliceWriter",
                email="alice@writer.com",
                hashed_password=hashed_pwd,
                role_id=author_role.id,
                is_active=True
            )
            db.add(demo_author)
            db.commit()
            db.refresh(demo_author)
        
        print(f"Using Author: {demo_author.username} (ID: {demo_author.id})")

        # 3. Create Articles
        articles_data = [
            {
                "title": "Lancement de Lava V2",
                "slug": "lancement-lava-v2",
                "content": "<p>Nous sommes ravis de vous présenter la nouvelle version de notre plateforme...</p>",
                "excerpt": "Découvrez les nouvelles fonctionnalités incroyables de Lava V2.",
                "cover_image": "https://images.unsplash.com/photo-1519389950473-47ba0277781c?ixlib=rb-4.0.3&auto=format&fit=crop&w=1000&q=80",
                "category": "News"
            },
            {
                "title": "Guide du Débutant : Créer sa première page",
                "slug": "guide-debutant-creation-page",
                "content": "<p>Apprenez à utiliser notre constructeur de page intuitif en quelques minutes...</p>",
                "excerpt": "Un tutoriel complet pour prendre en main le builder.",
                "cover_image": "https://images.unsplash.com/photo-1498050108023-c5249f4df085?ixlib=rb-4.0.3&auto=format&fit=crop&w=1000&q=80",
                "category": "Tutoriels"
            },
            {
                "title": "L'avenir du No-Code",
                "slug": "avenir-no-code",
                "content": "<p>Analyse des tendances du marché et pourquoi le No-Code est l'avenir...</p>",
                "excerpt": "Pourquoi vous devriez vous intéresser au No-Code dès maintenant.",
                "cover_image": "https://images.unsplash.com/photo-1504384308090-c54be3855833?ixlib=rb-4.0.3&auto=format&fit=crop&w=1000&q=80",
                "category": "Tech"
            }
        ]

        for art in articles_data:
            existing = db.query(Article).filter(Article.slug == art["slug"]).first()
            if not existing:
                print(f"Creating article: {art['title']}")
                article = Article(
                    title=art["title"],
                    slug=art["slug"],
                    content=art["content"],
                    excerpt=art["excerpt"],
                    cover_image=art["cover_image"],
                    category=art["category"],
                    status=ArticleStatus.PUBLISHED,
                    author_id=demo_author.id,
                    published_at=datetime.utcnow()
                )
                db.add(article)
            else:
                print(f"Article {art['title']} already exists")
        
        db.commit()

        # 4. Create/Update Home Page
        home_page = db.query(BuilderPage).filter(BuilderPage.slug == "home").first()
        
        # Define Widgets JSON
        # Structure: i, x, y, w, h, toolId, data
        widgets = []
        
        # Row 1: Navbar
        widgets.append({
            "i": "nav-1", "x": 0, "y": 0, "w": 24, "h": 3,
            "toolId": "navbar",
            "data": {
                "logoText": "Lava Portal",
                "links": [
                    {"label": "Accueil", "href": "/home", "variant": "link"},
                    {"label": "Articles", "href": "/articles", "variant": "link"},
                    {"label": "Contact", "href": "/contact", "variant": "button-primary"}
                ]
            }
        })
        
        # Row 2: Hero
        widgets.append({
            "i": "hero-1", "x": 0, "y": 3, "w": 24, "h": 14, # Taller Hero
            "toolId": "hero",
            "data": {
                "title": "Analyses critiques & Perspectives",
                "subtitle": "Lava est une revue belge d'analyse sociale et politique.",
                "buttonText": "S'abonner",
                "imageUrl": "https://images.unsplash.com/photo-1444653614773-8b83df53c566?q=80&w=2000&auto=format&fit=crop" # More textured/darker image
            }
        })
        
        # Row 3: Article List (Directly after Hero)
        widgets.append({
            "i": "article-list-1", "x": 0, "y": 17, "w": 24, "h": 20,
            "toolId": "article-list",
            "data": {
                "limit": 6, # More articles
                "layout": "grid",
                "title": "Dernières Publications" # Built-in title in tool
            }
        })
        
        # Row 5: Footer
        widgets.append({
            "i": "footer-1", "x": 0, "y": 35, "w": 24, "h": 6,
            "toolId": "footer",
            "data": {
                "copyright": f"© {datetime.now().year} Lava Inc. Tous droits réservés."
            }
        })

        if not home_page:
            print("Creating Home Page...")
            home_page = BuilderPage(
                name="Home",
                slug="home",
                description="Landing page principale",
                access_level="public",
                widgets_json=json.dumps(widgets)
            )
            db.add(home_page)
        else:
            print("Updating Home Page...")
            home_page.widgets_json = json.dumps(widgets)
            home_page.access_level = "public"
        
        db.commit()
        print("Home page seeded successfully!")

    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_home_v2()
