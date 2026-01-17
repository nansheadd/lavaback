import sys
import os

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import database, models
from sqlalchemy import text

def migrate():
    print("Starting manual migration for Project Channels...")
    engine = database.engine
    
    # 1. Create tables that might not exist (ProjectStep)
    print("Creating new tables if missing...")
    models.Base.metadata.create_all(bind=engine)
    
    with engine.connect() as conn:
        # 2. Add project_id to chat_channels
        try:
            print("Attempting to add project_id to chat_channels...")
            # Note: SQLite might complain about REFERENCES in ALTER TABLE, so we handle it simply
            # If Postgres, REFERENCES works. If SQLite, usually ignored or supported in recent versions.
            # Using simple ADD COLUMN for safety if strictly SQLite limitations apply, but standard SQL usually okay.
            conn.execute(text("ALTER TABLE chat_channels ADD COLUMN project_id INTEGER REFERENCES projects(id)"))
            print("Successfully added project_id column.")
        except Exception as e:
            print(f"Skipping chat_channels update (might exist or error): {e}")

        # 3. Add step_id to review_threads
        try:
            print("Attempting to add step_id to review_threads...")
            conn.execute(text("ALTER TABLE review_threads ADD COLUMN step_id INTEGER REFERENCES project_steps(id)"))
            print("Successfully added step_id column.")
        except Exception as e:
            print(f"Skipping review_threads update (might exist or error): {e}")
            
        conn.commit()
    
    print("Migration completed.")

if __name__ == "__main__":
    migrate()
