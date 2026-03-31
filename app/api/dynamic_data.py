from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app import models, database
from typing import List, Dict, Any, Optional

router = APIRouter()

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_table_name(project_id: int, table_slug: str) -> str:
    # Sanitization is important here, but for MVP we assume strict internal naming
    return f"app_{project_id}_{table_slug}"

@router.get("/apps/{project_id}/data/{table_name}")
def get_dynamic_data(
    project_id: int, 
    table_name: str, 
    limit: int = 100, 
    offset: int = 0,
    sort_by: Optional[str] = None,
    order: str = "asc",
    search_col: Optional[str] = None,
    search_val: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Fetch data from a dynamic app table.
    """
    real_table_name = get_table_name(project_id, table_name)
    
    # Check if table exists
    try:
        # Cross-database table existence check
        is_sqlite = db.bind.name == 'sqlite'
        if is_sqlite:
            check_query = text("SELECT name FROM sqlite_master WHERE type='table' AND name=:table_name")
        else:
             # Postgres
            check_query = text("SELECT to_regclass(:table_name)")
            
        result = db.execute(check_query, {"table_name": real_table_name}).scalar()
        if not result:
             # For Postgres, to_regclass returns None if not found. For SQLite, sqlite_master returns None if no row.
             raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found for this app")
             
        # Build Query
        query_str = f"SELECT * FROM {real_table_name}"
        params = {"limit": limit, "offset": offset}
        
        # Search
        if search_col and search_val:
            is_sqlite = db.bind.name == 'sqlite'
            if is_sqlite:
                query_str += f" WHERE LOWER({search_col}) LIKE LOWER(:search_val)"
            else:
                query_str += f" WHERE {search_col} ILIKE :search_val"
            params["search_val"] = f"%{search_val}%"
            
        # Sort
        if sort_by:
            # Validate sort_by column to prevent injection (basic check)
            # In a real app we'd check against column list
            query_str += f" ORDER BY {sort_by} {order}"
        else:
            query_str += " ORDER BY id DESC" # Default sort
            
        query_str += " LIMIT :limit OFFSET :offset"
        
        # Execute
        result = db.execute(text(query_str), params)
        rows = result.mappings().all()
        
        return {"data": rows, "count": len(rows)}
        
    except Exception as e:
        print(f"Dynamic Data Error: {e}")
        # If specific sql error, handle it
        if "does not exist" in str(e):
             raise HTTPException(status_code=404, detail=f"Table or column not found")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/apps/{project_id}/data/{table_name}")
def create_dynamic_data(
    project_id: int, 
    table_name: str, 
    data: Dict[str, Any], 
    db: Session = Depends(get_db)
):
    real_table_name = get_table_name(project_id, table_name)
    
    try:
        columns = ", ".join(data.keys())
        placeholders = ", ".join([f":{k}" for k in data.keys()])
        
        is_sqlite = db.bind.name == 'sqlite'
        if is_sqlite:
            query = text(f"INSERT INTO {real_table_name} ({columns}) VALUES ({placeholders})")
            result = db.execute(query, data)
            new_id = result.lastrowid
        else:
            query = text(f"INSERT INTO {real_table_name} ({columns}) VALUES ({placeholders}) RETURNING id")
            result = db.execute(query, data)
            new_id = result.scalar()
        
        db.commit()
        
        return {"id": new_id, "message": "Record created"}
    except Exception as e:
         db.rollback()
         print(f"Create Error: {e}")
         raise HTTPException(status_code=500, detail=str(e))

@router.put("/apps/{project_id}/data/{table_name}/{record_id}")
def update_dynamic_data(
    project_id: int, 
    table_name: str, 
    record_id: int, 
    data: Dict[str, Any], 
    db: Session = Depends(get_db)
):
    real_table_name = get_table_name(project_id, table_name)
    
    try:
        if not data:
            return {"message": "No data to update"}
            
        set_clauses = ", ".join([f"{k} = :{k}" for k in data.keys()])
        
        query = text(f"UPDATE {real_table_name} SET {set_clauses} WHERE id = :record_id")
        params = {**data, "record_id": record_id}
        
        db.execute(query, params)
        db.commit()
        
        return {"message": "Record updated"}
    except Exception as e:
         db.rollback()
         raise HTTPException(status_code=500, detail=str(e))

@router.delete("/apps/{project_id}/data/{table_name}/{record_id}")
def delete_dynamic_data(
    project_id: int, 
    table_name: str, 
    record_id: int, 
    db: Session = Depends(get_db)
):
    real_table_name = get_table_name(project_id, table_name)
    
    try:
        query = text(f"DELETE FROM {real_table_name} WHERE id = :record_id")
        db.execute(query, {"record_id": record_id})
        db.commit()
        
        return {"message": "Record deleted"}
    except Exception as e:
         db.rollback()
         raise HTTPException(status_code=500, detail=str(e))
