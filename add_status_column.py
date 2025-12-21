import sqlite3
import os

DB_NAME = "platform.db"

def migrate():
    if not os.path.exists(DB_NAME):
        print(f"Database {DB_NAME} not found!")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "status" not in columns:
            print("Adding status column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN status VARCHAR DEFAULT 'offline'")
            conn.commit()
            print("Migration successful: Added status column.")
        else:
            print("Status column already exists.")
            
    except Exception as e:
        print(f"Error migrating database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
