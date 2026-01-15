from app.database import SessionLocal
from app.models.base_models import ActivityLog
from datetime import datetime, timedelta

def seed_activity():
    db = SessionLocal()
    
    # Check if we already have recent logs to avoid duplicates if run multiple times (optional, but good practice)
    # simplified: just add them.

    now = datetime.utcnow()

    logs = [
        {
            "action": "DÉPLOIEMENT FRONTEND",
            "details": "Refonte 'App-Centric' du Builder : Dashboard des applications, Sidebar dédiée et nouveau design Lava Media (Orange/Navy).",
            "resource_type": "page", # Blue (Frontend)
            "timestamp": now
        },
        {
            "action": "MISE À JOUR BACKEND",
            "details": "Implémentation de l'interface Admin Database (CRUD tables) et API Chat avancée (Pins, Réactions).",
            "resource_type": "project", # Green (Backend)
            "timestamp": now - timedelta(minutes=5)
        },
        {
            "action": "SÉCURITÉ & AUTH",
            "details": "Support du Login par Email, correction du label 'Username' et sécurisation des routes Admin.",
            "resource_type": "auth", # Amber (Security)
            "timestamp": now - timedelta(minutes=10)
        },
        {
            "action": "DONNÉES & PRODUCTION",
            "details": "Seeding de la page d'accueil (v2) et liaison automatique des projets.",
            "resource_type": "project", # Green or Default? Let's use 'project' for 'Data' as it is backend related, or I can use a type that defaults to gray if I omit resource_type or set 'system'
            # Frontend uses default->Gray. Let's use 'system' for Data/System
            "resource_type": "system",
            "timestamp": now - timedelta(minutes=15)
        }
    ]

    print(f"Adding {len(logs)} activity logs...")
    for log_data in logs:
        log = ActivityLog(**log_data)
        db.add(log)

    db.commit()
    print("Done! Recent Activity populated.")

if __name__ == "__main__":
    seed_activity()
