
from app import models, database

db = database.SessionLocal()

# Link "Article" page (slug='article' or id=17 based on check) to Project 7 (Lava Portal)
page = db.query(models.BuilderPage).filter(models.BuilderPage.slug == "article").first()
if page:
    print(f"Found page: {page.slug} (ID: {page.id})")
    page.project_id = 7
    db.commit()
    print("Linked to Project 7")
else:
    print("Article page not found")

db.close()
