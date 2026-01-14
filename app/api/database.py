from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text, select, insert, update, delete
from sqlalchemy.exc import IntegrityError
from ..database import get_db, Base
from ..models import base_models as models # Ensure models are loaded
from ..auth import get_current_user
from ..models.base_models import User

router = APIRouter()

def check_admin_access(user: User = Depends(get_current_user)):
    if not user.is_active:
         raise HTTPException(status_code=400, detail="Inactive user")
    if not user.role or user.role.name not in ["admin", "engineer"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    return user

@router.get("/tables", response_model=Dict[str, Any])
def get_tables(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin_access)
):
    """
    List all tables and their complete schema (columns, types, foreign keys).
    """
    inspector = inspect(db.bind)
    tables_info = {}
    
    table_names = inspector.get_table_names()
    
    for table_name in table_names:
        columns = []
        for col in inspector.get_columns(table_name):
            # Parse column info to be JSON serializable
            col_info = {
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col["nullable"],
                "default": str(col["default"]) if col["default"] else None,
                "primary_key": col.get("primary_key", 0) > 0
            }
            columns.append(col_info)
            
        fks = inspector.get_foreign_keys(table_name)
        foreign_keys = []
        for fk in fks:
            foreign_keys.append({
                "constrained_columns": fk["constrained_columns"],
                "referred_table": fk["referred_table"],
                "referred_columns": fk["referred_columns"]
            })
            
        tables_info[table_name] = {
            "columns": columns,
            "foreign_keys": foreign_keys
        }
        
    return tables_info

@router.get("/tables/{table_name}")
def get_table_data(
    table_name: str,
    page: int = 1,
    limit: int = 50,
    sort_by: Optional[str] = None,
    order: str = "asc",
    search_col: Optional[str] = None,
    search_val: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin_access)
):
    """
    Get paginated data from a specific table.
    """
    if table_name not in Base.metadata.tables:
        # Fallback to introspection if not in metadata but exists (unlikely given app structure)
        inspector = inspect(db.bind)
        if table_name not in inspector.get_table_names():
            raise HTTPException(status_code=404, detail=f"Table {table_name} not found")
        
        # If strictly using SQLAlchemy Core for non-mapped tables
        tbl = Base.metadata.tables.get(table_name)
        if tbl is None:
             # Reflect table if not in metadata
            from sqlalchemy import Table, MetaData
            meta = MetaData()
            tbl = Table(table_name, meta, autoload_with=db.bind)
    else:
        tbl = Base.metadata.tables[table_name]

    query = select(tbl)

    # Sorting
    if sort_by:
        col = tbl.c.get(sort_by)
        if col is not None:
            if order == "desc":
                query = query.order_by(col.desc())
            else:
                query = query.order_by(col.asc())
    
    # Simple Search (Exact or ILIKE for strings)
    if search_col and search_val:
        col = tbl.c.get(search_col)
        if col is not None:
            # Check if column is string-like
            if str(col.type).startswith("VARCHAR") or str(col.type).startswith("TEXT") or str(col.type).startswith("STRING"):
                 query = query.where(col.ilike(f"%{search_val}%"))
            else:
                # Try exact match for others, handle errors gracefully
                try:
                    query = query.where(col == search_val)
                except:
                    pass

    # Pagination
    offset = (page - 1) * limit
    
    # Get total count first
    count_query = select(func.count()).select_from(query.alias()) # Wrap in subquery for safety with limits/order
    # Simplified count for generic table
    # Actually, counting with where clauses:
    # We need to construct a count query based on the same where criteria
    count_stmt = select(func.count()).select_from(tbl)
    if search_col and search_val:
         col = tbl.c.get(search_col)
         if col is not None and (str(col.type).startswith("VARCHAR") or str(col.type).startswith("TEXT")):
             count_stmt = count_stmt.where(col.ilike(f"%{search_val}%"))
         elif col is not None:
             try:
                 count_stmt = count_stmt.where(col == search_val)
             except:
                 pass
                 
    total = db.scalar(count_stmt)
    
    # Execute main query
    query = query.offset(offset).limit(limit)
    result = db.execute(query)
    
    # Convert rows to dicts
    rows = []
    # Result object yields Row objects which are somewhat dict-like but need explicit conversion
    # keys are accessible via result.keys()
    keys = result.keys()
    for row in result:
        row_dict = {}
        for idx, key in enumerate(keys):
            val = row[idx]
            # Handle non-serializable types like datetime
            if hasattr(val, 'isoformat'):
                val = val.isoformat()
            row_dict[key] = val
        rows.append(row_dict)

    return {
        "data": rows,
        "total": total,
        "page": page,
        "limit": limit
    }

from sqlalchemy import func

@router.post("/tables/{table_name}")
def create_record(
    table_name: str,
    record: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin_access)
):
    if table_name not in Base.metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
        
    tbl = Base.metadata.tables[table_name]
    
    try:
        stmt = insert(tbl).values(**record)
        result = db.execute(stmt)
        db.commit()
        
        # Try to return the inserted ID if possible
        if result.inserted_primary_key:
             return {"success": True, "id": result.inserted_primary_key[0]}
        return {"success": True}
        
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e.orig))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/tables/{table_name}/{record_id}")
def update_record(
    table_name: str,
    record_id: str,
    updates: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin_access)
):
    if table_name not in Base.metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    tbl = Base.metadata.tables[table_name]
    
    # Find primary key
    pk = list(tbl.primary_key.columns)[0]
    
    try:
        stmt = update(tbl).where(pk == record_id).values(**updates)
        result = db.execute(stmt)
        db.commit()
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Record not found")
            
        return {"success": True}
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e.orig))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/tables/{table_name}/{record_id}")
def delete_record(
    table_name: str,
    record_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin_access)
):
    if table_name not in Base.metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    tbl = Base.metadata.tables[table_name]
    pk = list(tbl.primary_key.columns)[0]
    
    try:
        stmt = delete(tbl).where(pk == record_id)
        result = db.execute(stmt)
        db.commit()
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Record not found")
            
        return {"success": True}
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete record usually due to foreign key constraints.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
