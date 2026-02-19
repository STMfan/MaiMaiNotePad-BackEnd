"""
TestDataFactory for generating test data
Provides factory methods for creating test instances of all major models
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.models.database import (
    User, KnowledgeBase, PersonaCard, Message, Comment,
    KnowledgeBaseFile, PersonaCardFile, StarRecord, CommentReaction
)
from app.core.security import get_password_hash


class TestDataFactory:
    """Factory for generating test data with referential integrity"""
    
    def __init__(self, db: Session):
        """
        Initialize the factory with a database session
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create_user(
        self,
        username: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
        is_active: bool = True,
        is_admin: bool = False,
        is_moderator: bool = False,
        is_super_admin: bool = False,
        is_muted: bool = False,
        muted_until: Optional[datetime] = None,
        failed_login_attempts: int = 0,
        locked_until: Optional[datetime] = None,
        password_version: int = 0,
        **kwargs
    ) -> User:
        """
        Create a test user with customizable attributes
        
        Args:
            username: Username (auto-generated if not provided)
            email: Email address (auto-generated if not provided)
            password: Plain text password (default: "testpassword123")
            is_active: Whether user is active
            is_admin: Whether user is admin
            is_moderator: Whether user is moderator
            is_super_admin: Whether user is super admin
            is_muted: Whether user is muted
            muted_until: Mute expiration datetime
            failed_login_attempts: Number of failed login attempts
            locked_until: Account lock expiration datetime
            password_version: Password version for token invalidation
            **kwargs: Additional attributes to set on the user
        
        Returns:
            Created User instance
        """
        # Generate unique username and email if not provided
        unique_id = str(uuid.uuid4())[:8]
        if username is None:
            username = f"testuser_{unique_id}"
        if email is None:
            email = f"test_{unique_id}@example.com"
        if password is None:
            password = "testpassword123"
        
        user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            is_active=is_active,
            is_admin=is_admin,
            is_moderator=is_moderator,
            is_super_admin=is_super_admin,
            is_muted=is_muted,
            muted_until=muted_until,
            failed_login_attempts=failed_login_attempts,
            locked_until=locked_until,
            password_version=password_version,
            created_at=datetime.now(),
            **kwargs
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def create_knowledge_base(
        self,
        uploader: Optional[User] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_public: bool = False,
        is_pending: bool = True,
        star_count: int = 0,
        downloads: int = 0,
        content: Optional[str] = None,
        tags: Optional[str] = None,
        copyright_owner: Optional[str] = None,
        version: str = "1.0",
        **kwargs
    ) -> KnowledgeBase:
        """
        Create a test knowledge base with customizable attributes
        
        Args:
            uploader: User who uploaded the knowledge base (auto-created if not provided)
            name: Knowledge base name (auto-generated if not provided)
            description: Knowledge base description (auto-generated if not provided)
            is_public: Whether knowledge base is public
            is_pending: Whether knowledge base is pending review
            star_count: Number of stars
            downloads: Number of downloads
            content: Knowledge base content
            tags: Comma-separated tags
            copyright_owner: Copyright owner name
            version: Version string
            **kwargs: Additional attributes to set on the knowledge base
        
        Returns:
            Created KnowledgeBase instance
        """
        # Create uploader if not provided
        if uploader is None:
            uploader = self.create_user()
        
        # Generate unique name and description if not provided
        unique_id = str(uuid.uuid4())[:8]
        if name is None:
            name = f"Test Knowledge Base {unique_id}"
        if description is None:
            description = f"Test description for knowledge base {unique_id}"
        
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            uploader_id=uploader.id,
            is_public=is_public,
            is_pending=is_pending,
            star_count=star_count,
            downloads=downloads,
            content=content,
            tags=tags,
            copyright_owner=copyright_owner,
            version=version,
            base_path="[]",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            **kwargs
        )
        
        self.db.add(kb)
        self.db.commit()
        self.db.refresh(kb)
        return kb
    
    def create_persona_card(
        self,
        uploader: Optional[User] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_public: bool = False,
        is_pending: bool = True,
        star_count: int = 0,
        downloads: int = 0,
        content: Optional[str] = None,
        tags: Optional[str] = None,
        copyright_owner: Optional[str] = None,
        version: str = "1.0",
        base_path: str = "/test/path",
        **kwargs
    ) -> PersonaCard:
        """
        Create a test persona card with customizable attributes
        
        Args:
            uploader: User who uploaded the persona card (auto-created if not provided)
            name: Persona card name (auto-generated if not provided)
            description: Persona card description (auto-generated if not provided)
            is_public: Whether persona card is public
            is_pending: Whether persona card is pending review
            star_count: Number of stars
            downloads: Number of downloads
            content: Persona card content
            tags: Comma-separated tags
            copyright_owner: Copyright owner name
            version: Version string
            base_path: Base path for persona card files
            **kwargs: Additional attributes to set on the persona card
        
        Returns:
            Created PersonaCard instance
        """
        # Create uploader if not provided
        if uploader is None:
            uploader = self.create_user()
        
        # Generate unique name and description if not provided
        unique_id = str(uuid.uuid4())[:8]
        if name is None:
            name = f"Test Persona Card {unique_id}"
        if description is None:
            description = f"Test description for persona card {unique_id}"
        
        persona = PersonaCard(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            uploader_id=uploader.id,
            is_public=is_public,
            is_pending=is_pending,
            star_count=star_count,
            downloads=downloads,
            content=content,
            tags=tags,
            copyright_owner=copyright_owner,
            version=version,
            base_path=base_path,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            **kwargs
        )
        
        self.db.add(persona)
        self.db.commit()
        self.db.refresh(persona)
        return persona
    
    def create_message(
        self,
        recipient: Optional[User] = None,
        sender: Optional[User] = None,
        title: Optional[str] = None,
        content: Optional[str] = None,
        summary: Optional[str] = None,
        message_type: str = "direct",
        broadcast_scope: Optional[str] = None,
        is_read: bool = False,
        **kwargs
    ) -> Message:
        """
        Create a test message with customizable attributes
        
        Args:
            recipient: User receiving the message (auto-created if not provided)
            sender: User sending the message (auto-created if not provided)
            title: Message title (auto-generated if not provided)
            content: Message content (auto-generated if not provided)
            summary: Message summary
            message_type: Type of message (direct, broadcast, etc.)
            broadcast_scope: Scope for broadcast messages
            is_read: Whether message has been read
            **kwargs: Additional attributes to set on the message
        
        Returns:
            Created Message instance
        """
        # Create recipient and sender if not provided
        if recipient is None:
            recipient = self.create_user()
        if sender is None:
            sender = self.create_user()
        
        # Generate unique title and content if not provided
        unique_id = str(uuid.uuid4())[:8]
        if title is None:
            title = f"Test Message {unique_id}"
        if content is None:
            content = f"Test message content {unique_id}"
        
        message = Message(
            id=str(uuid.uuid4()),
            recipient_id=recipient.id,
            sender_id=sender.id,
            title=title,
            content=content,
            summary=summary,
            message_type=message_type,
            broadcast_scope=broadcast_scope,
            is_read=is_read,
            created_at=datetime.now(),
            **kwargs
        )
        
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message
    
    def create_comment(
        self,
        user: Optional[User] = None,
        target_id: Optional[str] = None,
        target_type: str = "knowledge",
        content: Optional[str] = None,
        parent_id: Optional[str] = None,
        is_deleted: bool = False,
        like_count: int = 0,
        dislike_count: int = 0,
        **kwargs
    ) -> Comment:
        """
        Create a test comment with customizable attributes
        
        Args:
            user: User creating the comment (auto-created if not provided)
            target_id: ID of the target (knowledge base or persona card)
            target_type: Type of target ("knowledge" or "persona")
            content: Comment content (auto-generated if not provided)
            parent_id: ID of parent comment for nested comments
            is_deleted: Whether comment is deleted
            like_count: Number of likes
            dislike_count: Number of dislikes
            **kwargs: Additional attributes to set on the comment
        
        Returns:
            Created Comment instance
        """
        # Create user if not provided
        if user is None:
            user = self.create_user()
        
        # Create target if not provided
        if target_id is None:
            if target_type == "knowledge":
                target = self.create_knowledge_base(uploader=user)
                target_id = target.id
            elif target_type == "persona":
                target = self.create_persona_card(uploader=user)
                target_id = target.id
            else:
                target_id = str(uuid.uuid4())
        
        # Generate unique content if not provided
        unique_id = str(uuid.uuid4())[:8]
        if content is None:
            content = f"Test comment content {unique_id}"
        
        comment = Comment(
            id=str(uuid.uuid4()),
            user_id=user.id,
            target_id=target_id,
            target_type=target_type,
            content=content,
            parent_id=parent_id,
            is_deleted=is_deleted,
            like_count=like_count,
            dislike_count=dislike_count,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            **kwargs
        )
        
        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)
        return comment
    
    def create_knowledge_base_file(
        self,
        knowledge_base: Optional[KnowledgeBase] = None,
        file_name: Optional[str] = None,
        original_name: Optional[str] = None,
        file_path: Optional[str] = None,
        file_type: str = ".txt",
        file_size: int = 1024,
        **kwargs
    ) -> KnowledgeBaseFile:
        """
        Create a test knowledge base file with customizable attributes
        
        Args:
            knowledge_base: Knowledge base to attach file to (auto-created if not provided)
            file_name: Stored file name (auto-generated if not provided)
            original_name: Original file name (auto-generated if not provided)
            file_path: File path (auto-generated if not provided)
            file_type: File type/extension
            file_size: File size in bytes
            **kwargs: Additional attributes to set on the file
        
        Returns:
            Created KnowledgeBaseFile instance
        """
        # Create knowledge base if not provided
        if knowledge_base is None:
            knowledge_base = self.create_knowledge_base()
        
        # Generate unique file names if not provided
        unique_id = str(uuid.uuid4())[:8]
        if file_name is None:
            file_name = f"test_file_{unique_id}{file_type}"
        if original_name is None:
            original_name = f"original_{unique_id}{file_type}"
        if file_path is None:
            file_path = f"/test/path/{file_name}"
        
        kb_file = KnowledgeBaseFile(
            id=str(uuid.uuid4()),
            knowledge_base_id=knowledge_base.id,
            file_name=file_name,
            original_name=original_name,
            file_path=file_path,
            file_type=file_type,
            file_size=file_size,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            **kwargs
        )
        
        self.db.add(kb_file)
        self.db.commit()
        self.db.refresh(kb_file)
        return kb_file
    
    def create_persona_card_file(
        self,
        persona_card: Optional[PersonaCard] = None,
        file_name: Optional[str] = None,
        original_name: Optional[str] = None,
        file_path: Optional[str] = None,
        file_type: str = ".txt",
        file_size: int = 1024,
        **kwargs
    ) -> PersonaCardFile:
        """
        Create a test persona card file with customizable attributes
        
        Args:
            persona_card: Persona card to attach file to (auto-created if not provided)
            file_name: Stored file name (auto-generated if not provided)
            original_name: Original file name (auto-generated if not provided)
            file_path: File path (auto-generated if not provided)
            file_type: File type/extension
            file_size: File size in bytes
            **kwargs: Additional attributes to set on the file
        
        Returns:
            Created PersonaCardFile instance
        """
        # Create persona card if not provided
        if persona_card is None:
            persona_card = self.create_persona_card()
        
        # Generate unique file names if not provided
        unique_id = str(uuid.uuid4())[:8]
        if file_name is None:
            file_name = f"test_file_{unique_id}{file_type}"
        if original_name is None:
            original_name = f"original_{unique_id}{file_type}"
        if file_path is None:
            file_path = f"/test/path/{file_name}"
        
        pc_file = PersonaCardFile(
            id=str(uuid.uuid4()),
            persona_card_id=persona_card.id,
            file_name=file_name,
            original_name=original_name,
            file_path=file_path,
            file_type=file_type,
            file_size=file_size,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            **kwargs
        )
        
        self.db.add(pc_file)
        self.db.commit()
        self.db.refresh(pc_file)
        return pc_file
    
    def create_star_record(
        self,
        user: Optional[User] = None,
        target_id: Optional[str] = None,
        target_type: str = "knowledge",
        **kwargs
    ) -> StarRecord:
        """
        Create a test star record with customizable attributes
        
        Args:
            user: User creating the star (auto-created if not provided)
            target_id: ID of the target (knowledge base or persona card)
            target_type: Type of target ("knowledge" or "persona")
            **kwargs: Additional attributes to set on the star record
        
        Returns:
            Created StarRecord instance
        """
        # Create user if not provided
        if user is None:
            user = self.create_user()
        
        # Create target if not provided
        if target_id is None:
            if target_type == "knowledge":
                target = self.create_knowledge_base()
                target_id = target.id
            elif target_type == "persona":
                target = self.create_persona_card()
                target_id = target.id
            else:
                target_id = str(uuid.uuid4())
        
        star = StarRecord(
            id=str(uuid.uuid4()),
            user_id=user.id,
            target_id=target_id,
            target_type=target_type,
            created_at=datetime.now(),
            **kwargs
        )
        
        self.db.add(star)
        self.db.commit()
        self.db.refresh(star)
        return star
    
    def create_comment_reaction(
        self,
        user: Optional[User] = None,
        comment: Optional[Comment] = None,
        reaction_type: str = "like",
        **kwargs
    ) -> CommentReaction:
        """
        Create a test comment reaction with customizable attributes
        
        Args:
            user: User creating the reaction (auto-created if not provided)
            comment: Comment to react to (auto-created if not provided)
            reaction_type: Type of reaction ("like" or "dislike")
            **kwargs: Additional attributes to set on the reaction
        
        Returns:
            Created CommentReaction instance
        """
        # Create user if not provided
        if user is None:
            user = self.create_user()
        
        # Create comment if not provided
        if comment is None:
            comment = self.create_comment(user=user)
        
        reaction = CommentReaction(
            id=str(uuid.uuid4()),
            user_id=user.id,
            comment_id=comment.id,
            reaction_type=reaction_type,
            created_at=datetime.now(),
            **kwargs
        )
        
        self.db.add(reaction)
        self.db.commit()
        self.db.refresh(reaction)
        return reaction
