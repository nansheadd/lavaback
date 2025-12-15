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
import uvicorn
import shutil
import os
import uuid

# Create all tables (Base now includes workflow tables)
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="DuoText Platform API")

# Register routers
app.include_router(workflows_router, prefix="/api")
app.include_router(pages_router, prefix="/api")
app.include_router(activity_router, prefix="/api")

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

# --- Auth Logic (Must be defined before endpoints using it) ---
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from app.auth import verify_password, create_access_token, get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES
from datetime import timedelta
from jose import JWTError, jwt
from app.auth import SECRET_KEY, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    return user

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

@app.get("/users/me", response_model=schemas.User)
async def read_users_me(current_user: schemas.User = Depends(get_current_user)):
    return current_user

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
        
        # Seed Roles
        roles = ["admin", "editor", "subscriber", "user", "journalist"]
        for role_name in roles:
            role = db.query(models.Role).filter(models.Role.name == role_name).first()
            if not role:
                db.add(models.Role(name=role_name))
        db.commit()

        # Seed Admin User
        admin_user = db.query(models.User).filter(models.User.username == "admin").first()
        if not admin_user:
            hashed_pw = get_password_hash("password")
            admin_role = db.query(models.Role).filter(models.Role.name == "admin").first()
            db.add(models.User(username="admin", email="admin@example.com", hashed_password=hashed_pw, role_id=admin_role.id))
            db.commit()
            print("Seeded 'admin' user.")

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
