from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from app.services.docx_parser import parse_docx
from sqlalchemy.sql import func
from app import models, schemas, database
from app.api.workflows import router as workflows_router
from app.api.pages import router as pages_router
from app.api.activity import router as activity_router
from app.api.articles import router as articles_router
from app.api.shop import router as shop_router
from app.api.messaging import router as messaging_router
from app.api.upload import router as upload_router
from app.api.users import router as users_router
import uvicorn
import shutil
import os
import uuid

# Create all tables (Base now includes workflow tables)
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="DuoText Platform API")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Register routers
app.include_router(workflows_router, prefix="/api")
app.include_router(pages_router, prefix="/api")
app.include_router(activity_router, prefix="/api")
app.include_router(articles_router, prefix="/api/articles", tags=["articles"])
app.include_router(shop_router, prefix="/api", tags=["shop"])
app.include_router(messaging_router, prefix="/api", tags=["messaging"])
app.include_router(upload_router, prefix="/api", tags=["upload"])
app.include_router(users_router, prefix="/api/users", tags=["users"])

# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


# CORS configuration - supports environment variable for production
import os as os_module

cors_origins_env = os_module.getenv("CORS_ORIGINS", "")
origins = [
    "http://localhost:5173",  # Vite default
    "http://localhost:5174",  # Vite fallback
    "http://localhost:3000",
]
# Add production origins from environment
if cors_origins_env:
    origins.extend([origin.strip() for origin in cors_origins_env.split(",")])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure upload directory exists
os.makedirs("app/uploads", exist_ok=True)

# Mount static files
app.mount("/uploads", StaticFiles(directory="app/uploads"), name="uploads")

@app.get("/")
def read_root():
    return {"message": "DuoText Platform API is running"}

# --- Auth Logic ---
from fastapi.security import OAuth2PasswordRequestForm
from app.auth import verify_password, create_access_token, get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user
from datetime import datetime, timedelta

@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

class UserCreate(schemas.BaseModel):
    username: str
    email: str
    password: str

@app.post("/api/register", response_model=schemas.User)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter((models.User.username == user.username) | (models.User.email == user.email)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username or Email already registered")
    
    user_role = db.query(models.Role).filter(models.Role.name == "user").first()
    if not user_role:
        raise HTTPException(status_code=500, detail="Default role configuration missing")

    hashed_pw = get_password_hash(user.password)
    new_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_pw,
        role_id=user_role.id,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.get("/users/me", response_model=schemas.User)
async def read_users_me(current_user: schemas.User = Depends(get_current_user)):
    return current_user

# --- User Management ---
class UserAdminCreate(schemas.BaseModel):
    username: str
    email: str
    password: str
    role_name: str

@app.post("/api/users", response_model=schemas.User)
def create_user_admin(user: UserAdminCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role.name not in ["admin", "engineer"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db_user = db.query(models.User).filter((models.User.username == user.username) | (models.User.email == user.email)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username or Email already registered")
    
    role = db.query(models.Role).filter(models.Role.name == user.role_name).first()
    if not role:
        raise HTTPException(status_code=400, detail="Role not found")

    hashed_pw = get_password_hash(user.password)
    new_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_pw,
        role_id=role.id,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.delete("/api/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role.name not in ["admin", "engineer"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot delete yourself")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}

@app.get("/api/users", response_model=list[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Simple admin check
    if current_user.role.name not in ["admin", "engineer"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users

class UserRoleUpdate(schemas.BaseModel):
    role_name: str

@app.put("/api/users/{user_id}/role")
def update_user_role(
    user_id: int, 
    role_update: UserRoleUpdate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role.name not in ["admin", "engineer"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    role = db.query(models.Role).filter(models.Role.name == role_update.role_name).first()
    if not role:
        raise HTTPException(status_code=400, detail="Role not found")
    
    user.role_id = role.id
    db.commit()
    return {"message": f"User role updated to {role.name}"}

# --- Role Management API ---
class RoleUpdate(schemas.BaseModel):
    permissions: str

class RoleOut(schemas.BaseModel):
    id: int
    name: str
    permissions: str | None

    class Config:
        from_attributes = True

@app.get("/api/roles", response_model=list[RoleOut])
def read_roles(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role.name not in ["admin", "engineer"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    return db.query(models.Role).all()

@app.put("/api/roles/{role_id}")
def update_role_permissions(
    role_id: int,
    role_update: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role.name not in ["admin", "engineer"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    role = db.query(models.Role).filter(models.Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    role.permissions = role_update.permissions
    db.commit()
    return {"message": f"Role {role.name} updated"}


# --- Team Chat API ---
class ChatMessageCreate(schemas.BaseModel):
    content: str

class UserChatOut(schemas.BaseModel):
    id: int
    username: str
    role_name: str | None = None

class ChatMessageOut(schemas.BaseModel):
    id: int
    content: str
    timestamp: datetime
    user: UserChatOut

    class Config:
        from_attributes = True

@app.get("/api/chat", response_model=list[ChatMessageOut])
def get_chat_messages(limit: int = 50, db: Session = Depends(get_db)):
    msgs = db.query(models.ChatMessage).order_by(models.ChatMessage.timestamp.desc()).limit(limit).all()
    # Manual mapping to avoid circular deps or complex nested schemas
    result = []
    for m in msgs:
        role_name = m.user.role.name if m.user and m.user.role else "user"
        result.append({
            "id": m.id,
            "content": m.content,
            "timestamp": m.timestamp,
            "user": {
                "id": m.user.id if m.user else 0,
                "username": m.user.username if m.user else "Unknown",
                "role_name": role_name
            }
        })
    return result # Returns newest first

@app.post("/api/chat", response_model=ChatMessageOut)
def post_chat_message(msg: ChatMessageCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    new_msg = models.ChatMessage(content=msg.content, user_id=current_user.id)
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)
    
    role_name = current_user.role.name if current_user.role else "user"
    return {
        "id": new_msg.id,
        "content": new_msg.content,
        "timestamp": new_msg.timestamp,
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "role_name": role_name
        }
    }

# --- Project & Comment Endpoints ---

@app.get("/api/projects", response_model=list[schemas.Project])
def read_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    projects = db.query(models.Project).offset(skip).limit(limit).all()
    return projects

@app.post("/api/projects", response_model=schemas.Project)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    db_project = models.Project(**project.dict())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

@app.get("/api/projects/{project_id}", response_model=schemas.Project)
def read_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@app.put("/api/projects/{project_id}", response_model=schemas.Project)
def update_project(
    project_id: int, 
    project_update: schemas.ProjectUpdate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Track activity
    if project_update.version and project_update.version != project.version:
        log = models.ActivityLog(
            user_id=current_user.id,
            project_id=project_id,
            action=f"Updated version to {project_update.version}"
        )
        db.add(log)
    
    if project_update.status and project_update.status != project.status:
        log = models.ActivityLog(
            user_id=current_user.id,
            project_id=project_id,
            action=f"Changed status to {project_update.status}"
        )
        db.add(log)

    # Apply updates
    update_data = project_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)
    
    db.commit()
    db.refresh(project)
    return project

@app.get("/api/activity-logs", response_model=list[schemas.ActivityLog])
def read_activity_logs(limit: int = 10, db: Session = Depends(get_db)):
    logs = db.query(models.ActivityLog).order_by(models.ActivityLog.timestamp.desc()).limit(limit).all()
    # Populate username helper manually or via relationship
    for log in logs:
        if log.user:
            log.username = log.user.username
    return logs

@app.post("/api/projects/{project_id}/comments", response_model=schemas.Comment)
def create_comment(project_id: int, comment: schemas.CommentCreate, db: Session = Depends(get_db)):
    db_comment = models.Comment(**comment.dict()) # comment.project_id should match or we override
    # Ensure project_id is correct
    db_comment.project_id = project_id
    
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment

@app.get("/api/projects/{project_id}/comments", response_model=list[schemas.Comment])
def read_comments(project_id: int, db: Session = Depends(get_db)):
    comments = db.query(models.Comment).filter(models.Comment.project_id == project_id).all()
    return comments

# Review Endpoints
@app.post("/api/projects/{project_id}/reviews", response_model=schemas.ReviewThread)
def create_review_thread(project_id: int, review: schemas.ReviewThreadCreate, db: Session = Depends(get_db)):
    db_review = models.ReviewThread(**review.model_dump(), project_id=project_id)
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review

@app.get("/api/projects/{project_id}/reviews", response_model=list[schemas.ReviewThread])
def get_review_threads(project_id: int, db: Session = Depends(get_db)):
    return db.query(models.ReviewThread).filter(models.ReviewThread.project_id == project_id).all()

@app.post("/api/reviews/{thread_id}/comments", response_model=schemas.ReviewComment)
def create_review_comment(
    thread_id: int, 
    comment: schemas.ReviewCommentCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_comment = models.ReviewComment(
        **comment.model_dump(exclude={"author_name"}), 
        thread_id=thread_id,
        author_id=current_user.id,
        author_name=current_user.username
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment

@app.put("/api/reviews/comments/{comment_id}", response_model=schemas.ReviewComment)
def update_review_comment(
    comment_id: int, 
    comment_update: schemas.ReviewCommentUpdate, 
    db: Session = Depends(get_db),
    # current_user: models.User = Depends(get_current_user) # Optional: check ownership
):
    db_comment = db.query(models.ReviewComment).filter(models.ReviewComment.id == comment_id).first()
    if not db_comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    if comment_update.content is not None:
        db_comment.content = comment_update.content
        db_comment.edited_at = func.now()
    
    if comment_update.likes is not None: # Simple increment logic for demo
        db_comment.likes = comment_update.likes
    
    if comment_update.dislikes is not None:
        db_comment.dislikes = comment_update.dislikes

    db.commit()
    db.refresh(db_comment)
    return db_comment

@app.get("/api/reviews/{thread_id}/comments", response_model=list[schemas.ReviewComment])
def get_review_comments(thread_id: int, db: Session = Depends(get_db)):
    return db.query(models.ReviewComment).filter(models.ReviewComment.thread_id == thread_id).all()

@app.put("/api/reviews/{thread_id}/status")
def update_review_status(thread_id: int, status: str, db: Session = Depends(get_db)):
    thread = db.query(models.ReviewThread).filter(models.ReviewThread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Review thread not found")
    thread.status = status
    db.commit()
    return {"message": "Status updated"}


# Seeding Logic Update
@app.on_event("startup")
async def seed_data():
    db = database.SessionLocal()
    try:
        # Seed Project
        project = db.query(models.Project).filter(models.Project.title == "Text Editor").first()
        if not project:
            editor_tool = models.Project(
                title="Text Editor",
                description="A rich text editor with live preview, word import, and image support.",
                status=models.ProjectStatus.IN_PROGRESS.value
            )
            db.add(editor_tool)
            db.commit()
            print("Seeded 'Text Editor' project.")
        
        # Seed Roles & Permissions
        roles_data = [
            {"name": "admin", "permissions": "*"},
            {"name": "engineer", "permissions": "*"},
            {"name": "editor", "permissions": "view:content,edit:content,publish:content"},
            {"name": "author", "permissions": "view:own_content,edit:own_content"},
            {"name": "user", "permissions": "view:public"}
        ]
        
        for r_data in roles_data:
            role = db.query(models.Role).filter(models.Role.name == r_data["name"]).first()
            if not role:
                db.add(models.Role(name=r_data["name"], permissions=r_data["permissions"]))
            else:
                # Update permissions if changed
                if role.permissions != r_data["permissions"]:
                    role.permissions = r_data["permissions"]
        
        db.commit()

        # Seed Admin User
        admin_user = db.query(models.User).filter(models.User.username == "admin").first()
        if not admin_user:
            hashed_pw = get_password_hash("admin") # User requested admin/admin
            admin_role = db.query(models.Role).filter(models.Role.name == "admin").first()
            db.add(models.User(username="admin", email="admin@lava.com", hashed_password=hashed_pw, role_id=admin_role.id))
            db.commit()
            print("Seeded 'admin' user.")
        else:
            # Update password if needed (for dev convenience)
            # hashed_pw = get_password_hash("admin")
            # admin_user.hashed_password = hashed_pw
            pass

    finally:
        db.close()

@app.post("/api/upload-image")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")
    
    # Generate unique filename
    extension = file.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{extension}"
    file_path = f"app/uploads/{filename}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"url": f"http://localhost:8000/uploads/{filename}"}

@app.post("/api/import-docx")
async def import_docx(file: UploadFile = File(...)):
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .docx file.")
    
    try:
        content_html = await parse_docx(file)
        return {"html": content_html}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
