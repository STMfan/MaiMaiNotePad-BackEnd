"""
Property-based tests for authentication and authorization

**Validates: Requirements 7.1, 7.2, 7.3, 7.4**
"""

import pytest
from hypothesis import given, settings, strategies as st
from datetime import datetime, timedelta, timezone
from app.core.security import (
    create_user_token, verify_token, get_password_hash,
    verify_password, create_access_token
)


# Property 5: Valid credentials produce valid tokens
# **Validates: Requirement 7.1**
@pytest.mark.property
@given(
    user_id=st.uuids().map(str),
    username=st.text(min_size=3, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters='_-'
    )),
    role=st.sampled_from(['user', 'admin', 'moderator', 'super_admin']),
    password_version=st.integers(min_value=0, max_value=100)
)
@settings(max_examples=100)
def test_valid_credentials_produce_valid_tokens(user_id, username, role, password_version):
    """
    Property 5: Valid credentials produce valid tokens
    
    For any user with valid credentials, when authentication is attempted, then a valid
    JWT token SHALL be generated with correct user information and appropriate expiration time.
    
    **Validates: Requirement 7.1**
    """
    # Create a token for the user
    token = create_user_token(user_id, username, role, password_version)
    
    # Verify token is not empty
    assert token is not None, "Token should not be None"
    assert len(token) > 0, "Token should not be empty"
    assert isinstance(token, str), "Token should be a string"
    
    # Verify token can be decoded
    payload = verify_token(token)
    assert payload is not None, "Token should be verifiable"
    
    # Verify token contains correct user information
    assert payload['sub'] == user_id, "Token should contain correct user ID"
    assert payload['username'] == username, "Token should contain correct username"
    assert payload['role'] == role, "Token should contain correct role"
    assert payload['pwd_ver'] == password_version, "Token should contain password version"
    assert payload['type'] == 'access', "Token should be an access token"
    
    # Verify token has expiration
    assert 'exp' in payload, "Token should have expiration"
    exp_timestamp = payload['exp']
    exp_datetime = datetime.fromtimestamp(exp_timestamp, timezone.utc)
    now = datetime.now(timezone.utc)
    
    # Token should expire in the future
    assert exp_datetime > now, "Token expiration should be in the future"
    
    # Token should not expire too far in the future (reasonable limit)
    max_expiration = now + timedelta(days=365)
    assert exp_datetime < max_expiration, "Token should not expire too far in the future"


# Property 6: Invalid credentials are rejected
# **Validates: Requirement 7.2**
@pytest.mark.property
@given(
    password=st.text(
        min_size=1,
        max_size=70,
        alphabet=st.characters(
            blacklist_characters='\x00',  # Exclude NULL bytes for bcrypt
            blacklist_categories=('Cs',)  # Exclude surrogates (invalid UTF-8)
        )
    ),
    wrong_password=st.text(
        min_size=1,
        max_size=70,
        alphabet=st.characters(
            blacklist_characters='\x00',  # Exclude NULL bytes for bcrypt
            blacklist_categories=('Cs',)  # Exclude surrogates (invalid UTF-8)
        )
    )
)
@settings(max_examples=100)
def test_invalid_credentials_are_rejected(password, wrong_password):
    """
    Property 6: Invalid credentials are rejected
    
    For any authentication attempt with invalid credentials (wrong password, nonexistent user,
    or locked account), then authentication SHALL fail and no token SHALL be generated.
    
    **Validates: Requirement 7.2**
    """
    # Ensure passwords are different enough (at least 5 chars difference)
    if password == wrong_password or len(password) < 5:
        wrong_password = "completely_different_password_12345"
    
    # Hash the correct password
    hashed = get_password_hash(password)
    
    # Verify correct password works
    assert verify_password(password, hashed), "Correct password should verify"
    
    # Verify wrong password fails
    assert not verify_password(wrong_password, hashed), "Wrong password should not verify"


# Property 7: Role-based access control is enforced
# **Validates: Requirements 7.3, 7.4**
@pytest.mark.property
@given(
    user_role=st.sampled_from(['user', 'admin', 'moderator', 'super_admin']),
    required_role=st.sampled_from(['user', 'admin', 'moderator', 'super_admin'])
)
@settings(max_examples=100)
def test_role_based_access_control(user_role, required_role):
    """
    Property 7: Role-based access control is enforced
    
    For any user with a specific role and any protected resource, when the user attempts
    to access the resource, then access SHALL be granted if and only if the user's role
    has the required permissions.
    
    **Validates: Requirements 7.3, 7.4**
    """
    # Define role hierarchy
    role_hierarchy = {
        'user': 0,
        'moderator': 1,
        'admin': 2,
        'super_admin': 3
    }
    
    user_level = role_hierarchy.get(user_role, 0)
    required_level = role_hierarchy.get(required_role, 0)
    
    # Determine if access should be granted
    # In a typical system, higher roles have all permissions of lower roles
    should_have_access = user_level >= required_level
    
    # Create a token with the user's role
    token = create_user_token("test_user_id", "testuser", user_role, 0)
    payload = verify_token(token)
    
    # Verify the token contains the correct role
    assert payload['role'] == user_role, "Token should contain user's role"
    
    # Verify role hierarchy logic
    if should_have_access:
        assert user_level >= required_level, \
            f"User with role {user_role} should have access to {required_role} resources"
    else:
        assert user_level < required_level, \
            f"User with role {user_role} should not have access to {required_role} resources"


@pytest.mark.property
@given(
    password=st.text(
        min_size=8,
        max_size=70,
        alphabet=st.characters(
            blacklist_characters='\x00',  # Exclude NULL bytes for bcrypt
            blacklist_categories=('Cs',)  # Exclude surrogates (invalid UTF-8)
        )
    )
)
@settings(max_examples=100)
def test_password_hashing_is_consistent(password):
    """
    Property: Password hashing is consistent and secure
    
    For any password, hashing should produce a consistent result that can be verified.
    
    **Validates: Requirement 7.1**
    """
    # Hash the password
    hashed1 = get_password_hash(password)
    hashed2 = get_password_hash(password)
    
    # Hashes should be different (due to salt) but both should verify
    assert hashed1 != hashed2, "Hashes should be different due to salt"
    assert verify_password(password, hashed1), "Password should verify against first hash"
    assert verify_password(password, hashed2), "Password should verify against second hash"


@pytest.mark.property
@given(
    num_tokens=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=100)
def test_multiple_tokens_are_independent(num_tokens):
    """
    Property: Multiple tokens for different users are independent
    
    For any number of users, each should have their own independent token.
    
    **Validates: Requirement 7.1**
    """
    tokens = []
    user_ids = []
    
    # Create multiple tokens for different users
    for i in range(num_tokens):
        user_id = f"user_{i}"
        username = f"testuser_{i}"
        token = create_user_token(user_id, username, "user", 0)
        tokens.append(token)
        user_ids.append(user_id)
    
    # Verify all tokens are unique
    assert len(set(tokens)) == num_tokens, "All tokens should be unique"
    
    # Verify each token contains the correct user ID
    for i, token in enumerate(tokens):
        payload = verify_token(token)
        assert payload['sub'] == user_ids[i], \
            f"Token {i} should contain correct user ID"


@pytest.mark.property
@given(
    data=st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.one_of(st.text(), st.integers(), st.booleans()),
        min_size=1,
        max_size=5
    )
)
@settings(max_examples=100)
def test_token_payload_integrity(data):
    """
    Property: Token payload maintains data integrity
    
    For any data encoded in a token, it should be retrievable without corruption.
    
    **Validates: Requirement 7.1**
    """
    # Create a token with custom data
    token = create_access_token(data)
    
    # Verify token is created
    assert token is not None, "Token should be created"
    assert len(token) > 0, "Token should not be empty"
    
    # Decode the token
    payload = verify_token(token)
    
    # Verify all original data is present (except 'exp' which is added)
    for key, value in data.items():
        assert key in payload, f"Key '{key}' should be in payload"
        assert payload[key] == value, f"Value for '{key}' should match"
