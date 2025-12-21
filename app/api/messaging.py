from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app import models, database
from app.auth import get_current_user

router = APIRouter()

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ========== Pydantic Schemas ==========

class ChannelCreate(BaseModel):
    name: str
    description: Optional[str] = None
    channel_type: str = "public"  # public, private
    member_ids: Optional[List[int]] = []  # Initial members

class ChannelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_archived: Optional[bool] = None

class ChannelOut(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str]
    channel_type: str
    created_by: Optional[int]
    created_at: datetime
    is_archived: bool
    unread_count: int = 0
    last_message: Optional[str] = None
    
    class Config:
        from_attributes = True

class MemberOut(BaseModel):
    id: int
    user_id: int
    username: str
    role: str
    status: Optional[str] = "offline"
    joined_at: datetime
    
    class Config:
        from_attributes = True

class ReactionOut(BaseModel):
    id: int
    user_id: int
    emoji: str
    
    class Config:
        from_attributes = True

class AttachmentOut(BaseModel):
    id: int
    file_url: str
    file_type: str
    file_name: str
    file_size: Optional[int]
    
    class Config:
        from_attributes = True

class MessageCreate(BaseModel):
    content: str
    reply_to_id: Optional[int] = None
    attachment_url: Optional[str] = None
    attachment_type: Optional[str] = None
    attachment_name: Optional[str] = None
    attachment_size: Optional[int] = None

class MessageOut(BaseModel):
    id: int
    channel_id: int
    user_id: int
    username: str
    content: str
    timestamp: datetime
    edited_at: Optional[datetime]
    is_system_message: bool
    reply_to_id: Optional[int]
    
    reactions: List[ReactionOut] = []
    attachments: List[AttachmentOut] = []
    
    class Config:
        from_attributes = True

class UserStatusUpdate(BaseModel):
    status: str # online, away, dnd, offline

class NotificationPrefs(BaseModel):
    notifications_enabled: bool = True
    sound_enabled: bool = True

# ========== Helper Functions ==========

def check_can_create_channel(user: models.User, db: Session):
    """Check if user has permission to create channels"""
    if user.role.name in ["admin", "engineer"]:
        return True
    # Check if user has 'create_channels' permission
    if user.role.permissions and "create_channels" in user.role.permissions:
        return True
    raise HTTPException(status_code=403, detail="You don't have permission to create channels")

def get_user_membership(channel_id: int, user_id: int, db: Session):
    return db.query(models.ChannelMember).filter(
        models.ChannelMember.channel_id == channel_id,
        models.ChannelMember.user_id == user_id
    ).first()

def get_or_create_dm_channel(user1_id: int, user2_id: int, db: Session):
    """Get or create a DM channel between two users"""
    # Find existing DM channel
    existing = db.query(models.ChatChannel).filter(
        models.ChatChannel.channel_type == "direct"
    ).join(models.ChannelMember).filter(
        models.ChannelMember.user_id.in_([user1_id, user2_id])
    ).all()
    
    for channel in existing:
        member_ids = [m.user_id for m in channel.members]
        if set(member_ids) == {user1_id, user2_id}:
            return channel
    
    # Create new DM channel
    user1 = db.query(models.User).get(user1_id)
    user2 = db.query(models.User).get(user2_id)
    
    channel = models.ChatChannel(
        name=f"DM: {user1.username} & {user2.username}",
        slug=f"dm-{min(user1_id, user2_id)}-{max(user1_id, user2_id)}",
        channel_type="direct",
        created_by=user1_id
    )
    db.add(channel)
    db.flush()
    
    # Add both users as members
    db.add(models.ChannelMember(channel_id=channel.id, user_id=user1_id, role="owner"))
    db.add(models.ChannelMember(channel_id=channel.id, user_id=user2_id, role="member"))
    db.commit()
    db.refresh(channel)
    
    return channel

# ========== Channel Endpoints ==========

@router.get("/channels", response_model=List[ChannelOut])
def list_my_channels(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List all channels: public channels + channels where user is a member"""
    # Get user's memberships
    user_memberships = {m.channel_id: m for m in db.query(models.ChannelMember).filter(
        models.ChannelMember.user_id == current_user.id
    ).all()}
    
    # Get all non-archived channels that are either:
    # 1. Public (visible to everyone)
    # 2. The user is a member of (private or direct)
    member_channel_ids = list(user_memberships.keys())
    
    channels = db.query(models.ChatChannel).filter(
        models.ChatChannel.is_archived == False,
        or_(
            models.ChatChannel.channel_type == "public",
            models.ChatChannel.id.in_(member_channel_ids) if member_channel_ids else False
        )
    ).all()
    
    result = []
    for channel in channels:
        membership = user_memberships.get(channel.id)
        
        # Count unread messages
        unread = 0
        last_msg = None
        
        if membership:
            if membership.last_read_at:
                unread = db.query(models.ChannelMessage).filter(
                    models.ChannelMessage.channel_id == channel.id,
                    models.ChannelMessage.timestamp > membership.last_read_at,
                    models.ChannelMessage.user_id != current_user.id
                ).count()
            else:
                unread = db.query(models.ChannelMessage).filter(
                    models.ChannelMessage.channel_id == channel.id,
                    models.ChannelMessage.user_id != current_user.id
                ).count()
        
        # Get last message
        last = db.query(models.ChannelMessage).filter(
            models.ChannelMessage.channel_id == channel.id
        ).order_by(models.ChannelMessage.timestamp.desc()).first()
        
        if last:
            last_msg = last.content[:50] + "..." if len(last.content) > 50 else last.content
        
        result.append({
            **channel.__dict__,
            "unread_count": unread,
            "last_message": last_msg
        })
    
    return result

@router.post("/channels", response_model=ChannelOut)
def create_channel(
    channel: ChannelCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    check_can_create_channel(current_user, db)
    
    slug = channel.name.lower().replace(" ", "-").replace("'", "")
    
    # Check slug uniqueness
    existing = db.query(models.ChatChannel).filter(models.ChatChannel.slug == slug).first()
    if existing:
        slug = f"{slug}-{int(datetime.now().timestamp())}"
    
    db_channel = models.ChatChannel(
        name=channel.name,
        slug=slug,
        description=channel.description,
        channel_type=channel.channel_type,
        created_by=current_user.id
    )
    db.add(db_channel)
    db.flush()
    
    # Add creator as owner
    db.add(models.ChannelMember(
        channel_id=db_channel.id, 
        user_id=current_user.id, 
        role="owner"
    ))
    
    # Add initial members
    for user_id in channel.member_ids:
        if user_id != current_user.id:
            db.add(models.ChannelMember(
                channel_id=db_channel.id,
                user_id=user_id,
                role="member"
            ))
    
    # System message
    db.add(models.ChannelMessage(
        channel_id=db_channel.id,
        user_id=current_user.id,
        content=f"{current_user.username} a créé le salon",
        is_system_message=True
    ))
    
    db.commit()
    db.refresh(db_channel)
    
    return {**db_channel.__dict__, "unread_count": 0, "last_message": None}

@router.get("/channels/{channel_id}")
def get_channel(
    channel_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    channel = db.query(models.ChatChannel).filter(models.ChatChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    membership = get_user_membership(channel_id, current_user.id, db)
    if not membership and channel.channel_type != "public":
        raise HTTPException(status_code=403, detail="Not a member of this channel")
    
    members = []
    for m in channel.members:
        members.append({
            "id": m.id,
            "user_id": m.user_id,
            "username": m.user.username,
            "role": m.role,
            "status": m.user.status,
            "joined_at": m.joined_at
        })
    
    return {
        "channel": {**channel.__dict__, "unread_count": 0, "last_message": None},
        "members": members,
        "my_membership": membership
    }

@router.put("/channels/{channel_id}", response_model=ChannelOut)
def update_channel(
    channel_id: int,
    update: ChannelUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    channel = db.query(models.ChatChannel).filter(models.ChatChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    membership = get_user_membership(channel_id, current_user.id, db)
    if not membership or membership.role not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized to edit this channel")
    
    for key, value in update.model_dump(exclude_unset=True).items():
        setattr(channel, key, value)
    
    db.commit()
    db.refresh(channel)
    return {**channel.__dict__, "unread_count": 0, "last_message": None}

# ========== Member Endpoints ==========

@router.post("/channels/{channel_id}/members")
def add_member(
    channel_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    channel = db.query(models.ChatChannel).filter(models.ChatChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    membership = get_user_membership(channel_id, current_user.id, db)
    if not membership or membership.role not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    existing = get_user_membership(channel_id, user_id, db)
    if existing:
        raise HTTPException(status_code=400, detail="User already a member")
    
    db.add(models.ChannelMember(channel_id=channel_id, user_id=user_id, role="member"))
    
    # System message
    user = db.query(models.User).get(user_id)
    db.add(models.ChannelMessage(
        channel_id=channel_id,
        user_id=current_user.id,
        content=f"{user.username} a rejoint le salon",
        is_system_message=True
    ))
    
    db.commit()
    return {"message": "Member added"}

@router.delete("/channels/{channel_id}/members/{user_id}")
def remove_member(
    channel_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    membership = get_user_membership(channel_id, current_user.id, db)
    # Can remove self or if admin
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member")
    
    if user_id != current_user.id and membership.role not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    target = get_user_membership(channel_id, user_id, db)
    if not target:
        raise HTTPException(status_code=404, detail="User not a member")
    
    db.delete(target)
    db.commit()
    return {"message": "Member removed"}

@router.put("/channels/{channel_id}/notifications")
def update_notification_prefs(
    channel_id: int,
    prefs: NotificationPrefs,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    membership = get_user_membership(channel_id, current_user.id, db)
    if not membership:
        raise HTTPException(status_code=404, detail="Not a member")
    
    membership.notifications_enabled = prefs.notifications_enabled
    membership.sound_enabled = prefs.sound_enabled
    db.commit()
    return {"message": "Preferences updated"}

# ========== Message Endpoints ==========

@router.get("/channels/{channel_id}/messages", response_model=List[MessageOut])
def get_messages(
    channel_id: int,
    limit: int = 50,
    before_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    channel = db.query(models.ChatChannel).filter(models.ChatChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    membership = get_user_membership(channel_id, current_user.id, db)
    if not membership and channel.channel_type != "public":
        raise HTTPException(status_code=403, detail="Not a member")
    
    query = db.query(models.ChannelMessage).filter(
        models.ChannelMessage.channel_id == channel_id
    )
    
    if before_id:
        query = query.filter(models.ChannelMessage.id < before_id)
    
    messages = query.order_by(models.ChannelMessage.timestamp.desc()).limit(limit).all()
    
    # Update last_read_at
    if membership:
        membership.last_read_at = datetime.utcnow()
        db.commit()
    
    result = []
    for m in reversed(messages):
        result.append({
            "id": m.id,
            "channel_id": m.channel_id,
            "user_id": m.user_id,
            "username": m.user.username if m.user else "System",
            "content": m.content,
            "timestamp": m.timestamp,
            "edited_at": m.edited_at,
            "is_system_message": m.is_system_message,
            "reply_to_id": m.reply_to_id,
            "reactions": m.reactions,
            "attachments": m.attachments
        })
    
    return result

@router.post("/channels/{channel_id}/messages", response_model=MessageOut)
def send_message(
    channel_id: int,
    message: MessageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    channel = db.query(models.ChatChannel).filter(models.ChatChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    membership = get_user_membership(channel_id, current_user.id, db)
    if not membership:
        # Auto-join public channels
        if channel.channel_type == "public":
            membership = models.ChannelMember(
                channel_id=channel_id,
                user_id=current_user.id,
                role="member"
            )
            db.add(membership)
        else:
            raise HTTPException(status_code=403, detail="Not a member")
    
    db_message = models.ChannelMessage(
        channel_id=channel_id,
        user_id=current_user.id,
        content=message.content,
        reply_to_id=message.reply_to_id
    )
    db.add(db_message)
    db.flush() 

    if message.attachment_url:
        attachment = models.MessageAttachment(
            message_id=db_message.id,
            file_url=message.attachment_url,
            file_type=message.attachment_type,
            file_name=message.attachment_name,
            file_size=message.attachment_size
        )
        db.add(attachment)
    
    # Update last_read_at for sender
    membership.last_read_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_message)
    
    return {
        "id": db_message.id,
        "channel_id": db_message.channel_id,
        "user_id": db_message.user_id,
        "username": current_user.username,
        "content": db_message.content,
        "timestamp": db_message.timestamp,
        "edited_at": db_message.edited_at,
        "is_system_message": False,
        "reply_to_id": db_message.reply_to_id,
        "reactions": db_message.reactions,
        "attachments": db_message.attachments
    }

# ========== DM Endpoints ==========

@router.post("/dm/{user_id}")
def start_dm(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot DM yourself")
    
    target_user = db.query(models.User).get(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    channel = get_or_create_dm_channel(current_user.id, user_id, db)
    return {"channel_id": channel.id, "slug": channel.slug}

# ========== Notifications ==========

@router.get("/notifications/unread")
def get_unread_counts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    memberships = db.query(models.ChannelMember).filter(
        models.ChannelMember.user_id == current_user.id
    ).all()
    
    total_unread = 0
    channels = {}
    
    for membership in memberships:
        if membership.channel.is_archived:
            continue
            
        if membership.last_read_at:
            unread = db.query(models.ChannelMessage).filter(
                models.ChannelMessage.channel_id == membership.channel_id,
                models.ChannelMessage.timestamp > membership.last_read_at,
                models.ChannelMessage.user_id != current_user.id
            ).count()
        else:
            unread = db.query(models.ChannelMessage).filter(
                models.ChannelMessage.channel_id == membership.channel_id,
                models.ChannelMessage.user_id != current_user.id
            ).count()
        
        if unread > 0:
            channels[membership.channel_id] = unread
            total_unread += unread
    
    return {
        "total": total_unread,
        "channels": channels
    }

# ========== Reaction & Status Endpoints ==========

@router.post("/messages/{message_id}/reactions")
def add_reaction(
    message_id: int,
    emoji: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    message = db.query(models.ChannelMessage).get(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Check if user is in channel
    membership = get_user_membership(message.channel_id, current_user.id, db)
    if not membership and message.channel.channel_type != "public":
        raise HTTPException(status_code=403, detail="Not in channel")
    
    # Check if exists
    existing = db.query(models.MessageReaction).filter(
        models.MessageReaction.message_id == message_id,
        models.MessageReaction.user_id == current_user.id,
        models.MessageReaction.emoji == emoji
    ).first()
    
    if existing:
        db.delete(existing)
        action = "removed"
    else:
        db.add(models.MessageReaction(
            message_id=message_id,
            user_id=current_user.id,
            emoji=emoji
        ))
        action = "added"
    
    db.commit()
    return {"status": action}

@router.put("/users/status")
def update_status(
    status_update: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    current_user.status = status_update.status
    db.commit()
    return {"status": current_user.status}

@router.get("/users/status/{user_id}")
def get_user_status(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    user = db.query(models.User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": user.status}

# ========== Delete Endpoints ==========

@router.delete("/messages/{message_id}")
def delete_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Delete a message (only own message or admin)"""
    message = db.query(models.ChannelMessage).get(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Check permissions: own message or admin
    is_admin = current_user.role and current_user.role.name in ['admin', 'engineer']
    if message.user_id != current_user.id and not is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to delete this message")
    
    db.delete(message)
    db.commit()
    return {"status": "deleted", "message_id": message_id}

@router.delete("/channels/{channel_id}")
def delete_channel(
    channel_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Delete a channel (admin only or channel owner)"""
    channel = db.query(models.ChatChannel).get(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Check permissions
    is_admin = current_user.role and current_user.role.name in ['admin', 'engineer']
    is_owner = channel.created_by == current_user.id
    
    if not is_admin and not is_owner:
        raise HTTPException(status_code=403, detail="Not authorized to delete this channel")
    
    # Delete all messages first
    db.query(models.ChannelMessage).filter(models.ChannelMessage.channel_id == channel_id).delete()
    # Delete all members
    db.query(models.ChannelMember).filter(models.ChannelMember.channel_id == channel_id).delete()
    # Delete channel
    db.delete(channel)
    db.commit()
    return {"status": "deleted", "channel_id": channel_id}

@router.put("/channels/{channel_id}/messages/{message_id}/read")
def mark_message_read(
    channel_id: int,
    message_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Mark up to this message as read"""
    message = db.query(models.ChannelMessage).get(message_id)
    if not message or message.channel_id != channel_id:
        raise HTTPException(status_code=404, detail="Message not found")
    
    membership = db.query(models.ChannelMember).filter(
        models.ChannelMember.channel_id == channel_id,
        models.ChannelMember.user_id == current_user.id
    ).first()
    
    if membership:
        membership.last_read_at = message.timestamp
        db.commit()
    
    return {"status": "marked_read"}
