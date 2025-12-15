from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class CommentBase(BaseModel):
    content: str
    project_id: int

class CommentCreate(CommentBase):
    pass

class Comment(CommentBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class ProjectBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = "BACKLOG"
    version: Optional[str] = "0.0.1"
    summary: Optional[str] = None
    checklist: Optional[str] = "[]"

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    status: Optional[str] = None
    version: Optional[str] = None
    summary: Optional[str] = None
    checklist: Optional[str] = None

class Project(ProjectBase):
    id: int
    created_at: datetime
    comments: List[Comment] = []

    class Config:
        from_attributes = True

class ActivityLogBase(BaseModel):
    action: str
    project_id: Optional[int] = None

class ActivityLog(ActivityLogBase):
    id: int
    user_id: Optional[int] = None
    timestamp: datetime
    username: Optional[str] = None # Helper

    class Config:
        from_attributes = True

    class Config:
        from_attributes = True

# Review Schemas
# Review Schemas
class ReviewCommentBase(BaseModel):
    content: str
    author_name: str = "User"

class ReviewCommentCreate(ReviewCommentBase):
    pass

class ReviewCommentUpdate(BaseModel):
    content: str | None = None
    likes: int | None = None
    dislikes: int | None = None

class ReviewComment(ReviewCommentBase):
    id: int
    thread_id: int
    created_at: datetime
    edited_at: datetime | None = None
    likes: int = 0
    dislikes: int = 0
    author_id: int | None = None

    class Config:
        from_attributes = True

class ReviewThreadBase(BaseModel):
    tool_id: str | None = None
    selection_json: str | None = None
    coordinates: str | None = None
    context_type: str = "text"
    category: str = "comment"
    status: str = "open"

class ReviewThreadCreate(ReviewThreadBase):
    pass

class ReviewThread(ReviewThreadBase):
    id: int
    project_id: int
    created_at: datetime
    comments: list[ReviewComment] = []

    class Config:
        from_attributes = True

# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None

class UserBase(BaseModel):
    username: str
    email: str | None = None

class UserCreate(UserBase):
    password: str

class RoleBase(BaseModel):
    name: str

class Role(RoleBase):
    id: int
    permissions: str | None = None
    class Config:
        from_attributes = True

class User(UserBase):
    id: int
    is_active: bool
    role: Role | None = None
    class Config:
        from_attributes = True
