import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine
from app.models import Article, User, ArticleStatus, Role
from app.auth import get_password_hash

db = SessionLocal()

# 1. Find or create admin user
user = db.query(User).filter(User.username == "admin").first()
if not user:
    user = db.query(User).first()  # fallback: use any existing user
if not user:
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if not admin_role:
        print("Creating admin role...")
        admin_role = Role(name="admin", description="Admin Role")
        db.add(admin_role)
        db.commit()
        db.refresh(admin_role)
    
    user = User(
        username="admin",
        email="admin@lava.be",
        hashed_password=get_password_hash("admin123"),
        role_id=admin_role.id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print("Created new admin user.")

# 2. Add some Lava.be style articles
articles_to_seed = [
    {
        "title": "Les illusions de la souveraineté européenne",
        "slug": "illusions-souverainete-europeenne",
        "content": "<p>Face aux multiples crises qui secouent le capitalisme contemporain, l'Union européenne est souvent présentée comme la solution providentielle. On nous promet une 'souveraineté européenne' qui protègerait les citoyens de la mondialisation sauvage...</p><p>Pourtant, la réalité des politiques européennes démontre chaque jour le contraire.</p>",
        "excerpt": "L'Union européenne est-elle vraiment l'échelle adéquate pour mener une politique au service des classes populaires ?",
        "category": "Politique",
        "tags": "Europe, Souveraineté, Capitalisme",
        "cover_image": "https://images.unsplash.com/photo-1518534725357-e160161491ff?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80",
        "status": ArticleStatus.PUBLISHED
    },
    {
        "title": "L'écologie politique face au capitalisme vert",
        "slug": "ecologie-politique-capitalisme-vert",
        "content": "<p>La transition écologique ne peut se réduire à l'installation d'éoliennes et de panneaux solaires, ni au verdissement des portefeuilles d'investissement. L'urgence climatique exige de repenser fondamentalement nos modes de production et de consommation.</p><p>Le 'capitalisme vert' n'est qu'une illusion destinée à sauver un système fondé sur l'accumulation infinie.</p>",
        "excerpt": "Pourquoi la transition écologique nécessite une rupture radicale avec les logiques de marché.",
        "category": "Écologie",
        "tags": "Écologie politique, Transition, Climat",
        "cover_image": "https://images.unsplash.com/photo-1466611653911-95081537e5b7?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80",
        "status": ArticleStatus.PUBLISHED
    },
    {
        "title": "Pour un renouveau du syndicalisme d'action",
        "slug": "renouveau-syndicalisme-action",
        "content": "<p>Face à la dégradation continue des conditions de travail et à l'inflation galopante, le mouvement syndical semble parfois en recul. Or, l'histoire sociale nous enseigne que seuls les rapports de force concrets permettent d'arracher des victoires.</p><p>Il est temps d'inventer de nouvelles formes de mobilisation tout en renouant avec l'esprit combatif des premières grandes grèves.</p>",
        "excerpt": "Comment reconstruire un rapport de force favorable aux travailleurs dans un monde du travail éclaté.",
        "category": "Social",
        "tags": "Syndicalisme, Luttes sociales, Travail",
        "cover_image": "https://images.unsplash.com/photo-1541888086-2ae707923485?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80",
        "status": ArticleStatus.PUBLISHED
    }
]

import datetime
added_count = 0
for data in articles_to_seed:
    existing = db.query(Article).filter(Article.slug == data["slug"]).first()
    if not existing:
        article = Article(
            title=data["title"],
            slug=data["slug"],
            content=data["content"],
            excerpt=data["excerpt"],
            category=data["category"],
            tags=data["tags"],
            cover_image=data["cover_image"],
            status=data["status"],
            author_id=user.id,
            published_at=datetime.datetime.utcnow()
        )
        db.add(article)
        added_count += 1

db.commit()
print(f"Successfully added {added_count} articles.")
print(f"Admin User ID: {user.id}")
print("Admin login info:")
print("Username/Email: admin@lava.be")
print("Password: admin123")
db.close()
