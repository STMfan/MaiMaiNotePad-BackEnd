"""
认证路由一致性的属性测试

测试所有认证相关端点应该满足的通用属性。

**验证: 需求 3.8**
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestAuthenticationConsistency:
    """测试属性 1: 认证检查一致性

    **Property 1: Authentication Check Consistency**
    对于任何需要认证的端点，当在没有认证的情况下访问时，
    应该返回 401 状态码和认证错误消息。

    **Validates: Requirements 3.8**
    """

    # Define a subset of endpoints that definitely require authentication
    # These are verified to exist and require Depends(get_current_user)
    AUTHENTICATED_ENDPOINTS = [
        # Admin routes (require authentication)
        ("GET", "/api/admin/stats"),
        ("GET", "/api/admin/users"),
        # Knowledge routes (require authentication)
        ("POST", "/api/knowledge/upload"),
        ("PUT", "/api/knowledge/00000000-0000-0000-0000-000000000001"),
        ("DELETE", "/api/knowledge/00000000-0000-0000-0000-000000000001"),
        ("POST", "/api/knowledge/00000000-0000-0000-0000-000000000001/star"),
        ("DELETE", "/api/knowledge/00000000-0000-0000-0000-000000000001/star"),
        ("GET", "/api/knowledge/00000000-0000-0000-0000-000000000001/download"),
        ("GET", "/api/knowledge/00000000-0000-0000-0000-000000000001/starred"),
        # Persona routes (require authentication)
        ("POST", "/api/persona/upload"),
        ("DELETE", "/api/persona/00000000-0000-0000-0000-000000000002"),
        # Note: /download endpoint allows public access for public persona cards
    ]

    @pytest.mark.parametrize("method,endpoint", AUTHENTICATED_ENDPOINTS)
    def test_unauthenticated_access_returns_401(self, method: str, endpoint: str, test_db: Session):
        """
        测试在没有凭证的情况下访问认证端点返回 401。

        这是一个确定性测试，验证每个已知的认证端点
        在没有认证的情况下访问时返回 401。

        **Validates: Requirements 3.8**
        """
        from app.main import app

        client = TestClient(app)

        # Make request without authentication
        if method == "GET":
            response = client.get(endpoint)
        elif method == "POST":
            response = client.post(endpoint, json={})
        elif method == "PUT":
            response = client.put(endpoint, json={})
        elif method == "DELETE":
            response = client.delete(endpoint)
        else:
            pytest.skip(f"Unsupported HTTP method: {method}")

        # Verify 401 status code
        assert response.status_code == 401, (
            f"Expected 401 for unauthenticated {method} {endpoint}, " f"got {response.status_code}: {response.text}"
        )

        # Verify error response format
        data = response.json()
        assert "error" in data or "detail" in data, f"Expected error response for {method} {endpoint}, got: {data}"

        # Verify error message contains authentication-related keywords
        error_message = ""
        if "error" in data:
            error_message = data["error"].get("message", "").lower()
        elif "detail" in data:
            error_message = str(data["detail"]).lower()

        # Check for authentication-related keywords
        auth_keywords = [
            "认证",
            "授权",
            "token",
            "credential",
            "unauthorized",
            "authentication",
            "authenticated",
            "not authenticated",
        ]
        has_auth_keyword = any(keyword in error_message for keyword in auth_keywords)

        assert has_auth_keyword, (
            f"Expected authentication error message for {method} {endpoint}, " f"got: {error_message}"
        )

    @given(
        invalid_token=st.one_of(
            st.just(""),
            st.just("invalid"),
            st.just("Bearer"),
            st.just("Bearer "),
            st.text(alphabet=st.characters(min_codepoint=33, max_codepoint=126), min_size=1, max_size=50).filter(
                lambda x: not x.startswith("eyJ")
            ),
            st.from_regex(r"[a-zA-Z0-9]{10,100}", fullmatch=True),
        )
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_invalid_token_returns_401(self, invalid_token: str, test_db: Session):
        """
        属性测试：任何无效的认证令牌都应导致 401 响应。

        这个基于属性的测试生成各种无效的令牌格式并验证
        它们都导致 401 未授权响应。

        **Validates: Requirements 3.8**
        """
        from app.main import app

        client = TestClient(app)

        # Skip empty strings as they're handled by the no-auth case
        assume(invalid_token.strip() != "")

        # Test with a sample authenticated endpoint
        headers = {"Authorization": invalid_token}

        # Try accessing an authenticated endpoint
        response = client.get("/api/admin/stats", headers=headers)

        # Should return 401 for invalid token
        assert response.status_code == 401, (
            f"Expected 401 for invalid token '{invalid_token[:20]}...', " f"got {response.status_code}"
        )

        # Verify error response exists
        data = response.json()
        assert "error" in data or "detail" in data, f"Expected error response for invalid token, got: {data}"

    @given(
        malformed_bearer=st.one_of(
            st.just("bearer token"),  # lowercase bearer
            st.just("BEARER token"),  # uppercase bearer
            st.just("Token abc123"),  # wrong prefix
            st.just("Auth abc123"),  # wrong prefix
            st.from_regex(r"Bearer [a-zA-Z0-9]{5,20}", fullmatch=True),  # short tokens with space
        )
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_malformed_bearer_token_returns_401(self, malformed_bearer: str, test_db: Session):
        """
        属性测试：格式错误的 Bearer 令牌应导致 401 响应。

        测试各种格式错误的 Bearer 令牌格式以确保一致的
        认证失败处理。

        **Validates: Requirements 3.8**
        """
        from app.main import app

        client = TestClient(app)

        headers = {"Authorization": malformed_bearer}

        # Try accessing an authenticated endpoint
        response = client.get("/api/admin/users", headers=headers)

        # Should return 401 for malformed bearer token
        assert response.status_code == 401, (
            f"Expected 401 for malformed bearer '{malformed_bearer[:30]}...', " f"got {response.status_code}"
        )

    def test_expired_token_returns_401(self, test_db: Session):
        """
        测试过期的令牌导致 401 响应。

        此测试验证具有过期时间戳的令牌被拒绝。

        **Validates: Requirements 3.8**
        """
        from app.main import app
        from app.core.security import create_access_token
        from datetime import timedelta
        import jwt

        client = TestClient(app)

        # Create an expired token (expired 1 hour ago)
        expired_token = create_access_token(
            data={"sub": "test_user_id", "username": "testuser", "role": "user"}, expires_delta=timedelta(hours=-1)
        )

        headers = {"Authorization": f"Bearer {expired_token}"}

        # Try accessing an authenticated endpoint
        response = client.get("/api/admin/stats", headers=headers)

        # Should return 401 for expired token
        assert response.status_code == 401, f"Expected 401 for expired token, got {response.status_code}"

        # Verify error response
        data = response.json()
        assert "error" in data or "detail" in data

    def test_token_with_missing_claims_returns_401(self, test_db: Session):
        """
        测试缺少必需声明的令牌导致 401 响应。

        **Validates: Requirements 3.8**
        """
        from app.main import app
        from app.core.security import create_access_token
        import jwt

        client = TestClient(app)

        # Create token with missing 'sub' claim
        incomplete_token = create_access_token(
            data={"username": "testuser", "role": "user"}
            # Missing 'sub' claim
        )

        headers = {"Authorization": f"Bearer {incomplete_token}"}

        # Try accessing an authenticated endpoint
        response = client.get("/api/admin/users", headers=headers)

        # Should return 401 for incomplete token
        assert response.status_code == 401, f"Expected 401 for token with missing claims, got {response.status_code}"

    @given(
        method=st.sampled_from(["GET", "POST", "PUT", "DELETE"]),
        path_suffix=st.from_regex(r"[a-z0-9\-]{1,20}", fullmatch=True),
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_random_authenticated_paths_without_auth_return_401_or_404(
        self, method: str, path_suffix: str, test_db: Session
    ):
        """
        属性测试：认证路由下的随机路径应返回 401 或 404。

        此测试生成随机路径后缀并验证访问它们
        在没有认证的情况下返回 401（如果端点存在并需要认证）
        或 404（如果端点不存在）。

        **Validates: Requirements 3.8**
        """
        from app.main import app

        client = TestClient(app)

        # Test paths under authenticated route prefixes
        base_paths = ["/api/knowledge/", "/api/persona/", "/api/messages/", "/api/admin/"]

        for base_path in base_paths:
            test_path = f"{base_path}{path_suffix}"

            # Make request without authentication
            if method == "GET":
                response = client.get(test_path)
            elif method == "POST":
                response = client.post(test_path, json={})
            elif method == "PUT":
                response = client.put(test_path, json={})
            elif method == "DELETE":
                response = client.delete(test_path)

            # Should return either 401 (authenticated endpoint) or 404 (not found)
            # or 405 (method not allowed) or 422 (validation error)
            assert response.status_code in [401, 404, 405, 422], (
                f"Expected 401/404/405/422 for {method} {test_path}, " f"got {response.status_code}"
            )

            # If it's 401, verify it's an authentication error
            if response.status_code == 401:
                data = response.json()
                assert "error" in data or "detail" in data, f"Expected error response for {method} {test_path}"
