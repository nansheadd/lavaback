import sqlite3
import os

DB_FILE = "platform.db"

def check_tables():
    if not os.path.exists(DB_FILE):
        print(f"Database file {DB_FILE} not found.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        print("Tables found:", tables)
        
        if "articles" in tables and "article_reviews" in tables:
            print("SUCCESS: Article tables created.")
        else:
            print("WARNING: Article tables NOT found.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_tables()
