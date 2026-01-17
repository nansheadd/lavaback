
from app import models, database

db = database.SessionLocal()

# Check Projects
projects = db.query(models.Project).all()
print(f"Projects count: {len(projects)}")
for p in projects:
    print(f"Project: {p.id} - {p.title}")

# Check Pages
pages = db.query(models.BuilderPage).all()
print(f"Pages count: {len(pages)}")
for p in pages:
    print(f"Page: {p.id} - {p.slug} - ProjectID: {p.project_id}")

db.close()
