"""In-app messaging router for client-bidder communication."""

from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session

from elipsis_api import models
from elipsis_api.database import get_db
from elipsis_api.deps import get_current_user

router = APIRouter(prefix="/messages", tags=["messaging"])


@router.get("/conversations")
def list_conversations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    List all conversations for the current user.
    
    Returns conversations with last message preview.
    """
    # Get conversations where user is participant
    conversations = db.scalars(
        select(models.Conversation).where(
            or_(
                models.Conversation.user1_id == current_user.id,
                models.Conversation.user2_id == current_user.id
            )
        ).order_by(models.Conversation.last_message_at.desc())
    ).all()
    
    results = []
    for conv in conversations:
        # Get other participant
        other_user_id = conv.user2_id if conv.user1_id == current_user.id else conv.user1_id
        other_user = db.get(models.User, other_user_id)
        
        # Get last message
        last_message = db.scalar(
            select(models.Message)
            .where(models.Message.conversation_id == conv.id)
            .order_by(models.Message.created_at.desc())
            .limit(1)
        )
        
        # Count unread messages
        unread_count = db.scalar(
            select(models.Message)
            .where(
                and_(
                    models.Message.conversation_id == conv.id,
                    models.Message.receiver_id == current_user.id,
                    models.Message.is_read == False
                )
            ).count()
        ) or 0
        
        results.append({
            "id": conv.id,
            "request_id": conv.request_id,
            "other_user": {
                "id": other_user.id,
                "name": other_user.name,
                "user_type": other_user.user_type
            } if other_user else None,
            "last_message": {
                "content": last_message.content,
                "created_at": last_message.created_at.isoformat(),
                "is_from_me": last_message.sender_id == current_user.id
            } if last_message else None,
            "unread_count": unread_count,
            "updated_at": conv.last_message_at.isoformat()
        })
    
    return {"conversations": results, "count": len(results)}


@router.get("/conversations/{conversation_id}")
def get_conversation_messages(
    conversation_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Get messages in a conversation.
    
    - **conversation_id**: Conversation ID
    - **limit**: Messages per page
    - **offset**: Pagination offset
    """
    # Verify user is participant
    conv = db.get(models.Conversation, conversation_id)
    
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    if conv.user1_id != current_user.id and conv.user2_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this conversation"
        )
    
    # Get messages
    messages = db.scalars(
        select(models.Message)
        .where(models.Message.conversation_id == conversation_id)
        .order_by(models.Message.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    
    # Mark unread messages as read
    db.execute(
        select(models.Message)
        .where(
            and_(
                models.Message.conversation_id == conversation_id,
                models.Message.receiver_id == current_user.id,
                models.Message.is_read == False
            )
        )
    )
    for msg in messages:
        if msg.receiver_id == current_user.id and not msg.is_read:
            msg.is_read = True
    db.commit()
    
    # Format messages
    results = []
    for msg in reversed(messages):  # Reverse to show oldest first
        sender = db.get(models.User, msg.sender_id)
        results.append({
            "id": msg.id,
            "content": msg.content,
            "sender": {
                "id": sender.id,
                "name": sender.name,
                "user_type": sender.user_type
            } if sender else None,
            "is_from_me": msg.sender_id == current_user.id,
            "is_read": msg.is_read,
            "created_at": msg.created_at.isoformat()
        })
    
    return {
        "conversation_id": conversation_id,
        "messages": results,
        "count": len(results)
    }


@router.post("/conversations/{conversation_id}/messages", status_code=status.HTTP_201_CREATED)
def send_message(
    conversation_id: int,
    content: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Send a message in a conversation.
    
    - **conversation_id**: Conversation ID
    - **content**: Message content
    """
    # Verify user is participant
    conv = db.get(models.Conversation, conversation_id)
    
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    if conv.user1_id != current_user.id and conv.user2_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this conversation"
        )
    
    # Determine receiver
    receiver_id = conv.user2_id if conv.user1_id == current_user.id else conv.user1_id
    
    # Create message
    message = models.Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        receiver_id=receiver_id,
        content=content,
        is_read=False
    )
    
    db.add(message)
    
    # Update conversation last_message_at
    conv.last_message_at = datetime.now()
    
    db.commit()
    db.refresh(message)
    
    return {
        "id": message.id,
        "content": message.content,
        "created_at": message.created_at.isoformat(),
        "message": "Message sent successfully"
    }


@router.post("/conversations/start", status_code=status.HTTP_201_CREATED)
def start_conversation(
    other_user_id: int,
    request_id: int | None = None,
    initial_message: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Start a new conversation with another user.
    
    - **other_user_id**: User to message
    - **request_id**: Optional related request
    - **initial_message**: Optional first message
    """
    # Check if conversation already exists
    existing = db.scalar(
        select(models.Conversation).where(
            or_(
                and_(
                    models.Conversation.user1_id == current_user.id,
                    models.Conversation.user2_id == other_user_id
                ),
                and_(
                    models.Conversation.user1_id == other_user_id,
                    models.Conversation.user2_id == current_user.id
                )
            )
        )
    )
    
    if existing:
        # Return existing conversation
        return {
            "id": existing.id,
            "request_id": existing.request_id,
            "message": "Conversation already exists"
        }
    
    # Verify other user exists
    other_user = db.get(models.User, other_user_id)
    if not other_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Create conversation
    conversation = models.Conversation(
        user1_id=current_user.id,
        user2_id=other_user_id,
        request_id=request_id,
        last_message_at=datetime.now()
    )
    
    db.add(conversation)
    db.flush()
    
    # Send initial message if provided
    if initial_message:
        message = models.Message(
            conversation_id=conversation.id,
            sender_id=current_user.id,
            receiver_id=other_user_id,
            content=initial_message,
            is_read=False
        )
        db.add(message)
    
    db.commit()
    db.refresh(conversation)
    
    return {
        "id": conversation.id,
        "request_id": conversation.request_id,
        "message": "Conversation started successfully"
    }


@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get total unread message count for current user."""
    
    unread_count = db.scalar(
        select(models.Message)
        .where(
            and_(
                models.Message.receiver_id == current_user.id,
                models.Message.is_read == False
            )
        ).count()
    ) or 0
    
    return {"unread_count": unread_count}


@router.put("/messages/{message_id}/read")
def mark_message_read(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Mark a message as read."""
    
    message = db.get(models.Message, message_id)
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    if message.receiver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only mark your own messages as read"
        )
    
    message.is_read = True
    db.commit()
    
    return {"message": "Marked as read"}
