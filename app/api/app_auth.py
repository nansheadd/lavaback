
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from pydantic import BaseModel, EmailStr
from app import database, models
from app.auth import get_password_hash, verify_password, create_access_token
from app.core.project_db import get_project_table_name
from datetime import timedelta

router = APIRouter()

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

class AppUserLogin(BaseModel):
    username: str
    password: str

class AppUserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class AppToken(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str

@router.post("/apps/{app_id}/auth/register", response_model=AppToken)
def app_register(app_id: int, user: AppUserCreate, db: Session = Depends(get_db)):
    # 1. Verify User Table Exists
    table_name = get_project_table_name(app_id, "users", db)
    inspector = inspect(db.get_bind())
    if not inspector.has_table(table_name):
         raise HTTPException(status_code=404, detail=f"User table for App {app_id} does not exist. Please enable authentication in Builder.")

    # 2. Check if user exists (SQL Injection safe-ish via params if using SQLAlchemy text with bindparams, 
    # but here we construct generic SQL. Input validation is key.)
    # We use parameterized queries for safety.
    
    query = text(f"SELECT id FROM {table_name} WHERE username = :username OR email = :email")
    existing = db.execute(query, {"username": user.username, "email": user.email}).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail="Username or Email already registered in this app")

    # 3. Create User
    hashed_pw = get_password_hash(user.password)
    
    insert_stmt = text(f"""
        INSERT INTO {table_name} (username, email, hashed_password, created_at)
        VALUES (:username, :email, :password, CURRENT_TIMESTAMP)
        RETURNING id, username
    """)
    
    try:
        result = db.execute(insert_stmt, {
            "username": user.username, 
            "email": user.email, 
            "password": hashed_pw
        }).fetchone()
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
        
    # 4. Generate Token (Scoped to App)
    access_token = create_access_token(
        data={"sub": result.username, "app_id": app_id, "app_user_id": result.id}
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user_id": result.id,
        "username": result.username
    }

@router.post("/apps/{app_id}/auth/login", response_model=AppToken)
def app_login(app_id: int, user: AppUserLogin, db: Session = Depends(get_db)):
    # 1. Check Table
    table_name = get_project_table_name(app_id, "users", db)
    inspector = inspect(db.get_bind())
    if not inspector.has_table(table_name):
         raise HTTPException(status_code=404, detail="App Auth not configured")
         
    # 2. Get User
    query = text(f"SELECT id, username, hashed_password FROM {table_name} WHERE username = :username")
    result = db.execute(query, {"username": user.username}).fetchone()
    
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    # 3. Verify Password
    # result is a Row object/tuple. 0=id, 1=username, 2=hashed_password
    stored_hash = result[2]
    if not verify_password(user.password, stored_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    # 4. Generate Token
    access_token = create_access_token(
        data={"sub": result.username, "app_id": app_id, "app_user_id": result.id}
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user_id": result.id,
        "username": result.username
    }
