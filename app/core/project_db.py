from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.orm import sessionmaker, Session
from app import models, database
from typing import Optional

# Cache engines to avoid overhead
# Key: project_id -> Engine
_engine_cache = {}

def get_project_db_engine(project_id: int, db_session: Session):
    """
    Returns the SQLAlchemy Engine for a given project.
    If the project uses an external DB, returns that engine.
    If internal, returns the main DB engine.
    """
    project = db_session.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise Exception("Project not found")

    if project.db_type == "external" and project.db_connection_string:
        # Use external DB
        conn_str = project.db_connection_string
        
        # Simple caching mechanism 
        # Note: This doesn't handle updates to connection string ideally (would need app restart or cache clearing)
        # For this MVP, we will rely on checking if cache exists. 
        # In a real app, we'd want to invalidate this cache when project is updated.
        if project_id in _engine_cache:
            # Verify if connection string changed? For now assume it's stable per session or requires restart
            pass
            # To be safe, let's just create a new one if it's not resource intensive, 
            # OR better: checking equality is hard without storing the string in cache. 
            # I'll enable caching but simplistic.
            if _engine_cache[project_id].url.render_as_string(hide_password=False) == conn_str:
                 return _engine_cache[project_id]

        try:
            # Fix for Fly.io/Heroku postgres URLs if needed
            if conn_str.startswith("postgres://"):
                 conn_str = conn_str.replace("postgres://", "postgresql://", 1)
                 
            engine = create_engine(conn_str)
            _engine_cache[project_id] = engine
            return engine
        except Exception as e:
            raise Exception(f"Failed to connect to external database: {str(e)}")
            
    else:
        # Use Internal DB
        return database.engine

def get_project_table_name(project_id: int, table_name: str, db_session: Session) -> str:
    """
    Returns the actual table name.
    Internal: app_{id}_{table_name}
    External: {table_name}
    """
    project = db_session.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise Exception("Project not found")
        
    if project.db_type == "external" and project.db_connection_string:
        return table_name
    else:
        # Internal naming convention
        safe_name = table_name.lower().replace(" ", "_").replace("-", "_")
        return f"app_{project_id}_{safe_name}"

def is_external_db(project_id: int, db_session: Session) -> bool:
     project = db_session.query(models.Project).filter(models.Project.id == project_id).first()
     return bool(project and project.db_type == "external" and project.db_connection_string)

def clear_project_cache(project_id: int):
    if project_id in _engine_cache:
        try:
            _engine_cache[project_id].dispose()
        except:
            pass
        del _engine_cache[project_id]
