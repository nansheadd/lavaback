import sys
import os
import sqlite3

# Add current directory to path
sys.path.append(os.getcwd())

def update_schema():
    print("Updating database schema for App Builder...")
    
    db_path = "platform.db"
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check existing columns to avoid errors
        cursor.execute("PRAGMA table_info(projects)")
        columns = [info[1] for info in cursor.fetchall()]
        
        updates = [
            ("logo_url", "TEXT"),
            ("slogan", "TEXT"),
            ("is_active", "BOOLEAN DEFAULT 1"),
            ("global_styles", "TEXT DEFAULT '{}'")
        ]
        
        for col_name, col_type in updates:
            if col_name not in columns:
                print(f"Adding column {col_name}...")
                cursor.execute(f"ALTER TABLE projects ADD COLUMN {col_name} {col_type}")
            else:
                print(f"Column {col_name} already exists.")
                
        conn.commit()
        print("Schema update completed successfully.")
        
    except Exception as e:
        print(f"Error updating schema: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    update_schema()
