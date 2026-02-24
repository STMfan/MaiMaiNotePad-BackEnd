"""
WebSocket Token验证逻辑测试

测试 app/api/websocket.py 中的token验证逻辑。
覆盖各种token验证场景：过期token、格式错误token、签名错误token等。
"""

import pytest

# Mark all tests in this file as serial to avoid WebSocket connection conflicts
pytestmark = pytest.mark.serial
from datetime import UTC, datetime, timedelta  # noqa: E402

import jwt  # noqa: E402
from starlette.websockets import WebSocketDisconnect  # noqa: E402

from app.core.security import ALGORITHM, SECRET_KEY, create_access_token  # noqa: E402


class TestWebSocketExpiredToken:
    """测试过期token的WebSocket连接被拒绝"""

    def test_expired_token_rejected_with_1008(self, client, test_user):
        """
        测试过期token被拒绝，返回状态码1008

        验证：
        - 使用已过期的JWT token尝试连接
        - 连接应该被服务器拒绝
        - 服务器应该返回WebSocket关闭代码1008（Policy Violation）
        - get_user_from_token应该返回None（因为token已过期）

        覆盖代码：
        - websocket.py 第35-38行（token验证失败路径）
        - security.py get_user_from_token中的过期检查逻辑
        """
        # 创建一个已过期的token（过期时间设置为1秒前）
        expired_token = create_access_token(data={"sub": test_user.id}, expires_delta=timedelta(seconds=-1))

        # 尝试使用过期token建立连接
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/api/ws/{expired_token}"):
                pytest.fail("Connection should have been rejected with expired token")

        # 验证WebSocket关闭代码为1008
        assert exc_info.value.code == 1008, f"Expected close code 1008, got: {exc_info.value.code}"

    def test_token_expired_one_hour_ago(self, client, test_user):
        """
        测试1小时前过期的token被拒绝

        验证：
        - 使用1小时前过期的token
        - 连接应该被拒绝
        - 返回状态码1008
        """
        # 创建1小时前过期的token
        expired_token = create_access_token(data={"sub": test_user.id}, expires_delta=timedelta(hours=-1))

        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/api/ws/{expired_token}"):
                pytest.fail("Connection should have been rejected with expired token")

        assert exc_info.value.code == 1008


class TestWebSocketMalformedToken:
    """测试格式错误的token被拒绝"""

    def test_empty_token_rejected(self, client):
        """
        测试空token被拒绝

        验证：
        - 使用空字符串作为token
        - 连接应该被拒绝
        - 返回WebSocketDisconnect异常（可能是1000或1008）
        """
        empty_token = ""

        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/api/ws/{empty_token}"):
                pytest.fail("Connection should have been rejected with empty token")

        # 空token可能返回1000（正常关闭）或1008（策略违规）
        assert exc_info.value.code in [1000, 1008]

    def test_random_string_token_rejected_with_1008(self, client):
        """
        测试随机字符串token被拒绝

        验证：
        - 使用随机字符串（非JWT格式）作为token
        - 连接应该被拒绝
        - 返回状态码1008
        """
        random_token = "this_is_not_a_valid_jwt_token_at_all"

        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/api/ws/{random_token}"):
                pytest.fail("Connection should have been rejected with random string token")

        assert exc_info.value.code == 1008

    def test_malformed_jwt_structure_rejected_with_1008(self, client):
        """
        测试JWT结构错误的token被拒绝

        验证：
        - 使用JWT格式但结构错误的token（缺少部分）
        - 连接应该被拒绝
        - 返回状态码1008
        """
        # JWT应该有3个部分，用.分隔，这里只提供2个部分
        malformed_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0"

        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/api/ws/{malformed_token}"):
                pytest.fail("Connection should have been rejected with malformed JWT structure")

        assert exc_info.value.code == 1008

    def test_invalid_base64_token_rejected_with_1008(self, client):
        """
        测试Base64编码错误的token被拒绝

        验证：
        - 使用Base64编码错误的token
        - 连接应该被拒绝
        - 返回状态码1008
        """
        # 包含无效Base64字符的token
        invalid_base64_token = "invalid!!!.base64!!!.encoding!!!"

        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/api/ws/{invalid_base64_token}"):
                pytest.fail("Connection should have been rejected with invalid base64 token")

        assert exc_info.value.code == 1008


class TestWebSocketWrongSignature:
    """测试签名错误的token被拒绝"""

    def test_token_with_wrong_secret_rejected_with_1008(self, client, test_user):
        """
        测试使用错误密钥签名的token被拒绝

        验证：
        - 使用不同的密钥签名token
        - 连接应该被拒绝（签名验证失败）
        - 返回状态码1008
        """
        # 使用错误的密钥创建token（至少32字节以避免警告）
        wrong_secret = "wrong_secret_key_for_testing_at_least_32_bytes_long"
        token_data = {"sub": test_user.id, "exp": datetime.now(UTC) + timedelta(minutes=15)}
        wrong_signature_token = jwt.encode(token_data, wrong_secret, algorithm=ALGORITHM)

        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/api/ws/{wrong_signature_token}"):
                pytest.fail("Connection should have been rejected with wrong signature")

        assert exc_info.value.code == 1008

    def test_token_with_modified_payload_rejected_with_1008(self, client, test_user):
        """
        测试payload被篡改的token被拒绝

        验证：
        - 创建有效token后手动修改payload部分
        - 连接应该被拒绝（签名验证失败）
        - 返回状态码1008
        """
        # 创建有效token
        valid_token = create_access_token({"sub": test_user.id})

        # 分解token
        parts = valid_token.split(".")

        # 修改payload部分（改变一个字符）
        if len(parts) == 3:
            # 简单地修改payload的最后一个字符
            modified_payload = parts[1][:-1] + ("a" if parts[1][-1] != "a" else "b")
            tampered_token = f"{parts[0]}.{modified_payload}.{parts[2]}"

            with pytest.raises(WebSocketDisconnect) as exc_info:
                with client.websocket_connect(f"/api/ws/{tampered_token}"):
                    pytest.fail("Connection should have been rejected with tampered payload")

            assert exc_info.value.code == 1008

    def test_token_with_wrong_algorithm_rejected_with_1008(self, client, test_user):
        """
        测试使用错误算法签名的token被拒绝

        验证：
        - 使用不同的算法（如HS384而非HS256）签名token
        - 连接应该被拒绝
        - 返回状态码1008
        """
        # 使用不同的算法创建token
        token_data = {"sub": test_user.id, "exp": datetime.now(UTC) + timedelta(minutes=15)}
        # 使用HS384算法而不是配置的算法
        # HS384 需要至少48字节的密钥，使用一个足够长的测试密钥
        test_secret_for_hs384 = SECRET_KEY + "_extended_to_48_bytes_for_hs384_algorithm"
        wrong_algorithm_token = jwt.encode(token_data, test_secret_for_hs384, algorithm="HS384")

        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/api/ws/{wrong_algorithm_token}"):
                pytest.fail("Connection should have been rejected with wrong algorithm")

        assert exc_info.value.code == 1008


class TestWebSocketTokenMissingClaims:
    """测试缺少必要声明的token被拒绝"""

    def test_token_without_exp_claim_rejected_with_1008(self, client, test_user):
        """
        测试缺少exp声明的token被拒绝

        验证：
        - 创建不包含exp（过期时间）声明的token
        - 连接应该被拒绝
        - 返回状态码1008
        - get_user_from_token应该返回None（因为缺少exp声明）

        覆盖代码：
        - security.py get_user_from_token中的exp检查逻辑
        """
        # 手动创建不包含exp的token
        token_data = {"sub": test_user.id}
        token_without_exp = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/api/ws/{token_without_exp}"):
                pytest.fail("Connection should have been rejected with token missing exp claim")

        assert exc_info.value.code == 1008

    def test_token_with_null_sub_rejected_with_1008(self, client):
        """
        测试sub声明为null的token被拒绝

        验证：
        - 创建sub声明为None的token
        - 连接应该被拒绝
        - 返回状态码1008
        """
        # 创建sub为None的token
        token_data = {"sub": None, "exp": datetime.now(UTC) + timedelta(minutes=15)}
        token_with_null_sub = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/api/ws/{token_with_null_sub}"):
                pytest.fail("Connection should have been rejected with null sub claim")

        assert exc_info.value.code == 1008

    def test_token_with_empty_string_sub_rejected_with_1008(self, client):
        """
        测试sub声明为空字符串的token被拒绝

        验证：
        - 创建sub声明为空字符串的token
        - 连接应该被拒绝
        - 返回状态码1008
        """
        # 创建sub为空字符串的token
        token_data = {"sub": "", "exp": datetime.now(UTC) + timedelta(minutes=15)}
        token_with_empty_sub = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/api/ws/{token_with_empty_sub}"):
                pytest.fail("Connection should have been rejected with empty sub claim")

        assert exc_info.value.code == 1008


class TestWebSocketTokenEdgeCases:
    """测试token验证的边界情况"""

    def test_token_with_special_characters_in_sub(self, client):
        """
        测试sub包含特殊字符的token

        验证：
        - 创建sub包含特殊字符的token
        - token本身是有效的，可以成功连接
        - 连接建立后能正常工作（即使用户不存在）

        注意：这个测试验证token验证逻辑不会因为特殊字符而失败
        """
        # 创建包含特殊字符的sub
        token_data = {"sub": "user@#$%^&*()", "exp": datetime.now(UTC) + timedelta(minutes=15)}
        special_char_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

        # token验证应该成功，能建立连接
        with client.websocket_connect(f"/api/ws/{special_char_token}") as ws:
            # 验证连接成功建立
            assert ws is not None

            # 接收初始消息（即使用户不存在，也会发送消息）
            message = ws.receive_json()
            assert message is not None

    def test_token_with_very_long_sub(self, client):
        """
        测试sub非常长的token

        验证：
        - 创建sub非常长的token
        - token验证应该成功（长度不影响JWT验证）
        - 能够建立连接
        """
        # 创建非常长的sub
        long_sub = "a" * 1000
        token_data = {"sub": long_sub, "exp": datetime.now(UTC) + timedelta(minutes=15)}
        long_sub_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

        # token验证应该成功，能建立连接
        with client.websocket_connect(f"/api/ws/{long_sub_token}") as ws:
            # 验证连接成功建立
            assert ws is not None

            # 接收初始消息
            message = ws.receive_json()
            assert message is not None

    def test_token_expiring_in_one_second(self, client, test_user):
        """
        测试即将过期的token（1秒后过期）

        验证：
        - 创建1秒后过期的token
        - 应该能成功连接（因为还未过期）
        - 能接收到初始消息
        """
        # 创建1秒后过期的token
        almost_expired_token = create_access_token(data={"sub": test_user.id}, expires_delta=timedelta(seconds=1))

        # 应该能成功连接
        with client.websocket_connect(f"/api/ws/{almost_expired_token}") as ws:
            # 验证连接成功
            assert ws is not None

            # 接收初始消息
            message = ws.receive_json()
            assert message is not None
            assert "type" in message

    def test_token_with_extra_claims(self, client, test_user):
        """
        测试包含额外声明的token

        验证：
        - 创建包含额外声明（如role, username等）的token
        - 应该能成功连接（额外声明不影响验证）
        - 能接收到初始消息
        """
        # 创建包含额外声明的token
        token_with_extra_claims = create_access_token(
            {"sub": test_user.id, "username": test_user.username, "role": "user", "custom_field": "custom_value"}
        )

        # 应该能成功连接
        with client.websocket_connect(f"/api/ws/{token_with_extra_claims}") as ws:
            # 验证连接成功
            assert ws is not None

            # 接收初始消息
            message = ws.receive_json()
            assert message is not None
            assert "type" in message
