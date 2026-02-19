"""
Integration workflow tests for user registration and login
Tests complete end-to-end user registration and login flow

Example 1: User registration and login flow
Requirements: 9.1
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch

from app.models.database import User, EmailVerification


class TestRegistrationAndLoginWorkflow:
    """Test complete user registration and login workflow"""
    
    @patch('app.services.email_service.EmailService.send_email')
    def test_complete_registration_and_login_flow(self, mock_send_email, test_db: Session):
        """
        Test Example 1: User registration and login flow
        
        Complete workflow:
        1. Send verification code to email
        2. Verify email with code
        3. Register user with verified email
        4. Login with credentials
        5. Receive valid access token
        6. Use token to access protected endpoint
        
        **Validates: Requirements 9.1**
        """
        from app.main import app
        client = TestClient(app)
        
        mock_send_email.return_value = True
        
        # Step 1: Send verification code
        email = "newworkflowuser@example.com"
        username = "workflowuser"
        password = "securepassword123"
        
        send_code_response = client.post(
            "/api/auth/send_verification_code",
            data={"email": email}
        )
        
        assert send_code_response.status_code == 200
        assert "验证码已发送" in send_code_response.json()["message"]
        
        # Step 2: Get verification code from database (simulating user receiving email)
        verification = test_db.query(EmailVerification).filter(
            EmailVerification.email == email,
            EmailVerification.is_used == False
        ).first()
        
        assert verification is not None
        assert len(verification.code) == 6
        assert verification.code.isdigit()
        code = verification.code
        
        # Step 3: Register user with verification code
        register_response = client.post(
            "/api/auth/user/register",
            data={
                "username": username,
                "password": password,
                "email": email,
                "verification_code": code
            }
        )
        
        assert register_response.status_code == 200
        assert "注册成功" in register_response.json()["message"]
        
        # Verify user was created in database
        user = test_db.query(User).filter(User.username == username).first()
        assert user is not None
        assert user.email == email
        assert user.is_active == True
        assert user.is_admin == False
        assert user.is_moderator == False
        assert user.is_super_admin == False
        
        # Verify verification code was marked as used
        test_db.refresh(verification)
        assert verification.is_used == True
        
        # Step 4: Login with registered credentials
        login_response = client.post(
            "/api/auth/token",
            json={"username": username, "password": password}
        )
        
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert "data" in login_data
        assert "access_token" in login_data["data"]
        assert "refresh_token" in login_data["data"]
        assert login_data["data"]["token_type"] == "bearer"
        assert login_data["data"]["user"]["username"] == username
        assert login_data["data"]["user"]["email"] == email
        
        # Step 5: Extract and validate token
        access_token = login_data["data"]["access_token"]
        assert access_token is not None
        assert len(access_token) > 0
        
        # Step 6: Use token to access protected endpoint
        protected_response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert protected_response.status_code == 200
        response_data = protected_response.json()
        assert "data" in response_data
        user_data = response_data["data"]
        assert user_data["username"] == username
        assert user_data["email"] == email
    
    @patch('app.services.email_service.EmailService.send_email')
    def test_registration_flow_with_duplicate_username(self, mock_send_email, test_db: Session):
        """
        Test registration flow fails gracefully with duplicate username
        
        Workflow:
        1. Send verification code
        2. Register first user successfully
        3. Send another verification code
        4. Attempt to register with same username but different email
        5. Verify registration fails with appropriate error
        
        **Validates: Requirements 9.1**
        """
        from app.main import app
        client = TestClient(app)
        
        mock_send_email.return_value = True
        
        # Register first user
        email1 = "first@example.com"
        username = "duplicateuser"
        
        client.post("/api/auth/send_verification_code", data={"email": email1})
        verification1 = test_db.query(EmailVerification).filter(
            EmailVerification.email == email1
        ).first()
        
        client.post(
            "/api/auth/user/register",
            data={
                "username": username,
                "password": "password123",
                "email": email1,
                "verification_code": verification1.code
            }
        )
        
        # Try to register second user with same username
        email2 = "second@example.com"
        client.post("/api/auth/send_verification_code", data={"email": email2})
        verification2 = test_db.query(EmailVerification).filter(
            EmailVerification.email == email2
        ).first()
        
        response = client.post(
            "/api/auth/user/register",
            data={
                "username": username,
                "password": "password456",
                "email": email2,
                "verification_code": verification2.code
            }
        )
        
        assert response.status_code == 422
        assert "用户名已存在" in response.json()["error"]["message"]
    
    @patch('app.services.email_service.EmailService.send_email')
    def test_registration_flow_with_invalid_verification_code(self, mock_send_email, test_db: Session):
        """
        Test registration flow fails with invalid verification code
        
        Workflow:
        1. Send verification code
        2. Attempt to register with wrong code
        3. Verify registration fails
        4. Verify user was not created
        
        **Validates: Requirements 9.1**
        """
        from app.main import app
        client = TestClient(app)
        
        mock_send_email.return_value = True
        
        email = "invalidcode@example.com"
        username = "invalidcodeuser"
        
        # Send verification code
        client.post("/api/auth/send_verification_code", data={"email": email})
        
        # Try to register with wrong code
        response = client.post(
            "/api/auth/user/register",
            data={
                "username": username,
                "password": "password123",
                "email": email,
                "verification_code": "000000"  # Wrong code
            }
        )
        
        assert response.status_code == 422
        assert "验证码错误或已失效" in response.json()["error"]["message"]
        
        # Verify user was not created
        user = test_db.query(User).filter(User.username == username).first()
        assert user is None
    
    def test_login_flow_with_invalid_credentials(self, test_db: Session):
        """
        Test login flow fails with invalid credentials
        
        Workflow:
        1. Create a user directly in database
        2. Attempt to login with wrong password
        3. Verify login fails
        4. Verify failed login attempts are tracked
        
        **Validates: Requirements 9.1**
        """
        from app.main import app
        from app.core.security import get_password_hash
        import uuid
        
        client = TestClient(app)
        
        # Create user directly
        user = User(
            id=str(uuid.uuid4()),
            username="logintest",
            email="logintest@example.com",
            hashed_password=get_password_hash("correctpassword"),
            is_active=True,
            is_admin=False,
            is_moderator=False,
            is_super_admin=False,
            created_at=datetime.now(),
            password_version=0,
            failed_login_attempts=0
        )
        test_db.add(user)
        test_db.commit()
        
        # Attempt login with wrong password
        response = client.post(
            "/api/auth/token",
            json={"username": "logintest", "password": "wrongpassword"}
        )
        
        assert response.status_code == 401
        assert "用户名或密码错误" in response.json()["error"]["message"]
        
        # Verify failed login attempts incremented
        test_db.refresh(user)
        assert user.failed_login_attempts == 1
    
    @patch('app.services.email_service.EmailService.send_email')
    def test_complete_flow_with_token_refresh(self, mock_send_email, test_db: Session):
        """
        Test complete registration, login, and token refresh flow
        
        Workflow:
        1. Register user
        2. Login to get tokens
        3. Use refresh token to get new access token
        4. Use new access token to access protected endpoint
        
        **Validates: Requirements 9.1**
        """
        from app.main import app
        client = TestClient(app)
        
        mock_send_email.return_value = True
        
        # Register user
        email = "refreshflow@example.com"
        username = "refreshflowuser"
        password = "password123"
        
        client.post("/api/auth/send_verification_code", data={"email": email})
        verification = test_db.query(EmailVerification).filter(
            EmailVerification.email == email
        ).first()
        
        client.post(
            "/api/auth/user/register",
            data={
                "username": username,
                "password": password,
                "email": email,
                "verification_code": verification.code
            }
        )
        
        # Login
        login_response = client.post(
            "/api/auth/token",
            json={"username": username, "password": password}
        )
        
        assert login_response.status_code == 200
        tokens = login_response.json()["data"]
        refresh_token = tokens["refresh_token"]
        
        # Refresh token
        refresh_response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert refresh_response.status_code == 200
        new_access_token = refresh_response.json()["data"]["access_token"]
        
        # Use new token
        protected_response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {new_access_token}"}
        )
        
        assert protected_response.status_code == 200
        response_data = protected_response.json()
        assert "data" in response_data
        assert response_data["data"]["username"] == username
    
    @patch('app.services.email_service.EmailService.send_email')
    def test_registration_flow_email_case_insensitive(self, mock_send_email, test_db: Session):
        """
        Test registration flow handles email case insensitivity
        
        Workflow:
        1. Send verification code with uppercase email
        2. Register with lowercase email
        3. Verify registration succeeds
        4. Login and verify user data
        
        **Validates: Requirements 9.1**
        """
        from app.main import app
        client = TestClient(app)
        
        mock_send_email.return_value = True
        
        # Send code with uppercase
        email_upper = "CASETEST@EXAMPLE.COM"
        email_lower = "casetest@example.com"
        username = "casetest"
        password = "password123"
        
        client.post("/api/auth/send_verification_code", data={"email": email_upper})
        
        # Get verification (should be stored as lowercase)
        verification = test_db.query(EmailVerification).filter(
            EmailVerification.email == email_lower
        ).first()
        
        assert verification is not None
        
        # Register with lowercase
        register_response = client.post(
            "/api/auth/user/register",
            data={
                "username": username,
                "password": password,
                "email": email_lower,
                "verification_code": verification.code
            }
        )
        
        assert register_response.status_code == 200
        
        # Login and verify
        login_response = client.post(
            "/api/auth/token",
            json={"username": username, "password": password}
        )
        
        assert login_response.status_code == 200
        assert login_response.json()["data"]["user"]["email"] == email_lower
