# AuthHelper Documentation

## Overview

The `AuthHelper` class provides a convenient way to create authenticated test clients for integration tests. It simplifies the process of testing API endpoints that require authentication with different user roles.

## Features

- Generate authentication headers for any user
- Create authenticated test clients for different user roles:
  - Regular users
  - Admin users
  - Moderator users
  - Super admin users
- Support for both auto-created and existing users
- Easy cleanup of authentication headers

## Usage

### Basic Usage with Fixture

The `auth_helper` fixture is available in all tests via `conftest.py`:

```python
def test_my_endpoint(auth_helper, test_db):
    """Test an endpoint with authenticated user"""
    # Create authenticated user client
    user_client = auth_helper.create_user_client()
    
    # Make authenticated request
    response = user_client.get("/api/users/me")
    assert response.status_code == 200
```

### Creating Different User Roles

```python
def test_admin_endpoint(auth_helper, test_db):
    """Test admin-only endpoint"""
    # Create authenticated admin client
    admin_client = auth_helper.create_admin_client()
    
    response = admin_client.get("/api/admin/stats")
    assert response.status_code == 200

def test_moderator_endpoint(auth_helper, test_db):
    """Test moderator-only endpoint"""
    # Create authenticated moderator client
    moderator_client = auth_helper.create_moderator_client()
    
    response = moderator_client.get("/api/review/knowledge")
    assert response.status_code == 200
```

### Using Existing Users

```python
def test_with_custom_user(auth_helper, test_db, factory):
    """Test with a specific user"""
    # Create a custom user
    user = factory.create_user(
        username="specificuser",
        email="specific@example.com"
    )
    
    # Create authenticated client for this user
    client = auth_helper.create_user_client(user)
    
    response = client.get("/api/users/me")
    assert response.status_code == 200
```

### Getting Auth Headers Only

```python
def test_with_headers(auth_helper, test_db, factory):
    """Test using auth headers directly"""
    user = factory.create_user()
    
    # Get headers without modifying client
    headers = auth_helper.get_auth_headers(user)
    
    # Use headers in request
    response = auth_helper.client.get("/api/users/me", headers=headers)
    assert response.status_code == 200
```

### Clearing Authentication

```python
def test_clear_auth(auth_helper, test_db):
    """Test clearing authentication"""
    # Authenticate
    user_client = auth_helper.create_user_client()
    
    # Make authenticated request
    response = user_client.get("/api/users/me")
    assert response.status_code == 200
    
    # Clear authentication
    auth_helper.clear_auth()
    
    # Request should now fail
    response = auth_helper.client.get("/api/users/me")
    assert response.status_code == 401
```

## API Reference

### `AuthHelper(client: TestClient, db: Session)`

Initialize the AuthHelper with a test client and database session.

### `get_auth_headers(user: User) -> Dict[str, str]`

Generate authentication headers for a user.

**Returns:** Dictionary with `Authorization` header containing JWT token.

### `create_authenticated_client(user: User) -> TestClient`

Create an authenticated test client for a specific user.

**Returns:** TestClient with authentication headers set.

### `create_user_client(user: Optional[User] = None) -> TestClient`

Create an authenticated test client for a regular user.

**Parameters:**
- `user`: Optional existing user (will be created if not provided)

**Returns:** TestClient authenticated as a regular user.

### `create_admin_client(user: Optional[User] = None) -> TestClient`

Create an authenticated test client for an admin user.

**Parameters:**
- `user`: Optional existing user (will be created if not provided)

**Returns:** TestClient authenticated as an admin.

### `create_moderator_client(user: Optional[User] = None) -> TestClient`

Create an authenticated test client for a moderator user.

**Parameters:**
- `user`: Optional existing user (will be created if not provided)

**Returns:** TestClient authenticated as a moderator.

### `create_super_admin_client(user: Optional[User] = None) -> TestClient`

Create an authenticated test client for a super admin user.

**Parameters:**
- `user`: Optional existing user (will be created if not provided)

**Returns:** TestClient authenticated as a super admin.

### `clear_auth() -> None`

Clear authentication headers from the client.

## Requirements Validation

This implementation satisfies **Requirement 11.6**:
- ✅ Provides reusable fixtures for authenticated users
- ✅ Supports different user roles (user, admin, moderator, super_admin)
- ✅ Simplifies authentication in integration tests
- ✅ Generates valid JWT tokens
- ✅ Allows testing with both auto-created and existing users

## Testing

The AuthHelper is tested in:
- `tests/unit/test_auth_helper.py` - Unit tests for all methods
- `tests/integration/test_auth_helper_integration.py` - Integration tests demonstrating real usage

Run tests with:
```bash
pytest tests/unit/test_auth_helper.py tests/integration/test_auth_helper_integration.py -v
```
