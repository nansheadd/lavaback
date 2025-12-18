from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from ..database import Base

class ArticleStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"

class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    slug = Column(String, unique=True, index=True)
    content = Column(Text, nullable=True) # JSON or HTML content from editor
    excerpt = Column(Text, nullable=True) # Short summary for lists
    cover_image = Column(String, nullable=True)
    
    status = Column(Enum(ArticleStatus), default=ArticleStatus.DRAFT)
    category = Column(String, index=True, nullable=True)
    tags = Column(String, nullable=True) # Comma separated
    
    author_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)
    
    # Relationships
    author = relationship("User", foreign_keys=[author_id])
    reviews = relationship("ArticleReview", back_populates="article", cascade="all, delete-orphan")

class ArticleReview(Base):
    __tablename__ = "article_reviews"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"))
    reviewer_id = Column(Integer, ForeignKey("users.id"))
    
    status = Column(String) # APPROVED, CHANGES_REQUESTED
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    article = relationship("Article", back_populates="reviews")
    reviewer = relationship("User", foreign_keys=[reviewer_id])
