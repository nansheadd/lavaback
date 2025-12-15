from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
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
    
    # Page content (JSON)
    widgets_json = Column(Text, default="[]")  # Array of widget definitions
    theme_json = Column(Text, nullable=True)   # Theme settings
    
    # Metadata
    is_published = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
