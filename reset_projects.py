import sys
import os
import json

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app import models

# Re-create tables if needed (optional)
# models.Base.metadata.create_all(bind=engine)

def reset_projects():
    db = SessionLocal()
    try:
        # Delete existing
        db.query(models.Project).delete()
        
        projects = [
            models.Project(
                title="Article System", 
                description="Gestion éditoriale et publication", 
                status="VALIDATED",
                checklist=json.dumps([
                    {"id": 16001, "text": "Modèle Article & API", "checked": True},
                    {"id": 16002, "text": "Vue Editor Pleine Page", "checked": True},
                    {"id": 16003, "text": "Workflow Status (Draft->Published)", "checked": True},
                    {"id": 16004, "text": "Article Reader (Public View)", "checked": True},
                    {"id": 16005, "text": "Intégration Builder Widget", "checked": True},
                ])
            ),
            models.Project(
                title="App Builder", 
                description="Constructeur de pages", 
                status="VALIDATED",
                checklist=json.dumps([
                    {"id": 16101, "text": "Drag & Drop Canvas", "checked": True},
                    {"id": 16102, "text": "Tool Registry (Widgets)", "checked": True},
                    {"id": 16103, "text": "Property Editor Sidebar", "checked": True},
                    {"id": 16104, "text": "Save & Load Pages", "checked": True},
                ])
            ),
            models.Project(
                title="Workflows", 
                description="Automatisation no-code", 
                status="VALIDATED",
                checklist=json.dumps([
                    {"id": 16201, "text": "Visual Flow Builder", "checked": True},
                    {"id": 16202, "text": "Triggers & Actions", "checked": True},
                    {"id": 16203, "text": "Execution Engine", "checked": True},
                    {"id": 16204, "text": "Logs & Debugging", "checked": True},
                ])
            ),
            models.Project(
                title="Rich Editor", 
                description="Éditeur avancé", 
                status="VALIDATED",
                checklist=json.dumps([
                    {"id": 16301, "text": "Tiptap Integration", "checked": True},
                    {"id": 16302, "text": "Split View Preview", "checked": True},
                    {"id": 16303, "text": "Image Upload Handler", "checked": True},
                    {"id": 16304, "text": "Markdown Support", "checked": True},
                ])
            ),
            models.Project(
                title="CRM & Projects", 
                description="Gestion de roadmap", 
                status="VALIDATED",
                checklist=json.dumps([
                    {"id": 16401, "text": "Kanban Board", "checked": True},
                    {"id": 16402, "text": "Project List & Filtering", "checked": True},
                    {"id": 16403, "text": "Project Detail View", "checked": True},
                    {"id": 16404, "text": "Precision Mode (Pins)", "checked": True},
                ])
            ),
        ]
        
        db.add_all(projects)
        db.commit()
        print("Projects reset successfully.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_projects()
