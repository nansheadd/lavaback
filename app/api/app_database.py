
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app import models, database
from app.auth import get_current_user
from app.core.project_db import get_project_db_engine, get_project_table_name, is_external_db

router = APIRouter()

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Schemas
class ColumnDef(BaseModel):
    name: str
    type: str # TEXT, INTEGER, BOOLEAN, etc.
    nullable: bool = True
    primary_key: bool = False

class TableCreate(BaseModel):
    name: str
    columns: List[ColumnDef]

class TableInfo(BaseModel):
    name: str
    display_name: str # name without prefix
    columns: List[Dict[str, Any]]

@router.get("/apps/{app_id}/tables", response_model=List[TableInfo])
def list_app_tables(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Verify app exists and user has access
    project = db.query(models.Project).get(app_id)
    if not project:
        raise HTTPException(status_code=404, detail="App not found")
    
    # Resolve DB Engine
    try:
        engine = get_project_db_engine(app_id, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

    try:
        inspector = inspect(engine)
        all_tables = inspector.get_table_names()
    except Exception as e:
        print(f"Error inspecting tables: {e}")
        return []

    app_tables = []
    is_external = is_external_db(app_id, db)
    prefix = f"app_{app_id}_"

    for table in all_tables:
        # If external, show all. If internal, show only prefixed.
        if is_external or table.startswith(prefix):
            columns = []
            try:
                for col in inspector.get_columns(table):
                    columns.append({
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col["nullable"]
                    })
            except Exception as e:
                # Some tables might have complex types or issues
                print(f"Error inspecting table {table}: {e}")
                continue
            
            display_name = table if is_external else table[len(prefix):]
            
            app_tables.append({
                "name": table,
                "display_name": display_name,
                "columns": columns
            })
            
    return app_tables

@router.post("/apps/{app_id}/tables")
def create_app_table(
    app_id: int,
    table_def: TableCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Verify app/permissions
    project = db.query(models.Project).get(app_id)
    if not project:
        raise HTTPException(status_code=404, detail="App not found")
    
    try:
        engine = get_project_db_engine(app_id, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

    full_table_name = get_project_table_name(app_id, table_def.name, db)
    
    # Check if exists
    inspector = inspect(engine)
    if inspector.has_table(full_table_name):
        raise HTTPException(status_code=400, detail="Table already exists")
    
    # Construct SQL
    TYPE_MAP = {
        "text": "TEXT",
        "string": "VARCHAR(255)",
        "integer": "INTEGER",
        "boolean": "BOOLEAN",
        "timestamp": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "json": "JSONB"
    }
    
    # Check if ID should be AUTOINCREMENT (sqlite) or SERIAL (postgres)
    # Simple check on drivername
    is_postgres = "postgresql" in engine.name
    id_col = "id SERIAL PRIMARY KEY" if is_postgres else "id INTEGER PRIMARY KEY AUTOINCREMENT"
    
    cols_sql = [id_col]
    
    for col in table_def.columns:
        if col.name == "id": continue 
        
        sql_type = TYPE_MAP.get(col.type.lower(), "TEXT")
        nullable = "NULL" if col.nullable else "NOT NULL"
        cols_sql.append(f"{col.name} {sql_type} {nullable}")
    
    # Add timestamps if not exists
    if not any(c.name == 'created_at' for c in table_def.columns):
        cols_sql.append("created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    
    create_stmt = f"CREATE TABLE {full_table_name} ({', '.join(cols_sql)});"
    
    try:
        with engine.begin() as conn:
            conn.execute(text(create_stmt))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return {"status": "created", "table": full_table_name}

@router.delete("/apps/{app_id}/tables/{table_name}")
def delete_app_table(
    app_id: int,
    table_name: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    try:
        engine = get_project_db_engine(app_id, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

    full_table_name = get_project_table_name(app_id, table_name, db)
    
    # Security check for internal DBs
    if not is_external_db(app_id, db):
        expected_prefix = f"app_{app_id}_"
        if not full_table_name.startswith(expected_prefix):
             raise HTTPException(status_code=400, detail="Invalid table name")

    try:
        with engine.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {full_table_name}"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return {"status": "deleted"}

@router.get("/apps/{app_id}/data/{table_name}")
def read_app_table_data(
    app_id: int,
    table_name: str,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    try:
        engine = get_project_db_engine(app_id, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

    full_table_name = get_project_table_name(app_id, table_name, db)
    
    # Security check for internal DBs
    if not is_external_db(app_id, db):
        expected_prefix = f"app_{app_id}_"
        if not full_table_name.startswith(expected_prefix):
             raise HTTPException(status_code=400, detail="Invalid table name")

    # Check existence
    inspector = inspect(engine)
    if not inspector.has_table(full_table_name):
        raise HTTPException(status_code=404, detail="Table not found")
        
    try:
        with engine.connect() as conn:
            # Fetch Data
            query = text(f"SELECT * FROM {full_table_name} LIMIT :limit OFFSET :offset")
            result = conn.execute(query, {"limit": limit, "offset": offset})
            rows = [dict(row._mapping) for row in result]
            
            # Count
            count_query = text(f"SELECT COUNT(*) FROM {full_table_name}")
            total = conn.scalar(count_query)
            
            return {"data": rows, "total": total}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
