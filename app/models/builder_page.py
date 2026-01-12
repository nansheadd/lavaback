from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from ..database import Base


class BuilderPage(Base):
    """
    Represents a page created with the App Builder.
    """
    __tablename__ = "builder_pages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    slug = Column(String, unique=True, index=True)  # URL-friendly name
    description = Column(Text, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True) # Link to App/Project
    
    # Page content (JSON)
    widgets_json = Column(Text, default="[]")  # Array of widget definitions
    theme_json = Column(Text, nullable=True)   # Theme settings
    
    # Metadata
    is_published = Column(Boolean, default=False)
    
    # Access Control
    access_level = Column(String, default="public") # public, authenticated, role_based
    allowed_roles = Column(Text, default="[]")      # JSON array of role names if access_level is role_based

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
