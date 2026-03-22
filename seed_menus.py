from app.database import SessionLocal
from app.models.base_models import Menu, MenuItem
import datetime

db = SessionLocal()

PROJECT_ID = 7

def seed_menu(name, items):
    # Always recreate to ensure items are clean
    existing = db.query(Menu).filter(Menu.project_id == PROJECT_ID, Menu.name == name).first()
    if existing:
        print(f"Cleaning existing menu '{name}'...")
        db.query(MenuItem).filter(MenuItem.menu_id == existing.id).delete()
        db.delete(existing)
        db.commit()
    
    print(f"Creating menu '{name}' for project {PROJECT_ID}...")
    menu = Menu(
        name=name,
        project_id=PROJECT_ID,
        is_active=True
    )
    db.add(menu)
    db.commit()
    db.refresh(menu)
    
    for i, item_data in enumerate(items):
        item = MenuItem(
            menu_id=menu.id,
            label=item_data['label'],
            url=item_data['url'],
            order=i,
            is_active=True
        )
        db.add(item)
    
    db.commit()
    print(f"Added {len(items)} items to menu '{name}'.")
    return menu

# Seed Header
header_items = [
    {"label": "Accueil", "url": "home"},
    {"label": "Journal", "url": "article-list"}, # Assuming this slug or similar
    {"label": "À propos", "url": "about"}
]
seed_menu("header", header_items)

# Seed Footer
footer_items = [
    {"label": "Mentions Légales", "url": "legal"},
    {"label": "Contact", "url": "contact"},
    {"label": "Newsletter", "url": "newsletter"}
]
seed_menu("footer", footer_items)

db.close()
print("Done seeding menus.")
