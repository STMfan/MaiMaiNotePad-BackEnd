"""
内容审核路由集成测试

测试 AI 内容审核 API 的各种场景，包括正常审核、
错误处理、参数验证和健康检查。

需求: 2.2 - AI 内容审核路由集成测试
"""

import json
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient


class TestModerationCheckEndpoint:
    """测试内容审核接口"""

    def test_check_normal_text(self, client: TestClient, monkeypatch):
        """测试审核正常文本"""
        monkeypatch.setenv("SILICONFLOW_API_KEY", "test-api-key")

        # Mock OpenAI 响应
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps({"decision": "true", "confidence": 0.15, "violation_types": []})
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        with patch("app.services.moderation_service.OpenAI") as mock_openai:
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            # 重置服务实例
            import app.services.moderation_service as mod_service

            mod_service._moderation_service = None

            response = client.post(
                "/api/moderation/check",
                json={"text": "这是一条正常的评论", "text_type": "comment"},
                headers={"Cache-Control": "no-cache"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["result"]["decision"] == "true"
        assert data["result"]["confidence"] == 0.15
        assert data["result"]["violation_types"] == []
        assert data["message"] == "审核完成"

    def test_check_violation_text(self, client: TestClient, monkeypatch):
        """测试审核违规文本"""
        monkeypatch.setenv("SILICONFLOW_API_KEY", "test-api-key")

        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps({"decision": "false", "confidence": 0.92, "violation_types": ["abuse"]})
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        with patch("app.services.moderation_service.OpenAI") as mock_openai:
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            import app.services.moderation_service as mod_service

            mod_service._moderation_service = None

            response = client.post(
                "/api/moderation/check",
                json={"text": "违规内容", "text_type": "comment"},
                headers={"Cache-Control": "no-cache"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["result"]["decision"] == "false"
        assert data["result"]["confidence"] == 0.92
        assert "abuse" in data["result"]["violation_types"]

    def test_check_unknown_text(self, client: TestClient, monkeypatch):
        """测试审核不确定文本"""
        monkeypatch.setenv("SILICONFLOW_API_KEY", "test-api-key")

        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps({"decision": "unknown", "confidence": 0.65, "violation_types": ["politics"]})
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        with patch("app.services.moderation_service.OpenAI") as mock_openai:
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            import app.services.moderation_service as mod_service

            mod_service._moderation_service = None

            response = client.post(
                "/api/moderation/check",
                json={"text": "疑似违规内容", "text_type": "post"},
                headers={"Cache-Control": "no-cache"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["result"]["decision"] == "unknown"
        assert data["result"]["confidence"] == 0.65

    def test_check_different_text_types(self, client: TestClient, monkeypatch):
        """测试不同的文本类型"""
        monkeypatch.setenv("SILICONFLOW_API_KEY", "test-api-key")

        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps({"decision": "true", "confidence": 0.1, "violation_types": []})
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        text_types = ["comment", "post", "title", "content"]

        for text_type in text_types:
            with patch("app.services.moderation_service.OpenAI") as mock_openai:
                mock_client = Mock()
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client

                import app.services.moderation_service as mod_service

                mod_service._moderation_service = None

                response = client.post(
                    "/api/moderation/check",
                    json={"text": "测试内容", "text_type": text_type},
                    headers={"Cache-Control": "no-cache"},
                )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_check_default_text_type(self, client: TestClient, monkeypatch):
        """测试默认文本类型"""
        monkeypatch.setenv("SILICONFLOW_API_KEY", "test-api-key")

        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps({"decision": "true", "confidence": 0.1, "violation_types": []})
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        with patch("app.services.moderation_service.OpenAI") as mock_openai:
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            import app.services.moderation_service as mod_service

            mod_service._moderation_service = None

            # 不指定 text_type，应使用默认值 "comment"
            response = client.post(
                "/api/moderation/check", json={"text": "测试内容"}, headers={"Cache-Control": "no-cache"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestModerationCheckValidation:
    """测试请求参数验证"""

    def test_check_missing_text(self, client: TestClient):
        """测试缺少 text 参数"""
        response = client.post(
            "/api/moderation/check", json={"text_type": "comment"}, headers={"Cache-Control": "no-cache"}
        )

        assert response.status_code == 422  # Validation error

    def test_check_empty_text(self, client: TestClient, monkeypatch):
        """测试空文本"""
        monkeypatch.setenv("SILICONFLOW_API_KEY", "test-api-key")

        response = client.post(
            "/api/moderation/check", json={"text": "", "text_type": "comment"}, headers={"Cache-Control": "no-cache"}
        )

        # 空文本应该被 Pydantic 验证拒绝（min_length=1）
        assert response.status_code == 422  # Validation error

    def test_check_invalid_text_type(self, client: TestClient):
        """测试无效的文本类型"""
        response = client.post(
            "/api/moderation/check",
            json={"text": "测试内容", "text_type": "invalid_type"},
            headers={"Cache-Control": "no-cache"},
        )

        assert response.status_code == 422  # Validation error

    def test_check_invalid_json(self, client: TestClient):
        """测试无效的 JSON"""
        response = client.post(
            "/api/moderation/check",
            content="invalid json",  # 使用 content 而不是 data
            headers={"Content-Type": "application/json", "Cache-Control": "no-cache"},
        )

        assert response.status_code == 422


class TestModerationCheckErrors:
    """测试错误处理"""

    def test_check_api_key_not_configured(self, client: TestClient, monkeypatch):
        """测试 API Key 未配置"""
        monkeypatch.delenv("SILICONFLOW_API_KEY", raising=False)

        # 重置服务实例
        import app.services.moderation_service as mod_service

        mod_service._moderation_service = None

        # 由于依赖注入会在路由处理前执行，ValueError 会被 FastAPI 捕获
        # 并转换为 500 错误，但在测试环境中可能会直接抛出异常
        # 我们需要捕获这个异常或者期望 500 错误
        try:
            response = client.post(
                "/api/moderation/check",
                json={"text": "测试内容", "text_type": "comment"},
                headers={"Cache-Control": "no-cache"},
            )
            # 如果没有抛出异常，应该返回 500 错误
            assert response.status_code == 500
            assert "审核服务配置错误" in response.json()["detail"]
        except ValueError as e:
            # 如果抛出了 ValueError，验证错误消息
            assert "未找到 SILICONFLOW_API_KEY" in str(e)

    def test_check_service_exception(self, client: TestClient, monkeypatch):
        """测试服务异常"""
        monkeypatch.setenv("SILICONFLOW_API_KEY", "test-api-key")

        with patch("app.services.moderation_service.OpenAI") as mock_openai:
            mock_client = Mock()
            mock_client.chat.completions.create.side_effect = Exception("API 调用失败")
            mock_openai.return_value = mock_client

            import app.services.moderation_service as mod_service

            mod_service._moderation_service = None

            response = client.post(
                "/api/moderation/check",
                json={"text": "测试内容", "text_type": "comment"},
                headers={"Cache-Control": "no-cache"},
            )

        # 服务层应该捕获异常并返回 unknown 结果
        assert response.status_code == 200
        data = response.json()
        assert data["result"]["decision"] == "unknown"


class TestModerationHealthEndpoint:
    """测试健康检查接口"""

    def test_health_check_success(self, client: TestClient, monkeypatch):
        """测试健康检查成功"""
        monkeypatch.setenv("SILICONFLOW_API_KEY", "test-api-key")

        with patch("app.services.moderation_service.OpenAI"):
            import app.services.moderation_service as mod_service

            mod_service._moderation_service = None

            response = client.get("/api/moderation/health", headers={"Cache-Control": "no-cache"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "healthy"
        assert "model" in data["data"]
        assert "base_url" in data["data"]

    def test_health_check_service_not_configured(self, client: TestClient, monkeypatch):
        """测试服务未配置时的健康检查"""
        monkeypatch.delenv("SILICONFLOW_API_KEY", raising=False)

        import app.services.moderation_service as mod_service

        mod_service._moderation_service = None

        response = client.get("/api/moderation/health", headers={"Cache-Control": "no-cache"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "服务异常" in data["message"]


class TestModerationCaching:
    """测试缓存行为"""

    def test_check_with_cache_control_no_cache(self, client: TestClient, monkeypatch):
        """测试使用 Cache-Control: no-cache 头"""
        monkeypatch.setenv("SILICONFLOW_API_KEY", "test-api-key")

        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps({"decision": "true", "confidence": 0.1, "violation_types": []})
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        with patch("app.services.moderation_service.OpenAI") as mock_openai:
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            import app.services.moderation_service as mod_service

            mod_service._moderation_service = None

            # 第一次请求
            response1 = client.post(
                "/api/moderation/check",
                json={"text": "测试内容", "text_type": "comment"},
                headers={"Cache-Control": "no-cache"},
            )

            # 第二次请求（相同内容）
            response2 = client.post(
                "/api/moderation/check",
                json={"text": "测试内容", "text_type": "comment"},
                headers={"Cache-Control": "no-cache"},
            )

        assert response1.status_code == 200
        assert response2.status_code == 200
        # 两次请求都应该成功


class TestModerationEdgeCases:
    """测试边界情况"""

    def test_check_very_long_text(self, client: TestClient, monkeypatch):
        """测试超长文本"""
        monkeypatch.setenv("SILICONFLOW_API_KEY", "test-api-key")

        long_text = "测试" * 10000  # 20000 字符

        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps({"decision": "true", "confidence": 0.1, "violation_types": []})
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        with patch("app.services.moderation_service.OpenAI") as mock_openai:
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            import app.services.moderation_service as mod_service

            mod_service._moderation_service = None

            response = client.post(
                "/api/moderation/check",
                json={"text": long_text, "text_type": "comment"},
                headers={"Cache-Control": "no-cache"},
            )

        assert response.status_code == 200

    def test_check_special_characters(self, client: TestClient, monkeypatch):
        """测试特殊字符"""
        monkeypatch.setenv("SILICONFLOW_API_KEY", "test-api-key")

        special_text = "测试 @#$%^&*() \n\t\r 特殊字符"

        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps({"decision": "true", "confidence": 0.1, "violation_types": []})
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        with patch("app.services.moderation_service.OpenAI") as mock_openai:
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            import app.services.moderation_service as mod_service

            mod_service._moderation_service = None

            response = client.post(
                "/api/moderation/check",
                json={"text": special_text, "text_type": "comment"},
                headers={"Cache-Control": "no-cache"},
            )

        assert response.status_code == 200

    def test_check_unicode_emoji(self, client: TestClient, monkeypatch):
        """测试 Unicode 和 Emoji"""
        monkeypatch.setenv("SILICONFLOW_API_KEY", "test-api-key")

        unicode_text = "测试 emoji 😀😁😂 和其他字符"

        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps({"decision": "true", "confidence": 0.1, "violation_types": []})
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        with patch("app.services.moderation_service.OpenAI") as mock_openai:
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            import app.services.moderation_service as mod_service

            mod_service._moderation_service = None

            response = client.post(
                "/api/moderation/check",
                json={"text": unicode_text, "text_type": "comment"},
                headers={"Cache-Control": "no-cache"},
            )

        assert response.status_code == 200
