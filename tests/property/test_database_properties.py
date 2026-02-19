"""
Property-based tests for database operations

**Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6**
"""

import pytest
from hypothesis import given, settings, strategies as st, assume, HealthCheck
from sqlalchemy.exc import IntegrityError
from app.models.database import User, KnowledgeBase, PersonaCard, Message
from app.core.security import get_password_hash


# Property 8: CRUD operations maintain data integrity
# **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.6**
@pytest.mark.property
@given(
    username=st.text(
        min_size=3,
        max_size=50,
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='_-',
            blacklist_categories=('Cs',)  # Exclude surrogates
        )
    ),
    email=st.emails(),
    password=st.text(
        min_size=8,
        max_size=50,
        alphabet=st.characters(blacklist_characters='\x00', blacklist_categories=('Cs',))
    )
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_user_crud_operations_maintain_integrity(test_db, username, email, password):
    """
    Property 8: CRUD operations maintain data integrity
    
    For any database model and any valid data, the system SHALL support creating the model
    with that data, reading it back with identical values, updating it with new valid data,
    and deleting it such that it no longer exists, with all operations respecting foreign
    key constraints and triggering appropriate constraint violations for invalid data.
    
    **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.6**
    """
    # Ensure username and email are unique for this test
    existing_user = test_db.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first()
    assume(existing_user is None)
    
    # CREATE: Create a new user
    hashed_password = get_password_hash(password)
    new_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        is_active=True,
        is_admin=False
    )
    test_db.add(new_user)
    test_db.commit()
    test_db.refresh(new_user)
    
    # Verify user was created
    assert new_user.id is not None, "User should have an ID after creation"
    created_user_id = new_user.id
    
    # READ: Read the user back from database
    retrieved_user = test_db.query(User).filter(User.id == created_user_id).first()
    assert retrieved_user is not None, "User should be retrievable after creation"
    assert retrieved_user.username == username, "Username should match"
    assert retrieved_user.email == email, "Email should match"
    assert retrieved_user.hashed_password == hashed_password, "Password hash should match"
    assert retrieved_user.is_active == True, "is_active should match"
    assert retrieved_user.is_admin == False, "is_admin should match"
    
    # UPDATE: Update the user
    new_is_admin_value = True
    retrieved_user.is_admin = new_is_admin_value
    test_db.commit()
    test_db.refresh(retrieved_user)
    
    # Verify update
    updated_user = test_db.query(User).filter(User.id == created_user_id).first()
    assert updated_user is not None, "User should still exist after update"
    assert updated_user.is_admin == new_is_admin_value, "is_admin should be updated"
    assert updated_user.username == username, "Username should remain unchanged"
    
    # DELETE: Delete the user
    test_db.delete(updated_user)
    test_db.commit()
    
    # Verify deletion
    deleted_user = test_db.query(User).filter(User.id == created_user_id).first()
    assert deleted_user is None, "User should not exist after deletion"


@pytest.mark.property
@given(
    username1=st.text(min_size=3, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters='_-',
        blacklist_categories=('Cs',)
    )),
    username2=st.text(min_size=3, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters='_-',
        blacklist_categories=('Cs',)
    )),
    email=st.emails()
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_unique_constraint_violations_are_handled(test_db, username1, username2, email):
    """
    Property 8: CRUD operations maintain data integrity (constraint violations)
    
    For any database model, constraint violations SHALL be properly detected and handled.
    
    **Validates: Requirement 8.6**
    """
    # Ensure usernames are different
    assume(username1 != username2)
    
    # Ensure no existing users with these usernames or email
    existing = test_db.query(User).filter(
        (User.username.in_([username1, username2])) | (User.email == email)
    ).first()
    assume(existing is None)
    
    # Create first user
    user1 = User(
        username=username1,
        email=email,
        hashed_password=get_password_hash("password123"),
        is_active=True
    )
    test_db.add(user1)
    test_db.commit()
    
    # Try to create second user with same email (should violate unique constraint)
    user2 = User(
        username=username2,
        email=email,  # Same email as user1
        hashed_password=get_password_hash("password456"),
        is_active=True
    )
    test_db.add(user2)
    
    # Should raise IntegrityError due to unique constraint on email
    with pytest.raises(IntegrityError):
        test_db.commit()
    
    # Rollback the failed transaction
    test_db.rollback()
    
    # Verify first user still exists and second user was not created
    users = test_db.query(User).filter(User.email == email).all()
    assert len(users) == 1, "Only first user should exist"
    assert users[0].username == username1, "First user should be unchanged"
    
    # Clean up
    test_db.delete(user1)
    test_db.commit()


# Property 9: Transaction rollback prevents partial updates
# **Validates: Requirement 8.5**
@pytest.mark.property
@given(
    username=st.text(min_size=3, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters='_-',
        blacklist_categories=('Cs',)
    )),
    email=st.emails(),
    new_username=st.text(min_size=3, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters='_-',
        blacklist_categories=('Cs',)
    ))
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_transaction_rollback_prevents_partial_updates(test_db, username, email, new_username):
    """
    Property 9: Transaction rollback prevents partial updates
    
    For any database transaction that encounters an error, when the error occurs, then all
    changes made within that transaction SHALL be rolled back and the database SHALL remain
    in its pre-transaction state.
    
    **Validates: Requirement 8.5**
    """
    # Ensure usernames are different
    assume(username != new_username)
    
    # Ensure no existing users with these identifiers
    existing = test_db.query(User).filter(
        (User.username.in_([username, new_username])) | (User.email == email)
    ).first()
    assume(existing is None)
    
    # Create initial user
    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash("password123"),
        is_active=True,
        is_admin=False
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    user_id = user.id
    original_username = user.username
    original_is_admin = user.is_admin
    
    # Start a transaction that will fail
    try:
        # Update user
        user.username = new_username
        user.is_admin = True
        test_db.flush()  # Flush changes but don't commit
        
        # Create another user with the original username (will cause conflict after rollback test)
        # Instead, let's create a user with a duplicate email to force an error
        conflicting_user = User(
            username="different_user_" + username,
            email=email,  # Same email - will violate unique constraint
            hashed_password=get_password_hash("password456"),
            is_active=True
        )
        test_db.add(conflicting_user)
        test_db.commit()  # This should fail
        
        # If we get here, the test setup is wrong
        pytest.fail("Expected IntegrityError was not raised")
        
    except IntegrityError:
        # Rollback the transaction
        test_db.rollback()
    
    # Verify the user's state was rolled back to original
    test_db.expire_all()  # Clear the session cache
    rolled_back_user = test_db.query(User).filter(User.id == user_id).first()
    
    assert rolled_back_user is not None, "User should still exist after rollback"
    assert rolled_back_user.username == original_username, \
        "Username should be rolled back to original value"
    assert rolled_back_user.is_admin == original_is_admin, \
        "is_admin should be rolled back to original value"
    
    # Verify no conflicting user was created
    conflicting_users = test_db.query(User).filter(
        User.username.like("different_user_%")
    ).all()
    assert len(conflicting_users) == 0, "Conflicting user should not exist after rollback"
    
    # Clean up
    test_db.delete(rolled_back_user)
    test_db.commit()


@pytest.mark.property
@given(
    name=st.text(min_size=1, max_size=100, alphabet=st.characters(
        blacklist_categories=('Cs',)
    )),
    description=st.text(min_size=1, max_size=500, alphabet=st.characters(
        blacklist_categories=('Cs',)
    ))
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_knowledge_base_crud_operations(test_db, name, description):
    """
    Property 8: CRUD operations maintain data integrity (KnowledgeBase model)
    
    Test CRUD operations on KnowledgeBase model to ensure data integrity.
    
    **Validates: Requirements 8.1, 8.2, 8.3, 8.4**
    """
    # Create a user first (required for foreign key)
    user = User(
        username=f"testuser_{name[:10]}",
        email=f"test_{name[:10]}@example.com",
        hashed_password=get_password_hash("password123"),
        is_active=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    try:
        # CREATE: Create knowledge base
        kb = KnowledgeBase(
            name=name,
            description=description,
            uploader_id=user.id,
            star_count=0
        )
        test_db.add(kb)
        test_db.commit()
        test_db.refresh(kb)
        
        kb_id = kb.id
        assert kb_id is not None, "KnowledgeBase should have an ID"
        
        # READ: Read back
        retrieved_kb = test_db.query(KnowledgeBase).filter(
            KnowledgeBase.id == kb_id
        ).first()
        assert retrieved_kb is not None, "KnowledgeBase should be retrievable"
        assert retrieved_kb.name == name, "Name should match"
        assert retrieved_kb.description == description, "Description should match"
        assert retrieved_kb.uploader_id == user.id, "Uploader ID should match"
        
        # UPDATE: Update knowledge base
        new_star_count = 5
        retrieved_kb.star_count = new_star_count
        test_db.commit()
        
        updated_kb = test_db.query(KnowledgeBase).filter(
            KnowledgeBase.id == kb_id
        ).first()
        assert updated_kb.star_count == new_star_count, "Star count should be updated"
        
        # DELETE: Delete knowledge base
        test_db.delete(updated_kb)
        test_db.commit()
        
        deleted_kb = test_db.query(KnowledgeBase).filter(
            KnowledgeBase.id == kb_id
        ).first()
        assert deleted_kb is None, "KnowledgeBase should not exist after deletion"
        
    finally:
        # Clean up user
        test_db.query(KnowledgeBase).filter(
            KnowledgeBase.uploader_id == user.id
        ).delete()
        test_db.delete(user)
        test_db.commit()


@pytest.mark.property
@given(
    count=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_bulk_operations_maintain_consistency(test_db, count):
    """
    Property 8: CRUD operations maintain data integrity (bulk operations)
    
    Test that bulk create and delete operations maintain database consistency.
    
    **Validates: Requirements 8.1, 8.4**
    """
    created_users = []
    
    try:
        # Bulk CREATE
        for i in range(count):
            user = User(
                username=f"bulkuser_{i}_{count}",
                email=f"bulk_{i}_{count}@example.com",
                hashed_password=get_password_hash("password123"),
                is_active=True
            )
            test_db.add(user)
            created_users.append(user)
        
        test_db.commit()
        
        # Verify all users were created
        for user in created_users:
            test_db.refresh(user)
            assert user.id is not None, "Each user should have an ID"
        
        # Verify count
        retrieved_count = test_db.query(User).filter(
            User.username.like(f"bulkuser_%_{count}")
        ).count()
        assert retrieved_count == count, f"Should have created {count} users"
        
        # Bulk DELETE
        for user in created_users:
            test_db.delete(user)
        test_db.commit()
        
        # Verify all users were deleted
        remaining_count = test_db.query(User).filter(
            User.username.like(f"bulkuser_%_{count}")
        ).count()
        assert remaining_count == 0, "All users should be deleted"
        
    finally:
        # Cleanup in case of failure
        test_db.query(User).filter(
            User.username.like(f"bulkuser_%_{count}")
        ).delete()
        test_db.commit()
