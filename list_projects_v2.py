import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app import models

def list_projects():
    db = SessionLocal()
    try:
        projects = db.query(models.Project).all()
        for p in projects:
            print(f"ID: {p.id} | Title: {p.title} | Status: {p.status}")
    finally:
        db.close()

if __name__ == "__main__":
    list_projects()
