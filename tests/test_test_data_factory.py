"""
Tests for TestDataFactory
Verifies that the factory creates valid test data with proper referential integrity
"""

import pytest
from datetime import datetime, timedelta
from tests.test_data_factory import TestDataFactory
from app.models.database import (
    User, KnowledgeBase, PersonaCard, Message, Comment,
    KnowledgeBaseFile, PersonaCardFile, StarRecord, CommentReaction
)


def test_factory_fixture_available(factory):
    """Test that factory fixture is available"""
    assert factory is not None
    assert isinstance(factory, TestDataFactory)


def test_create_user_with_defaults(factory):
    """Test creating a user with default values"""
    user = factory.create_user()
    
    assert user.id is not None
    assert user.username.startswith("testuser_")
    assert user.email.startswith("test_")
    assert "@example.com" in user.email
    assert user.is_active is True
    assert user.is_admin is False
    assert user.is_moderator is False
    assert user.is_super_admin is False
    assert user.password_version == 0
    assert user.failed_login_attempts == 0


def test_create_user_with_custom_values(factory):
    """Test creating a user with custom values"""
    user = factory.create_user(
        username="customuser",
        email="custom@example.com",
        is_admin=True,
        is_moderator=True,
        password_version=5
    )
    
    assert user.username == "customuser"
    assert user.email == "custom@example.com"
    assert user.is_admin is True
    assert user.is_moderator is True
    assert user.password_version == 5


def test_create_user_with_kwargs(factory):
    """Test creating a user with additional kwargs"""
    locked_time = datetime.now() + timedelta(hours=1)
    user = factory.create_user(
        locked_until=locked_time,
        failed_login_attempts=3
    )
    
    assert user.locked_until == locked_time
    assert user.failed_login_attempts == 3


def test_create_knowledge_base_with_defaults(factory):
    """Test creating a knowledge base with default values"""
    kb = factory.create_knowledge_base()
    
    assert kb.id is not None
    assert kb.name.startswith("Test Knowledge Base")
    assert kb.description.startswith("Test description")
    assert kb.uploader_id is not None
    assert kb.is_public is False
    assert kb.is_pending is True
    assert kb.star_count == 0
    assert kb.downloads == 0
    assert kb.version == "1.0"


def test_create_knowledge_base_with_existing_user(factory):
    """Test creating a knowledge base with an existing user"""
    user = factory.create_user(username="kbowner")
    kb = factory.create_knowledge_base(uploader=user)
    
    assert kb.uploader_id == user.id
    assert kb.uploader.username == "kbowner"


def test_create_knowledge_base_with_custom_values(factory):
    """Test creating a knowledge base with custom values"""
    kb = factory.create_knowledge_base(
        name="Custom KB",
        description="Custom description",
        is_public=True,
        is_pending=False,
        star_count=10,
        downloads=50,
        tags="tag1,tag2,tag3"
    )
    
    assert kb.name == "Custom KB"
    assert kb.description == "Custom description"
    assert kb.is_public is True
    assert kb.is_pending is False
    assert kb.star_count == 10
    assert kb.downloads == 50
    assert kb.tags == "tag1,tag2,tag3"


def test_create_persona_card_with_defaults(factory):
    """Test creating a persona card with default values"""
    persona = factory.create_persona_card()
    
    assert persona.id is not None
    assert persona.name.startswith("Test Persona Card")
    assert persona.description.startswith("Test description")
    assert persona.uploader_id is not None
    assert persona.is_public is False
    assert persona.is_pending is True
    assert persona.star_count == 0
    assert persona.downloads == 0
    assert persona.version == "1.0"


def test_create_persona_card_with_existing_user(factory):
    """Test creating a persona card with an existing user"""
    user = factory.create_user(username="personaowner")
    persona = factory.create_persona_card(uploader=user)
    
    assert persona.uploader_id == user.id
    assert persona.uploader.username == "personaowner"


def test_create_persona_card_with_custom_values(factory):
    """Test creating a persona card with custom values"""
    persona = factory.create_persona_card(
        name="Custom Persona",
        description="Custom description",
        is_public=True,
        is_pending=False,
        star_count=15,
        downloads=75,
        tags="persona,test"
    )
    
    assert persona.name == "Custom Persona"
    assert persona.description == "Custom description"
    assert persona.is_public is True
    assert persona.is_pending is False
    assert persona.star_count == 15
    assert persona.downloads == 75
    assert persona.tags == "persona,test"


def test_create_message_with_defaults(factory):
    """Test creating a message with default values"""
    message = factory.create_message()
    
    assert message.id is not None
    assert message.title.startswith("Test Message")
    assert message.content.startswith("Test message content")
    assert message.recipient_id is not None
    assert message.sender_id is not None
    assert message.message_type == "direct"
    assert message.is_read is False


def test_create_message_with_existing_users(factory):
    """Test creating a message with existing users"""
    sender = factory.create_user(username="sender")
    recipient = factory.create_user(username="recipient")
    message = factory.create_message(sender=sender, recipient=recipient)
    
    assert message.sender_id == sender.id
    assert message.recipient_id == recipient.id
    assert message.sender.username == "sender"
    assert message.recipient.username == "recipient"


def test_create_message_with_custom_values(factory):
    """Test creating a message with custom values"""
    message = factory.create_message(
        title="Custom Title",
        content="Custom content",
        message_type="broadcast",
        broadcast_scope="all",
        is_read=True
    )
    
    assert message.title == "Custom Title"
    assert message.content == "Custom content"
    assert message.message_type == "broadcast"
    assert message.broadcast_scope == "all"
    assert message.is_read is True


def test_create_comment_with_defaults(factory):
    """Test creating a comment with default values"""
    comment = factory.create_comment()
    
    assert comment.id is not None
    assert comment.content.startswith("Test comment content")
    assert comment.user_id is not None
    assert comment.target_id is not None
    assert comment.target_type == "knowledge"
    assert comment.is_deleted is False
    assert comment.like_count == 0
    assert comment.dislike_count == 0


def test_create_comment_on_knowledge_base(factory):
    """Test creating a comment on a knowledge base"""
    kb = factory.create_knowledge_base()
    user = factory.create_user()
    comment = factory.create_comment(
        user=user,
        target_id=kb.id,
        target_type="knowledge"
    )
    
    assert comment.user_id == user.id
    assert comment.target_id == kb.id
    assert comment.target_type == "knowledge"


def test_create_comment_on_persona_card(factory):
    """Test creating a comment on a persona card"""
    persona = factory.create_persona_card()
    user = factory.create_user()
    comment = factory.create_comment(
        user=user,
        target_id=persona.id,
        target_type="persona"
    )
    
    assert comment.user_id == user.id
    assert comment.target_id == persona.id
    assert comment.target_type == "persona"


def test_create_nested_comment(factory):
    """Test creating a nested comment"""
    parent_comment = factory.create_comment()
    child_comment = factory.create_comment(
        parent_id=parent_comment.id,
        target_id=parent_comment.target_id,
        target_type=parent_comment.target_type
    )
    
    assert child_comment.parent_id == parent_comment.id
    assert child_comment.target_id == parent_comment.target_id


def test_create_comment_with_custom_values(factory):
    """Test creating a comment with custom values"""
    comment = factory.create_comment(
        content="Custom comment",
        like_count=5,
        dislike_count=2,
        is_deleted=True
    )
    
    assert comment.content == "Custom comment"
    assert comment.like_count == 5
    assert comment.dislike_count == 2
    assert comment.is_deleted is True


def test_create_knowledge_base_file(factory):
    """Test creating a knowledge base file"""
    kb = factory.create_knowledge_base()
    kb_file = factory.create_knowledge_base_file(
        knowledge_base=kb,
        file_type=".pdf",
        file_size=2048
    )
    
    assert kb_file.id is not None
    assert kb_file.knowledge_base_id == kb.id
    assert kb_file.file_name.endswith(".pdf")
    assert kb_file.file_type == ".pdf"
    assert kb_file.file_size == 2048


def test_create_knowledge_base_file_auto_creates_kb(factory):
    """Test that creating a file auto-creates knowledge base if not provided"""
    kb_file = factory.create_knowledge_base_file()
    
    assert kb_file.knowledge_base_id is not None


def test_create_persona_card_file(factory):
    """Test creating a persona card file"""
    persona = factory.create_persona_card()
    pc_file = factory.create_persona_card_file(
        persona_card=persona,
        file_type=".json",
        file_size=512
    )
    
    assert pc_file.id is not None
    assert pc_file.persona_card_id == persona.id
    assert pc_file.file_name.endswith(".json")
    assert pc_file.file_type == ".json"
    assert pc_file.file_size == 512


def test_create_persona_card_file_auto_creates_persona(factory):
    """Test that creating a file auto-creates persona card if not provided"""
    pc_file = factory.create_persona_card_file()
    
    assert pc_file.persona_card_id is not None


def test_create_star_record_for_knowledge_base(factory):
    """Test creating a star record for a knowledge base"""
    kb = factory.create_knowledge_base()
    user = factory.create_user()
    star = factory.create_star_record(
        user=user,
        target_id=kb.id,
        target_type="knowledge"
    )
    
    assert star.user_id == user.id
    assert star.target_id == kb.id
    assert star.target_type == "knowledge"


def test_create_star_record_for_persona_card(factory):
    """Test creating a star record for a persona card"""
    persona = factory.create_persona_card()
    user = factory.create_user()
    star = factory.create_star_record(
        user=user,
        target_id=persona.id,
        target_type="persona"
    )
    
    assert star.user_id == user.id
    assert star.target_id == persona.id
    assert star.target_type == "persona"


def test_create_star_record_auto_creates_target(factory):
    """Test that creating a star auto-creates target if not provided"""
    star = factory.create_star_record(target_type="knowledge")
    
    assert star.target_id is not None
    assert star.target_type == "knowledge"


def test_create_comment_reaction_like(factory):
    """Test creating a like reaction on a comment"""
    comment = factory.create_comment()
    user = factory.create_user()
    reaction = factory.create_comment_reaction(
        user=user,
        comment=comment,
        reaction_type="like"
    )
    
    assert reaction.user_id == user.id
    assert reaction.comment_id == comment.id
    assert reaction.reaction_type == "like"


def test_create_comment_reaction_dislike(factory):
    """Test creating a dislike reaction on a comment"""
    comment = factory.create_comment()
    user = factory.create_user()
    reaction = factory.create_comment_reaction(
        user=user,
        comment=comment,
        reaction_type="dislike"
    )
    
    assert reaction.user_id == user.id
    assert reaction.comment_id == comment.id
    assert reaction.reaction_type == "dislike"


def test_create_comment_reaction_auto_creates_comment(factory):
    """Test that creating a reaction auto-creates comment if not provided"""
    reaction = factory.create_comment_reaction()
    
    assert reaction.comment_id is not None
    assert reaction.reaction_type == "like"


def test_referential_integrity_user_to_knowledge_base(factory):
    """Test referential integrity between user and knowledge base"""
    user = factory.create_user(username="testowner")
    kb1 = factory.create_knowledge_base(uploader=user, name="KB1")
    kb2 = factory.create_knowledge_base(uploader=user, name="KB2")
    
    # Verify relationships
    assert kb1.uploader_id == user.id
    assert kb2.uploader_id == user.id
    assert kb1.uploader.username == "testowner"
    assert kb2.uploader.username == "testowner"


def test_referential_integrity_user_to_persona_card(factory):
    """Test referential integrity between user and persona card"""
    user = factory.create_user(username="personacreator")
    persona1 = factory.create_persona_card(uploader=user, name="Persona1")
    persona2 = factory.create_persona_card(uploader=user, name="Persona2")
    
    # Verify relationships
    assert persona1.uploader_id == user.id
    assert persona2.uploader_id == user.id
    assert persona1.uploader.username == "personacreator"
    assert persona2.uploader.username == "personacreator"


def test_referential_integrity_message_sender_recipient(factory):
    """Test referential integrity for message sender and recipient"""
    sender = factory.create_user(username="sender")
    recipient = factory.create_user(username="recipient")
    message = factory.create_message(sender=sender, recipient=recipient)
    
    # Verify relationships
    assert message.sender_id == sender.id
    assert message.recipient_id == recipient.id
    assert message.sender.username == "sender"
    assert message.recipient.username == "recipient"


def test_multiple_users_created_with_unique_identifiers(factory):
    """Test that multiple users have unique usernames and emails"""
    user1 = factory.create_user()
    user2 = factory.create_user()
    user3 = factory.create_user()
    
    # Verify uniqueness
    assert user1.username != user2.username
    assert user1.username != user3.username
    assert user2.username != user3.username
    
    assert user1.email != user2.email
    assert user1.email != user3.email
    assert user2.email != user3.email


def test_complex_scenario_with_multiple_entities(factory):
    """Test a complex scenario with multiple related entities"""
    # Create users
    admin = factory.create_user(username="admin", is_admin=True)
    user1 = factory.create_user(username="user1")
    user2 = factory.create_user(username="user2")
    
    # Create knowledge base
    kb = factory.create_knowledge_base(
        uploader=user1,
        name="Test KB",
        is_public=True,
        is_pending=False
    )
    
    # Create files for knowledge base
    file1 = factory.create_knowledge_base_file(knowledge_base=kb, file_type=".pdf")
    file2 = factory.create_knowledge_base_file(knowledge_base=kb, file_type=".txt")
    
    # Create comments
    comment1 = factory.create_comment(user=user2, target_id=kb.id, target_type="knowledge")
    comment2 = factory.create_comment(
        user=user1,
        target_id=kb.id,
        target_type="knowledge",
        parent_id=comment1.id
    )
    
    # Create reactions
    reaction1 = factory.create_comment_reaction(user=user1, comment=comment1, reaction_type="like")
    reaction2 = factory.create_comment_reaction(user=admin, comment=comment1, reaction_type="like")
    
    # Create star
    star = factory.create_star_record(user=user2, target_id=kb.id, target_type="knowledge")
    
    # Create message
    message = factory.create_message(sender=admin, recipient=user1, title="KB Approved")
    
    # Verify all relationships
    assert kb.uploader_id == user1.id
    assert file1.knowledge_base_id == kb.id
    assert file2.knowledge_base_id == kb.id
    assert comment1.target_id == kb.id
    assert comment2.parent_id == comment1.id
    assert reaction1.comment_id == comment1.id
    assert reaction2.comment_id == comment1.id
    assert star.target_id == kb.id
    assert message.sender_id == admin.id
    assert message.recipient_id == user1.id
