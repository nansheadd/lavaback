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
    status = Column(String, default="offline") # online, away, dnd, offline

    role = relationship("Role", back_populates="users")
    messages = relationship("ChatMessage", back_populates="user")
    orders = relationship("Order", back_populates="user")
    subscription = relationship("UserSubscription", back_populates="user", uselist=False)

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey("users.id"))
    
    user = relationship("User", back_populates="messages")

# ========== E-COMMERCE MODELS ==========

class ProductCategory(Base):
    __tablename__ = "product_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    slug = Column(String, unique=True, index=True)
    description = Column(Text, nullable=True)
    icon = Column(String, nullable=True)  # Lucide icon name
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    products = relationship("Product", back_populates="category")

class ProductType(str, enum.Enum):
    PHYSICAL = "physical"
    DIGITAL = "digital"

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    slug = Column(String, unique=True, index=True)
    description = Column(Text, nullable=True)
    price = Column(Integer)  # Price in cents (e.g., 499 = 4.99€)
    currency = Column(String, default="EUR")
    product_type = Column(String, default=ProductType.PHYSICAL.value)
    category_id = Column(Integer, ForeignKey("product_categories.id"), nullable=True)
    
    image_url = Column(String, nullable=True)
    stock = Column(Integer, nullable=True)  # NULL for digital products
    
    stripe_product_id = Column(String, nullable=True)
    stripe_price_id = Column(String, nullable=True)
    
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    category = relationship("ProductCategory", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")

class SubscriptionInterval(str, enum.Enum):
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"

class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    price = Column(Integer)  # Price in cents
    currency = Column(String, default="EUR")
    interval = Column(String, default=SubscriptionInterval.MONTH.value)
    
    features = Column(Text, nullable=True)  # JSON array of features
    
    stripe_product_id = Column(String, nullable=True)
    stripe_price_id = Column(String, nullable=True)
    
    is_active = Column(Boolean, default=True)
    is_popular = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    subscriptions = relationship("UserSubscription", back_populates="plan")

class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    status = Column(String, default=OrderStatus.PENDING.value)
    total_amount = Column(Integer)  # Total in cents
    currency = Column(String, default="EUR")
    
    stripe_session_id = Column(String, nullable=True)
    stripe_payment_intent_id = Column(String, nullable=True)
    
    shipping_address = Column(Text, nullable=True)  # JSON
    billing_address = Column(Text, nullable=True)  # JSON
    
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    
    quantity = Column(Integer, default=1)
    unit_price = Column(Integer)  # Price at time of purchase (cents)
    
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    PAUSED = "paused"

class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"))
    
    stripe_subscription_id = Column(String, nullable=True)
    status = Column(String, default=SubscriptionStatus.ACTIVE.value)
    
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="subscription")
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")

class AppSettings(Base):
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    value = Column(Text, nullable=True)
    is_secret = Column(Boolean, default=False)  # Hide value in UI
    description = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ========== MESSAGING SYSTEM (Slack-like) ==========

class ChannelType(str, enum.Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    DIRECT = "direct"  # DM between 2 users

class ChatChannel(Base):
    __tablename__ = "chat_channels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    slug = Column(String, unique=True, index=True)
    description = Column(Text, nullable=True)
    channel_type = Column(String, default=ChannelType.PUBLIC.value)
    
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_archived = Column(Boolean, default=False)

    creator = relationship("User", foreign_keys=[created_by])
    members = relationship("ChannelMember", back_populates="channel", cascade="all, delete-orphan")
    messages = relationship("ChannelMessage", back_populates="channel", cascade="all, delete-orphan")

class MemberRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"

class ChannelMember(Base):
    __tablename__ = "channel_members"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("chat_channels.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    
    role = Column(String, default=MemberRole.MEMBER.value)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    last_read_at = Column(DateTime(timezone=True), nullable=True)
    
    # Notification preferences
    notifications_enabled = Column(Boolean, default=True)
    sound_enabled = Column(Boolean, default=True)

    channel = relationship("ChatChannel", back_populates="members")
    user = relationship("User")

class ChannelMessage(Base):
    __tablename__ = "channel_messages"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("chat_channels.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    edited_at = Column(DateTime(timezone=True), nullable=True)
    
    is_system_message = Column(Boolean, default=False)  # "X joined the channel"
    reply_to_id = Column(Integer, ForeignKey("channel_messages.id"), nullable=True)  # Thread support

    channel = relationship("ChatChannel", back_populates="messages")
    user = relationship("User")
    reply_to = relationship("ChannelMessage", remote_side=[id])
    
    reactions = relationship("MessageReaction", back_populates="message", cascade="all, delete-orphan")
    attachments = relationship("MessageAttachment", back_populates="message", cascade="all, delete-orphan")

class MessageReaction(Base):
    __tablename__ = "message_reactions"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("channel_messages.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    emoji = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    message = relationship("ChannelMessage", back_populates="reactions")
    user = relationship("User")

class MessageAttachment(Base):
    __tablename__ = "message_attachments"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("channel_messages.id"))
    
    file_url = Column(String, nullable=False)
    file_type = Column(String, nullable=False) # image/png, application/pdf etc
    file_name = Column(String, nullable=False)
    file_size = Column(Integer, nullable=True) # in bytes
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    message = relationship("ChannelMessage", back_populates="attachments")


