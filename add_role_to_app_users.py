import sqlite3

def upgrade():
    # Connect to the SQLite database
    conn = sqlite3.connect('platform.db')
    cursor = conn.cursor()

    # Check if the column already exists
    cursor.execute("PRAGMA table_info(app_users)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'role' not in columns:
        print("Adding 'role' column to 'app_users' table...")
        cursor.execute("ALTER TABLE app_users ADD COLUMN role VARCHAR DEFAULT 'free'")
        conn.commit()
        print("Successfully added 'role' column.")
    else:
        print("'role' column already exists in 'app_users' table.")

    conn.close()

if __name__ == '__main__':
    upgrade()
