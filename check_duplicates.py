from app.database import SessionLocal
from app.models.base_models import Project
from sqlalchemy import func

def check_duplicates():
    db = SessionLocal()
    try:
        # Check for duplicates
        duplicates = db.query(Project.title, func.count(Project.title))\
            .group_by(Project.title)\
            .having(func.count(Project.title) > 1)\
            .all()
        
        if duplicates:
            print(f"Found {len(duplicates)} duplicated titles:")
            for title, count in duplicates:
                print(f" - '{title}': {count} copies")
        else:
            print("No duplicates found.")

        # List all for sanity
        print("\nAll Projects:")
        all_projs = db.query(Project).all()
        for p in all_projs:
            print(f"[{p.id}] {p.title}")

    finally:
        db.close()

if __name__ == "__main__":
    check_duplicates()
