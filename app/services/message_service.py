"""Message service module

This module provides business logic for message operations including:
- Message CRUD operations
- Broadcast message functionality
- Message read/unread status management
"""

import re
from datetime import datetime
from typing import List, Optional, Set, Dict, Any
from sqlalchemy.orm import Session

from app.models.database import Message, User


class MessageService:
    """Service class for message operations"""

    def __init__(self, db: Session):
        """Initialize message service with database session
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_message_by_id(self, message_id: str) -> Optional[Message]:
        """Get message by ID
        
        Args:
            message_id: Message ID
            
        Returns:
            Message object or None if not found
        """
        return self.db.query(Message).filter(Message.id == message_id).first()

    def get_user_messages(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> List[Message]:
        """Get messages received by user
        
        Args:
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Number of messages per page
            
        Returns:
            List of Message objects
        """
        offset = (page - 1) * page_size
        return self.db.query(Message).filter(
            Message.recipient_id == user_id
        ).order_by(Message.created_at.desc()).offset(offset).limit(page_size).all()

    def get_conversation_messages(
        self,
        user_id: str,
        other_user_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> List[Message]:
        """Get conversation messages between two users
        
        Args:
            user_id: Current user ID
            other_user_id: Other user ID
            page: Page number (1-indexed)
            page_size: Number of messages per page
            
        Returns:
            List of Message objects
        """
        offset = (page - 1) * page_size
        return self.db.query(Message).filter(
            ((Message.sender_id == user_id) & (Message.recipient_id == other_user_id)) |
            ((Message.sender_id == other_user_id) & (Message.recipient_id == user_id))
        ).order_by(Message.created_at.desc()).offset(offset).limit(page_size).all()

    def get_user_messages_by_type(
        self,
        user_id: str,
        message_type: str,
        page: int = 1,
        page_size: int = 20
    ) -> List[Message]:
        """Get user messages filtered by type
        
        Args:
            user_id: User ID
            message_type: Message type (e.g., 'direct', 'announcement')
            page: Page number (1-indexed)
            page_size: Number of messages per page
            
        Returns:
            List of Message objects
        """
        offset = (page - 1) * page_size
        return self.db.query(Message).filter(
            Message.recipient_id == user_id,
            Message.message_type == message_type
        ).order_by(Message.created_at.desc()).offset(offset).limit(page_size).all()

    def get_all_users(self) -> List[User]:
        """Get all users
        
        Returns:
            List of User objects
        """
        return self.db.query(User).all()

    def get_users_by_ids(self, user_ids: List[str]) -> List[User]:
        """Get users by IDs
        
        Args:
            user_ids: List of user IDs
            
        Returns:
            List of User objects
        """
        return self.db.query(User).filter(User.id.in_(user_ids)).all()

    def generate_summary(self, content: str) -> str:
        """Generate summary from content
        
        Args:
            content: Message content
            
        Returns:
            Generated summary (max 150 characters)
        """
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', content)
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        if len(text) > 150:
            truncated = text[:150]
            # Try to find last punctuation
            last_punctuation = max(
                truncated.rfind('。'),
                truncated.rfind('！'),
                truncated.rfind('？'),
                truncated.rfind('.'),
                truncated.rfind('!'),
                truncated.rfind('?')
            )
            if last_punctuation > 75:
                return truncated[:last_punctuation + 1]
            else:
                return truncated + '...'
        else:
            return text

    def create_messages(
        self,
        sender_id: str,
        recipient_ids: Set[str],
        title: str,
        content: str,
        summary: Optional[str] = None,
        message_type: str = "direct",
        broadcast_scope: Optional[str] = None
    ) -> List[Message]:
        """Create messages for multiple recipients
        
        Args:
            sender_id: Sender user ID
            recipient_ids: Set of recipient user IDs
            title: Message title
            content: Message content
            summary: Message summary (auto-generated if not provided)
            message_type: Message type ('direct' or 'announcement')
            broadcast_scope: Broadcast scope (e.g., 'all_users')
            
        Returns:
            List of created Message objects
        """
        # Generate summary if not provided
        if not summary and content:
            summary = self.generate_summary(content)

        # Create message objects
        messages = []
        for recipient_id in recipient_ids:
            message = Message(
                sender_id=sender_id,
                recipient_id=recipient_id,
                title=title,
                content=content,
                summary=summary,
                message_type=message_type,
                broadcast_scope=broadcast_scope if message_type == "announcement" else None,
                is_read=False,
                created_at=datetime.now()
            )
            self.db.add(message)
            messages.append(message)

        # Commit all messages
        self.db.commit()
        
        # Refresh to get IDs
        for message in messages:
            self.db.refresh(message)

        return messages

    def mark_message_read(self, message_id: str, user_id: str) -> bool:
        """Mark message as read
        
        Args:
            message_id: Message ID
            user_id: User ID (must be recipient)
            
        Returns:
            True if successful, False otherwise
        """
        message = self.get_message_by_id(message_id)
        if not message:
            return False
        
        # Verify user is recipient
        if str(message.recipient_id) != str(user_id):
            return False
        
        message.is_read = True
        self.db.commit()
        return True

    def delete_message(self, message_id: str, user_id: str) -> bool:
        """Delete a single message
        
        Args:
            message_id: Message ID
            user_id: User ID (must be recipient)
            
        Returns:
            True if successful, False otherwise
        """
        message = self.get_message_by_id(message_id)
        if not message:
            return False
        
        # Verify user is recipient
        if str(message.recipient_id) != str(user_id):
            return False
        
        self.db.delete(message)
        self.db.commit()
        return True

    def delete_broadcast_messages(self, message_id: str, sender_id: str) -> int:
        """Delete all messages in a broadcast
        
        Args:
            message_id: Any message ID from the broadcast
            sender_id: Sender user ID (must be sender)
            
        Returns:
            Number of messages deleted
        """
        # Get the original message to find broadcast details
        original_message = self.get_message_by_id(message_id)
        if not original_message:
            return 0
        
        # Verify user is sender
        if str(original_message.sender_id) != str(sender_id):
            return 0
        
        # Find all messages with same sender, title, and created_at (within 1 second)
        # This identifies messages from the same broadcast
        messages = self.db.query(Message).filter(
            Message.sender_id == sender_id,
            Message.title == original_message.title,
            Message.message_type == "announcement",
            Message.broadcast_scope == "all_users"
        ).all()
        
        # Filter by created_at within 1 second
        target_time = original_message.created_at
        broadcast_messages = [
            msg for msg in messages
            if abs((msg.created_at - target_time).total_seconds()) < 1
        ]
        
        # Delete all broadcast messages
        count = 0
        for message in broadcast_messages:
            self.db.delete(message)
            count += 1
        
        self.db.commit()
        return count

    def update_message(
        self,
        message_id: str,
        user_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        summary: Optional[str] = None
    ) -> bool:
        """Update a single message
        
        Args:
            message_id: Message ID
            user_id: User ID (must be recipient)
            title: New title (optional)
            content: New content (optional)
            summary: New summary (optional)
            
        Returns:
            True if successful, False otherwise
        """
        message = self.get_message_by_id(message_id)
        if not message:
            return False
        
        # Verify user is recipient
        if str(message.recipient_id) != str(user_id):
            return False
        
        # Update fields
        if title:
            message.title = title
        if content:
            message.content = content
        if summary is not None:  # Allow empty string
            message.summary = summary
        
        self.db.commit()
        return True

    def update_broadcast_messages(
        self,
        message_id: str,
        sender_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        summary: Optional[str] = None
    ) -> int:
        """Update all messages in a broadcast
        
        Args:
            message_id: Any message ID from the broadcast
            sender_id: Sender user ID (must be sender)
            title: New title (optional)
            content: New content (optional)
            summary: New summary (optional)
            
        Returns:
            Number of messages updated
        """
        # Get the original message to find broadcast details
        original_message = self.get_message_by_id(message_id)
        if not original_message:
            return 0
        
        # Verify user is sender
        if str(original_message.sender_id) != str(sender_id):
            return 0
        
        # Find all messages with same sender, title, and created_at (within 1 second)
        messages = self.db.query(Message).filter(
            Message.sender_id == sender_id,
            Message.title == original_message.title,
            Message.message_type == "announcement",
            Message.broadcast_scope == "all_users"
        ).all()
        
        # Filter by created_at within 1 second
        target_time = original_message.created_at
        broadcast_messages = [
            msg for msg in messages
            if abs((msg.created_at - target_time).total_seconds()) < 1
        ]
        
        # Update all broadcast messages
        count = 0
        for message in broadcast_messages:
            if title:
                message.title = title
            if content:
                message.content = content
            if summary is not None:  # Allow empty string
                message.summary = summary
            count += 1
        
        self.db.commit()
        return count

    def get_broadcast_messages(self, page: int = 1, page_size: int = 20) -> List[Message]:
        """Get broadcast messages (unique by sender, title, and time)
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of messages per page
            
        Returns:
            List of unique broadcast Message objects
        """
        # Get all announcement messages
        all_messages = self.db.query(Message).filter(
            Message.message_type == "announcement",
            Message.broadcast_scope == "all_users"
        ).order_by(Message.created_at.desc()).all()
        
        # Group by sender_id, title, and created_at (within 1 second)
        unique_messages = []
        seen = set()
        
        for msg in all_messages:
            # Create a key based on sender, title, and rounded timestamp
            timestamp_key = int(msg.created_at.timestamp()) if msg.created_at else 0
            key = (msg.sender_id, msg.title, timestamp_key)
            
            if key not in seen:
                seen.add(key)
                unique_messages.append(msg)
        
        # Paginate
        offset = (page - 1) * page_size
        return unique_messages[offset:offset + page_size]

    def get_broadcast_message_stats(self, message_id: str) -> Dict[str, Any]:
        """Get statistics for a broadcast message
        
        Args:
            message_id: Any message ID from the broadcast
            
        Returns:
            Dictionary with stats (total_sent, total_read, total_unread)
        """
        # Get the original message
        original_message = self.get_message_by_id(message_id)
        if not original_message:
            return {
                "total_sent": 0,
                "total_read": 0,
                "total_unread": 0
            }
        
        # Find all messages with same sender, title, and created_at (within 1 second)
        messages = self.db.query(Message).filter(
            Message.sender_id == original_message.sender_id,
            Message.title == original_message.title,
            Message.message_type == "announcement",
            Message.broadcast_scope == "all_users"
        ).all()
        
        # Filter by created_at within 1 second
        target_time = original_message.created_at
        broadcast_messages = [
            msg for msg in messages
            if abs((msg.created_at - target_time).total_seconds()) < 1
        ]
        
        total_sent = len(broadcast_messages)
        total_read = sum(1 for msg in broadcast_messages if msg.is_read)
        total_unread = total_sent - total_read
        
        return {
            "total_sent": total_sent,
            "total_read": total_read,
            "total_unread": total_unread
        }

    def count_broadcast_messages(self) -> int:
        """Count total broadcast messages
        
        Returns:
            Total count of broadcast messages
        """
        return self.db.query(Message).filter(
            Message.message_type == "announcement",
            Message.broadcast_scope == "all_users"
        ).count()
