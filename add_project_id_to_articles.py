import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "platform.db")

def upgrade_db():
    print(f"Connecting to {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if project_id exists
        cursor.execute("PRAGMA table_info(articles)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if "project_id" not in columns:
            print("Adding project_id column to articles table...")
            cursor.execute("ALTER TABLE articles ADD COLUMN project_id INTEGER REFERENCES projects(id)")
            conn.commit()
            print("Successfully added project_id column.")
        else:
            print("Column project_id already exists in articles table.")

    except Exception as e:
        print(f"Error updating database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    upgrade_db()
