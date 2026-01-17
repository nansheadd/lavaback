
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app import models, database
from app.auth import get_current_user

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

# Helper to get prefixed table name
def get_table_name(app_id: int, name: str) -> str:
    safe_name = name.lower().replace(" ", "_").replace("-", "_")
    return f"app_{app_id}_{safe_name}"

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
    
    # Inspect tables
    inspector = inspect(db.get_bind())
    all_tables = inspector.get_table_names()
    
    prefix = f"app_{app_id}_"
    app_tables = []
    
    for table in all_tables:
        if table.startswith(prefix):
            columns = []
            for col in inspector.get_columns(table):
                columns.append({
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col["nullable"]
                })
            
            app_tables.append({
                "name": table,
                "display_name": table[len(prefix):],
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
    
    full_table_name = get_table_name(app_id, table_def.name)
    
    # Check if exists
    inspector = inspect(db.get_bind())
    if inspector.has_table(full_table_name):
        raise HTTPException(status_code=400, detail="Table already exists")
    
    # Construct SQL
    # WARNING: This is raw SQL construction. Validate types strictly or map them.
    # Supported types map
    TYPE_MAP = {
        "text": "TEXT",
        "string": "VARCHAR(255)",
        "integer": "INTEGER",
        "boolean": "BOOLEAN",
        "timestamp": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "json": "JSONB"
    }
    
    cols_sql = ["id SERIAL PRIMARY KEY"] # Always ID
    
    for col in table_def.columns:
        if col.name == "id": continue 
        
        sql_type = TYPE_MAP.get(col.type.lower(), "TEXT")
        nullable = "NULL" if col.nullable else "NOT NULL"
        cols_sql.append(f"{col.name} {sql_type} {nullable}")
    
    # Add timestamps
    cols_sql.append("created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    
    create_stmt = f"CREATE TABLE {full_table_name} ({', '.join(cols_sql)});"
    
    try:
        db.execute(text(create_stmt))
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
        
    return {"status": "created", "table": full_table_name}

@router.delete("/apps/{app_id}/tables/{table_name}")
def delete_app_table(
    app_id: int,
    table_name: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    full_table_name = get_table_name(app_id, table_name)
    
    # Security check: ensure it starts with prefix
    expected_prefix = f"app_{app_id}_"
    if not full_table_name.startswith(expected_prefix):
         raise HTTPException(status_code=400, detail="Invalid table name")

    try:
        db.execute(text(f"DROP TABLE IF EXISTS {full_table_name}"))
        db.commit()
    except Exception as e:
        db.rollback()
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
    full_table_name = get_table_name(app_id, table_name)
    
    # Security check
    expected_prefix = f"app_{app_id}_"
    if not full_table_name.startswith(expected_prefix):
         raise HTTPException(status_code=400, detail="Invalid table name")

    # Check existence
    inspector = inspect(db.get_bind())
    if not inspector.has_table(full_table_name):
        raise HTTPException(status_code=404, detail="Table not found")
        
    try:
        # Fetch Data
        query = text(f"SELECT * FROM {full_table_name} LIMIT :limit OFFSET :offset")
        result = db.execute(query, {"limit": limit, "offset": offset})
        rows = [dict(row._mapping) for row in result]
        
        # Count
        count_query = text(f"SELECT COUNT(*) FROM {full_table_name}")
        total = db.scalar(count_query)
        
        return {"data": rows, "total": total}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
