import os
from sqlalchemy import create_engine, text

# Get DB URL
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not DATABASE_URL:
    print("No DATABASE_URL set. Trying sqlite if available or exiting.")
    # Fallback for testing if manual run locally
    DATABASE_URL = "sqlite:///./platform.db"

print(f"Connecting to DB...")
engine = create_engine(DATABASE_URL)

def run_fix():
    with engine.connect() as conn:
        # SQLite doesn't support isolation_level="AUTOCOMMIT" in the same way for schema changes sometimes,
        # but for PG it's needed for some operations.
        # However, for simple ALTER TABLE, standard transaction is fine.
        # But let's try to be generic. 
        if DATABASE_URL and "postgresql" in DATABASE_URL:
             conn = conn.execution_options(isolation_level="AUTOCOMMIT")

        print("Starting schema fix...")

        # 1. Add is_pinned to channel_messages
        print("Checking is_pinned...")
        try:
            if DATABASE_URL and "postgresql" in DATABASE_URL:
                conn.execute(text("ALTER TABLE channel_messages ADD COLUMN IF NOT EXISTS is_pinned BOOLEAN DEFAULT FALSE;"))
            else:
                # SQLite fallback: catch duplicate column error
                try:
                    conn.execute(text("ALTER TABLE channel_messages ADD COLUMN is_pinned BOOLEAN DEFAULT FALSE;"))
                except Exception as e:
                    if "duplicate column" in str(e).lower():
                        print("Column is_pinned already exists (SQLite).")
                    else:
                        raise e
            print("is_pinned checked/added.")
        except Exception as e:
            print(f"Note on is_pinned: {e}")

        # 2. Add reply_to_id to channel_messages
        print("Checking reply_to_id...")
        try:
            if DATABASE_URL and "postgresql" in DATABASE_URL:
                conn.execute(text("ALTER TABLE channel_messages ADD COLUMN IF NOT EXISTS reply_to_id INTEGER REFERENCES channel_messages(id);"))
            else:
                try:
                    conn.execute(text("ALTER TABLE channel_messages ADD COLUMN reply_to_id INTEGER REFERENCES channel_messages(id);"))
                except Exception as e:
                    if "duplicate column" in str(e).lower():
                         print("Column reply_to_id already exists (SQLite).")
                    else:
                        raise e
            print("reply_to_id checked/added.")
        except Exception as e:
            print(f"Note on reply_to_id: {e}")

        # 3. Create message_reactions table
        try:
            print("Checking message_reactions table...")
            # PG syntax for serial. SQLite uses INTEGER PRIMARY KEY AUTOINCREMENT
            if DATABASE_URL and "postgresql" in DATABASE_URL:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS message_reactions (
                        id SERIAL PRIMARY KEY,
                        message_id INTEGER REFERENCES channel_messages(id) ON DELETE CASCADE,
                        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                        emoji VARCHAR NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );
                """))
            else:
                 # SQLite syntax
                 conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS message_reactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        message_id INTEGER REFERENCES channel_messages(id) ON DELETE CASCADE,
                        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                        emoji VARCHAR NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    );
                """))
            print("message_reactions checked/created.")
        except Exception as e:
            print(f"Error creating message_reactions: {e}")

        # 4. Update Projects table (App Builder fields)
        print("Checking projects table schema...")
        project_updates = [
            ("logo_url", "VARCHAR", "TEXT"),
            ("slogan", "VARCHAR", "TEXT"),
            ("is_active", "BOOLEAN DEFAULT TRUE", "BOOLEAN DEFAULT 1"), 
            ("global_styles", "TEXT DEFAULT '{}'", "TEXT DEFAULT '{}'")
        ]

        for col, pg_type, sqlite_type in project_updates:
            try:
                if DATABASE_URL and "postgresql" in DATABASE_URL:
                    conn.execute(text(f"ALTER TABLE projects ADD COLUMN IF NOT EXISTS {col} {pg_type};"))
                else:
                    try:
                        conn.execute(text(f"ALTER TABLE projects ADD COLUMN {col} {sqlite_type};"))
                    except Exception as e:
                         if "duplicate column" in str(e).lower():
                             print(f"Column {col} already exists (SQLite).")
                         else:
                             raise e
                print(f"Column {col} checked/added.")
            except Exception as e:
                print(f"Error adding {col} to projects: {e}")
        
        # 4.1 Update BuilderPages table
        print("Checking builder_pages table schema...")
        bp_updates = [
            ("description", "TEXT", "TEXT"),
            ("category", "VARCHAR", "VARCHAR")
        ]
        for col, pg_type, sqlite_type in bp_updates:
            try:
                if DATABASE_URL and "postgresql" in DATABASE_URL:
                    conn.execute(text(f"ALTER TABLE builder_pages ADD COLUMN IF NOT EXISTS {col} {pg_type};"))
                else:
                    try:
                        conn.execute(text(f"ALTER TABLE builder_pages ADD COLUMN {col} {sqlite_type};"))
                    except Exception as e:
                         if "duplicate column" in str(e).lower():
                             print(f"Column {col} already exists in builder_pages (SQLite).")
                         else:
                             raise e
                print(f"Column {col} checked/added to builder_pages.")
            except Exception as e:
                print(f"Error adding {col} to builder_pages: {e}")
        
        # 5. Add project_id to chat_channels
        print("Checking chat_channels schema...")
        try:
            if DATABASE_URL and "postgresql" in DATABASE_URL:
                conn.execute(text("ALTER TABLE chat_channels ADD COLUMN IF NOT EXISTS project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE;"))
            else:
                try:
                    conn.execute(text("ALTER TABLE chat_channels ADD COLUMN project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE;"))
                except Exception as e:
                     if "duplicate column" in str(e).lower():
                         print("Column project_id already exists in chat_channels (SQLite).")
                     else:
                         raise e
            print("chat_channels project_id checked/added.")
        except Exception as e:
            print(f"Error adding project_id to chat_channels: {e}")

        # 6. Add step_id to review_threads
        print("Checking review_threads schema...")
        try:
            if DATABASE_URL and "postgresql" in DATABASE_URL:
                conn.execute(text("ALTER TABLE review_threads ADD COLUMN IF NOT EXISTS step_id INTEGER REFERENCES project_steps(id);"))
            else:
                try:
                    conn.execute(text("ALTER TABLE review_threads ADD COLUMN step_id INTEGER REFERENCES project_steps(id);"))
                except Exception as e:
                     if "duplicate column" in str(e).lower():
                         print("Column step_id already exists in review_threads (SQLite).")
                     else:
                         raise e
            print("review_threads step_id checked/added.")
        except Exception as e:
            print(f"Error adding step_id to review_threads: {e}")

        # 7. Add chat_thread_id to review_threads
        print("Checking review_threads schema (chat_thread_id)...")
        try:
            if DATABASE_URL and "postgresql" in DATABASE_URL:
                conn.execute(text("ALTER TABLE review_threads ADD COLUMN IF NOT EXISTS chat_thread_id INTEGER REFERENCES channel_messages(id);"))
            else:
                try:
                    conn.execute(text("ALTER TABLE review_threads ADD COLUMN chat_thread_id INTEGER REFERENCES channel_messages(id);"))
                except Exception as e:
                     if "duplicate column" in str(e).lower():
                         print("Column chat_thread_id already exists in review_threads (SQLite).")
                     else:
                         raise e
            print("review_threads chat_thread_id checked/added.")
        except Exception as e:
            print(f"Error adding chat_thread_id to review_threads: {e}")

        # 8. Add project_id to articles
        print("Checking articles schema (project_id)...")
        try:
            if DATABASE_URL and "postgresql" in DATABASE_URL:
                conn.execute(text("ALTER TABLE articles ADD COLUMN IF NOT EXISTS project_id INTEGER REFERENCES projects(id);"))
            else:
                try:
                    conn.execute(text("ALTER TABLE articles ADD COLUMN project_id INTEGER REFERENCES projects(id);"))
                except Exception as e:
                     if "duplicate column" in str(e).lower():
                         print("Column project_id already exists in articles (SQLite).")
                     else:
                         raise e
            print("articles project_id checked/added.")
        except Exception as e:
            print(f"Error adding project_id to articles: {e}")

        print("Schema fix complete.")

if __name__ == "__main__":
    run_fix()
