import sys
import os
import json

# Add current directory to path so we can import app modules
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models.base_models import Project, ProjectStatus
from app.models.builder_page import BuilderPage

def link_home_to_app():
    print("Linking Home Page to Application...")
    db = SessionLocal()
    
    try:
        # 1. Find or Create Main App
        app_title = "Lava Portal"
        project = db.query(Project).filter(Project.title == app_title).first()
        
        if not project:
            print(f"Creating project '{app_title}'...")
            project = Project(
                title=app_title,
                description="Le portail principal de Lava Media.",
                status=ProjectStatus.IN_PROGRESS.value,
                is_active=True,
                slogan="Analyses critiques & Perspectives",
                logo_url="https://lavamedia.be/wp-content/uploads/2017/09/logo-lava.png" # Example placeholder
            )
            db.add(project)
            db.commit()
            db.refresh(project)
        else:
            print(f"Project '{app_title}' already exists (ID: {project.id})")

        # 2. Find Home Page
        home_page = db.query(BuilderPage).filter(BuilderPage.slug == "home").first()
        
        if home_page:
            if home_page.project_id != project.id:
                print(f"Linking Home Page (ID: {home_page.id}) to Project (ID: {project.id})...")
                home_page.project_id = project.id
                db.commit()
                print("Link successful!")
            else:
                print("Home page is already linked to this project.")
        else:
            print("Home page not found! Please run seed_home_v2.py first.")

    except Exception as e:
        print(f"Error linking data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    link_home_to_app()
