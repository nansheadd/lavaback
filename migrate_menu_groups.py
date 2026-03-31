"""Migration: Add group_name column to menu_items table"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "app", "platform.db")
# Also try the root-level DB
DB_PATH_ROOT = os.path.join(os.path.dirname(__file__), "platform.db")

def migrate(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if column already exists
    cursor.execute("PRAGMA table_info(menu_items)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "group_name" not in columns:
        cursor.execute("ALTER TABLE menu_items ADD COLUMN group_name TEXT DEFAULT NULL")
        conn.commit()
        print(f"✅ Added 'group_name' column to menu_items in {db_path}")
    else:
        print(f"ℹ️  'group_name' column already exists in {db_path}")
    
    conn.close()

if __name__ == "__main__":
    for path in [DB_PATH, DB_PATH_ROOT]:
        if os.path.exists(path):
            migrate(path)
        else:
            print(f"⚠️  DB not found at {path}")
