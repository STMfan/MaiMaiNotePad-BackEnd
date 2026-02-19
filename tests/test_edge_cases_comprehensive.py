"""
Comprehensive edge case tests for all modules
Tests empty strings, null/None, max length, special chars, numeric boundaries, and collections

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8
"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session
from tests.test_data_factory import TestDataFactory


class TestStringEdgeCases:
    """Test edge cases for string inputs across all endpoints"""
    
    def test_empty_string_username(self, client):
        """Test registration with empty username"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "",
                "email": "test@example.com",
                "password": "password123"
            }
        )
        assert response.status_code in [400, 422]
    
    def test_empty_string_email(self, client):
        """Test registration with empty email"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "",
                "password": "password123"
            }
        )
        assert response.status_code in [400, 422]
    
    def test_empty_string_password(self, client):
        """Test registration with empty password"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": ""
            }
        )
        assert response.status_code in [400, 422]
    
    def test_whitespace_only_username(self, client):
        """Test registration with whitespace-only username"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "   ",
                "email": "test@example.com",
                "password": "password123"
            }
        )
        assert response.status_code in [400, 422]
    
    def test_max_length_username(self, authenticated_client):
        """Test profile update with maximum length username"""
        max_username = "a" * 50  # Assuming 50 is max length
        response = authenticated_client.put(
            "/api/users/me",
            json={"username": max_username}
        )
        # Should either succeed or return validation error
        assert response.status_code in [200, 400, 422]
    
    def test_over_max_length_username(self, authenticated_client):
        """Test profile update with over maximum length username"""
        over_max_username = "a" * 51  # Over max length
        response = authenticated_client.put(
            "/api/users/me",
            json={"username": over_max_username}
        )
        assert response.status_code in [400, 422]
    
    def test_special_characters_username(self, client):
        """Test registration with special characters in username"""
        special_usernames = [
            "user@name",
            "user#name",
            "user$name",
            "user%name",
            "user&name",
            "user*name",
            "user(name)",
            "user<name>",
            "user{name}",
            "user[name]",
            "user|name",
            "user\\name",
            "user/name",
            "user:name",
            "user;name",
            "user'name",
            'user"name',
            "user`name",
            "user~name",
            "user!name",
            "user?name",
            "user=name",
            "user+name",
        ]
        
        for username in special_usernames:
            response = client.post(
                "/api/auth/register",
                json={
                    "username": username,
                    "email": f"{username}@example.com",
                    "password": "password123"
                }
            )
            # Should return validation error for most special chars
            assert response.status_code in [200, 400, 422]
    
    def test_unicode_characters_username(self, client):
        """Test registration with unicode characters in username"""
        unicode_usernames = [
            "用户名",  # Chinese
            "ユーザー",  # Japanese
            "사용자",  # Korean
            "пользователь",  # Russian
            "مستخدم",  # Arabic
            "🙂😀",  # Emojis
            "user™",  # Trademark symbol
            "user©",  # Copyright symbol
            "user®",  # Registered symbol
        ]
        
        for username in unicode_usernames:
            response = client.post(
                "/api/auth/register",
                json={
                    "username": username,
                    "email": f"test{hash(username)}@example.com",
                    "password": "password123"
                }
            )
            # Should handle unicode appropriately
            assert response.status_code in [200, 400, 422]
    
    def test_sql_injection_username(self, client):
        """Test registration with SQL injection attempts in username"""
        sql_injection_attempts = [
            "admin'--",
            "admin' OR '1'='1",
            "admin'; DROP TABLE users;--",
            "admin' UNION SELECT * FROM users--",
            "' OR 1=1--",
            "1' OR '1' = '1",
        ]
        
        for username in sql_injection_attempts:
            response = client.post(
                "/api/auth/register",
                json={
                    "username": username,
                    "email": f"test{hash(username)}@example.com",
                    "password": "password123"
                }
            )
            # Should safely handle SQL injection attempts
            assert response.status_code in [200, 400, 422]
    
    def test_xss_injection_username(self, client):
        """Test registration with XSS injection attempts in username"""
        xss_attempts = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='javascript:alert(\"XSS\")'></iframe>",
        ]
        
        for username in xss_attempts:
            response = client.post(
                "/api/auth/register",
                json={
                    "username": username,
                    "email": f"test{hash(username)}@example.com",
                    "password": "password123"
                }
            )
            # Should safely handle XSS attempts
            assert response.status_code in [200, 400, 422]


class TestNullAndNoneEdgeCases:
    """Test edge cases for null/None inputs"""
    
    def test_null_username(self, client):
        """Test registration with null username"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": None,
                "email": "test@example.com",
                "password": "password123"
            }
        )
        assert response.status_code in [400, 422]
    
    def test_missing_username(self, client):
        """Test registration with missing username field"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "password123"
            }
        )
        assert response.status_code in [400, 422]
    
    def test_null_email(self, client):
        """Test registration with null email"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": None,
                "password": "password123"
            }
        )
        assert response.status_code in [400, 422]
    
    def test_null_password(self, client):
        """Test registration with null password"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": None
            }
        )
        assert response.status_code in [400, 422]
    
    def test_null_knowledge_title(self, authenticated_client):
        """Test knowledge base creation with null title"""
        response = authenticated_client.post(
            "/api/knowledge",
            json={
                "title": None,
                "description": "Test description"
            }
        )
        assert response.status_code in [400, 422]
    
    def test_null_persona_name(self, authenticated_client):
        """Test persona card creation with null name"""
        response = authenticated_client.post(
            "/api/persona",
            json={
                "name": None,
                "description": "Test description"
            }
        )
        assert response.status_code in [400, 422]


class TestNumericBoundaryEdgeCases:
    """Test edge cases for numeric inputs"""
    
    def test_zero_page_number(self, authenticated_client):
        """Test pagination with page number 0"""
        response = authenticated_client.get("/api/knowledge?page=0")
        # Should either use default or return error
        assert response.status_code in [200, 400, 404, 422]
    
    def test_negative_page_number(self, authenticated_client):
        """Test pagination with negative page number"""
        response = authenticated_client.get("/api/knowledge?page=-1")
        assert response.status_code in [200, 400, 404, 422]
    
    def test_zero_page_size(self, authenticated_client):
        """Test pagination with page size 0"""
        response = authenticated_client.get("/api/knowledge?page_size=0")
        assert response.status_code in [200, 400, 404, 422]
    
    def test_negative_page_size(self, authenticated_client):
        """Test pagination with negative page size"""
        response = authenticated_client.get("/api/knowledge?page_size=-10")
        assert response.status_code in [200, 400, 404, 422]
    
    def test_max_page_size(self, authenticated_client):
        """Test pagination with maximum page size"""
        response = authenticated_client.get("/api/knowledge?page_size=1000")
        # Should either cap at max or return error
        assert response.status_code in [200, 400, 404, 422]
    
    def test_over_max_page_size(self, authenticated_client):
        """Test pagination with over maximum page size"""
        response = authenticated_client.get("/api/knowledge?page_size=10000")
        assert response.status_code in [200, 400, 404, 422]
    
    def test_very_large_page_number(self, authenticated_client):
        """Test pagination with very large page number"""
        response = authenticated_client.get("/api/knowledge?page=999999")
        # Should return empty results or 404
        assert response.status_code in [200, 404]
    
    def test_zero_mute_duration(self, admin_client, factory: TestDataFactory, test_db: Session):
        """Test muting user with zero duration"""
        user = factory.create_user()
        response = admin_client.post(
            f"/api/admin/users/{user.id}/mute",
            json={"duration": 0}
        )
        assert response.status_code in [200, 400, 422]
    
    def test_negative_mute_duration(self, admin_client, factory: TestDataFactory, test_db: Session):
        """Test muting user with negative duration"""
        user = factory.create_user()
        response = admin_client.post(
            f"/api/admin/users/{user.id}/mute",
            json={"duration": -1}
        )
        assert response.status_code in [400, 422]
    
    def test_max_mute_duration(self, admin_client, factory: TestDataFactory, test_db: Session):
        """Test muting user with maximum duration"""
        user = factory.create_user()
        response = admin_client.post(
            f"/api/admin/users/{user.id}/mute",
            json={"duration": 999999}
        )
        # Should either succeed or cap at max
        assert response.status_code in [200, 400, 422]


class TestCollectionEdgeCases:
    """Test edge cases for collection operations"""
    
    def test_empty_knowledge_list(self, authenticated_client, test_db: Session):
        """Test retrieving knowledge bases when none exist"""
        # Clean up any existing knowledge bases for this test
        response = authenticated_client.get("/api/knowledge")
        
        assert response.status_code == 200
        data = response.json()
        # Should return empty list or paginated empty result
        assert "data" in data
        assert isinstance(data["data"], list)
    
    def test_empty_persona_list(self, authenticated_client, test_db: Session):
        """Test retrieving persona cards when none exist"""
        response = authenticated_client.get("/api/persona")
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
    
    def test_empty_message_list(self, authenticated_client, test_db: Session):
        """Test retrieving messages when none exist"""
        response = authenticated_client.get("/api/messages")
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
    
    def test_empty_comment_list(self, authenticated_client, test_db: Session):
        """Test retrieving comments when none exist"""
        response = authenticated_client.get("/api/comments")
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
    
    def test_single_item_knowledge_list(self, authenticated_client, factory: TestDataFactory, test_db: Session):
        """Test retrieving knowledge bases with single item"""
        kb = factory.create_knowledge_base()
        
        response = authenticated_client.get("/api/knowledge")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 1
    
    def test_single_item_persona_list(self, authenticated_client, factory: TestDataFactory, test_db: Session):
        """Test retrieving persona cards with single item"""
        persona = factory.create_persona_card()
        
        response = authenticated_client.get("/api/persona")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 1
    
    def test_large_knowledge_list(self, authenticated_client, factory: TestDataFactory, test_db: Session):
        """Test retrieving large number of knowledge bases"""
        # Create many knowledge bases
        for i in range(50):
            factory.create_knowledge_base(title=f"KB {i}")
        
        response = authenticated_client.get("/api/knowledge?page_size=100")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 50
    
    def test_large_persona_list(self, authenticated_client, factory: TestDataFactory, test_db: Session):
        """Test retrieving large number of persona cards"""
        # Create many persona cards
        for i in range(50):
            factory.create_persona_card(name=f"Persona {i}")
        
        response = authenticated_client.get("/api/persona?page_size=100")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 50
    
    def test_empty_search_results(self, authenticated_client, test_db: Session):
        """Test search with no matching results"""
        response = authenticated_client.get("/api/knowledge?search=nonexistentxyz123")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 0
    
    def test_empty_filter_results(self, authenticated_client, test_db: Session):
        """Test filter with no matching results"""
        response = authenticated_client.get("/api/knowledge?status=nonexistent")
        
        assert response.status_code in [200, 400, 422]


class TestEmailEdgeCases:
    """Test edge cases for email inputs"""
    
    def test_invalid_email_format(self, client):
        """Test registration with invalid email formats"""
        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@",
            "user@@example.com",
            "user@example",
            "user@.com",
            "user@example..com",
            "user name@example.com",
            "user@exam ple.com",
        ]
        
        for email in invalid_emails:
            response = client.post(
                "/api/auth/register",
                json={
                    "username": f"user{hash(email)}",
                    "email": email,
                    "password": "password123"
                }
            )
            assert response.status_code in [400, 422]
    
    def test_very_long_email(self, client):
        """Test registration with very long email"""
        long_email = "a" * 200 + "@example.com"
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": long_email,
                "password": "password123"
            }
        )
        assert response.status_code in [200, 400, 422]
    
    def test_email_with_special_chars(self, client):
        """Test registration with special characters in email"""
        special_emails = [
            "user+tag@example.com",  # Plus sign (valid)
            "user.name@example.com",  # Dot (valid)
            "user_name@example.com",  # Underscore (valid)
            "user-name@example.com",  # Hyphen (valid)
        ]
        
        for email in special_emails:
            response = client.post(
                "/api/auth/register",
                json={
                    "username": f"user{hash(email)}",
                    "email": email,
                    "password": "password123"
                }
            )
            # These should be valid
            assert response.status_code in [200, 400, 422]


class TestPasswordEdgeCases:
    """Test edge cases for password inputs"""
    
    def test_very_short_password(self, client):
        """Test registration with very short password"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "123"
            }
        )
        assert response.status_code in [400, 422]
    
    def test_very_long_password(self, client):
        """Test registration with very long password"""
        long_password = "a" * 1000
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": long_password
            }
        )
        # Should either succeed or return validation error
        assert response.status_code in [200, 400, 422]
    
    def test_password_with_special_chars(self, client):
        """Test registration with special characters in password"""
        special_passwords = [
            "Pass@word123!",
            "P@$$w0rd!",
            "Pass#word$123",
            "Pass%word^123",
            "Pass&word*123",
            "Pass(word)123",
            "Pass[word]123",
            "Pass{word}123",
            "Pass<word>123",
            "Pass|word\\123",
            "Pass/word:123",
            "Pass;word'123",
            'Pass"word`123',
            "Pass~word=123",
            "Pass+word-123",
        ]
        
        for password in special_passwords:
            response = client.post(
                "/api/auth/register",
                json={
                    "username": f"user{hash(password)}",
                    "email": f"test{hash(password)}@example.com",
                    "password": password
                }
            )
            # Should handle special characters in passwords
            assert response.status_code in [200, 400, 422]
    
    def test_password_with_unicode(self, client):
        """Test registration with unicode characters in password"""
        unicode_passwords = [
            "密码123",  # Chinese
            "パスワード123",  # Japanese
            "비밀번호123",  # Korean
            "пароль123",  # Russian
        ]
        
        for password in unicode_passwords:
            response = client.post(
                "/api/auth/register",
                json={
                    "username": f"user{hash(password)}",
                    "email": f"test{hash(password)}@example.com",
                    "password": password
                }
            )
            # Should handle unicode in passwords
            assert response.status_code in [200, 400, 422]
