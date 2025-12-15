from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from ..database import Base

class ProjectStatus(str, enum.Enum):
    BACKLOG = "BACKLOG"
    IN_PROGRESS = "IN_PROGRESS"
    VALIDATED = "VALIDATED"

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text, nullable=True)
    status = Column(String, default=ProjectStatus.BACKLOG.value) # Storing Enum as String for simplicity in SQLite
    version = Column(String, default="0.0.1")
    summary = Column(Text, nullable=True)
    checklist = Column(Text, default="[]") # JSON string of completed checks
    created_at = Column(DateTime, default=datetime.utcnow)

    comments = relationship("Comment", back_populates="project", cascade="all, delete-orphan")

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    page_id = Column(Integer, ForeignKey("builder_pages.id"), nullable=True) # New FK
    
    action = Column(String) # e.g., "Updated page", "Created project"
    details = Column(Text, nullable=True) # JSON or text details
    resource_type = Column(String, default="system") # project, page, system, auth
    
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    project = relationship("Project")
    page = relationship("BuilderPage") # Relationship to BuilderPage

class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    project_id = Column(Integer, ForeignKey("projects.id"))

    project = relationship("Project", back_populates="comments")

from sqlalchemy.sql import func

class ReviewThread(Base):
    __tablename__ = "review_threads"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    tool_id = Column(String, nullable=True) 
    selection_json = Column(String, nullable=True) 
    coordinates = Column(String, nullable=True) # JSON {x, y}
    context_type = Column(String, default="text") # "text" or "point"
    category = Column(String, default="comment") # "bug", "design", "question", "comment"
    status = Column(String, default="open") 
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    comments = relationship("ReviewComment", back_populates="thread", cascade="all, delete-orphan")

class ReviewComment(Base):
    __tablename__ = "review_comments"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("review_threads.id"))
    content = Column(Text)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Link to User
    author_name = Column(String, default="User") # Fallback/Cache
    edited_at = Column(DateTime(timezone=True), nullable=True)
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    thread = relationship("ReviewThread", back_populates="comments")
    author = relationship("User") # Relationship to User

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    permissions = Column(Text, nullable=True) # JSON or comma-separated string

    users = relationship("User", back_populates="role")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    role_id = Column(Integer, ForeignKey("roles.id"))

    role = relationship("Role", back_populates="users")
