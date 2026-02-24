"""
ModerationService 单元测试

测试 AI 内容审核服务的各种场景，包括正常审核、
异常处理、结果验证和降级策略。

需求: 2.2 - AI 内容审核服务单元测试
"""

import pytest
import json
from unittest.mock import patch, MagicMock, Mock
from app.services.moderation_service import ModerationService, get_moderation_service


class TestModerationServiceInitialization:
    """测试 ModerationService 初始化"""

    def test_init_with_api_key(self):
        """测试使用 API Key 初始化服务"""
        service = ModerationService(api_key="test-api-key")
        
        assert service.api_key == "test-api-key"
        assert service.base_url == "https://api.siliconflow.cn/v1"
        assert service.model == "Qwen/Qwen2.5-7B-Instruct"
        assert service.client is not None

    def test_init_from_env_variable(self, monkeypatch):
        """测试从环境变量读取 API Key"""
        monkeypatch.setenv("SILICONFLOW_API_KEY", "env-api-key")
        
        service = ModerationService()
        
        assert service.api_key == "env-api-key"

    def test_init_without_api_key_raises_error(self, monkeypatch):
        """测试未配置 API Key 时抛出异常"""
        monkeypatch.delenv("SILICONFLOW_API_KEY", raising=False)
        
        with pytest.raises(ValueError, match="未找到 SILICONFLOW_API_KEY"):
            ModerationService()

    def test_init_with_custom_base_url(self):
        """测试使用自定义 API 地址"""
        service = ModerationService(
            api_key="test-api-key",
            base_url="https://custom.api.com/v1"
        )
        
        assert service.base_url == "https://custom.api.com/v1"


class TestModerateMethod:
    """测试 moderate 方法"""

    @pytest.fixture
    def service(self):
        """创建测试用的服务实例"""
        return ModerationService(api_key="test-api-key")

    @pytest.fixture
    def mock_openai_response(self):
        """创建模拟的 OpenAI 响应"""
        def _create_response(content):
            mock_response = Mock()
            mock_choice = Mock()
            mock_message = Mock()
            mock_message.content = content
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]
            return mock_response
        return _create_response

    def test_moderate_normal_text(self, service, mock_openai_response):
        """测试审核正常文本"""
        result_json = json.dumps({
            "decision": "true",
            "confidence": 0.15,
            "violation_types": []
        })
        
        with patch.object(service.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = mock_openai_response(result_json)
            
            result = service.moderate("这是一条正常的评论")
            
            assert result["decision"] == "true"
            assert result["confidence"] == 0.15
            assert result["violation_types"] == []
            
            # 验证调用参数
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["model"] == "Qwen/Qwen2.5-7B-Instruct"
            assert call_kwargs["temperature"] == 0.1
            assert call_kwargs["max_tokens"] == 100

    def test_moderate_violation_text(self, service, mock_openai_response):
        """测试审核违规文本"""
        result_json = json.dumps({
            "decision": "false",
            "confidence": 0.92,
            "violation_types": ["abuse"]
        })
        
        with patch.object(service.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = mock_openai_response(result_json)
            
            result = service.moderate("违规内容")
            
            assert result["decision"] == "false"
            assert result["confidence"] == 0.92
            assert "abuse" in result["violation_types"]

    def test_moderate_unknown_text(self, service, mock_openai_response):
        """测试审核不确定文本"""
        result_json = json.dumps({
            "decision": "unknown",
            "confidence": 0.65,
            "violation_types": ["politics"]
        })
        
        with patch.object(service.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = mock_openai_response(result_json)
            
            result = service.moderate("疑似违规内容")
            
            assert result["decision"] == "unknown"
            assert result["confidence"] == 0.65
            assert "politics" in result["violation_types"]

    def test_moderate_multiple_violations(self, service, mock_openai_response):
        """测试审核包含多种违规类型的文本"""
        result_json = json.dumps({
            "decision": "false",
            "confidence": 0.95,
            "violation_types": ["porn", "abuse"]
        })
        
        with patch.object(service.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = mock_openai_response(result_json)
            
            result = service.moderate("多种违规内容")
            
            assert result["decision"] == "false"
            assert len(result["violation_types"]) == 2
            assert "porn" in result["violation_types"]
            assert "abuse" in result["violation_types"]

    def test_moderate_empty_text(self, service):
        """测试审核空文本"""
        result = service.moderate("")
        
        assert result["decision"] == "true"
        assert result["confidence"] == 0.0
        assert result["violation_types"] == []

    def test_moderate_whitespace_only(self, service):
        """测试审核仅包含空格的文本"""
        result = service.moderate("   \n\t  ")
        
        assert result["decision"] == "true"
        assert result["confidence"] == 0.0
        assert result["violation_types"] == []

    def test_moderate_with_text_type(self, service, mock_openai_response):
        """测试指定文本类型"""
        result_json = json.dumps({
            "decision": "true",
            "confidence": 0.2,
            "violation_types": []
        })
        
        with patch.object(service.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = mock_openai_response(result_json)
            
            service.moderate("测试内容", text_type="post")
            
            # 验证用户消息包含文本类型
            call_kwargs = mock_create.call_args[1]
            messages = call_kwargs["messages"]
            user_message = messages[1]["content"]
            assert "文本类型：post" in user_message

    def test_moderate_with_custom_parameters(self, service, mock_openai_response):
        """测试使用自定义参数"""
        result_json = json.dumps({
            "decision": "true",
            "confidence": 0.1,
            "violation_types": []
        })
        
        with patch.object(service.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = mock_openai_response(result_json)
            
            service.moderate("测试", temperature=0.0, max_tokens=50)
            
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["temperature"] == 0.0
            assert call_kwargs["max_tokens"] == 50


class TestErrorHandling:
    """测试错误处理"""

    @pytest.fixture
    def service(self):
        """创建测试用的服务实例"""
        return ModerationService(api_key="test-api-key")

    def test_moderate_json_parse_error(self, service):
        """测试 JSON 解析失败"""
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "这不是有效的 JSON"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        with patch.object(service.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = mock_response
            
            result = service.moderate("测试文本")
            
            # 应该返回默认的 unknown 结果
            assert result["decision"] == "unknown"
            assert result["confidence"] == 0.5
            assert result["violation_types"] == []

    def test_moderate_invalid_result_format(self, service):
        """测试返回格式不正确"""
        invalid_json = json.dumps({
            "decision": "invalid_value",  # 无效的决策值
            "confidence": 0.5,
            "violation_types": []
        })
        
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = invalid_json
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        with patch.object(service.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = mock_response
            
            result = service.moderate("测试文本")
            
            # 应该返回默认的 unknown 结果
            assert result["decision"] == "unknown"
            assert result["confidence"] == 0.5

    def test_moderate_api_exception(self, service):
        """测试 API 调用异常"""
        with patch.object(service.client.chat.completions, 'create') as mock_create:
            mock_create.side_effect = Exception("API 调用失败")
            
            result = service.moderate("测试文本")
            
            # 应该返回默认的 unknown 结果
            assert result["decision"] == "unknown"
            assert result["confidence"] == 0.5
            assert result["violation_types"] == []

    def test_moderate_missing_fields(self, service):
        """测试返回结果缺少必需字段"""
        incomplete_json = json.dumps({
            "decision": "true"
            # 缺少 confidence 和 violation_types
        })
        
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = incomplete_json
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        with patch.object(service.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = mock_response
            
            result = service.moderate("测试文本")
            
            assert result["decision"] == "unknown"


class TestResultValidation:
    """测试结果验证"""

    @pytest.fixture
    def service(self):
        """创建测试用的服务实例"""
        return ModerationService(api_key="test-api-key")

    def test_validate_result_valid(self, service):
        """测试验证有效结果"""
        valid_result = {
            "decision": "true",
            "confidence": 0.5,
            "violation_types": []
        }
        
        assert service._validate_result(valid_result) is True

    def test_validate_result_invalid_decision(self, service):
        """测试验证无效的决策值"""
        invalid_result = {
            "decision": "maybe",  # 无效值
            "confidence": 0.5,
            "violation_types": []
        }
        
        assert service._validate_result(invalid_result) is False

    def test_validate_result_invalid_confidence(self, service):
        """测试验证无效的置信度"""
        # 置信度超出范围
        invalid_result = {
            "decision": "true",
            "confidence": 1.5,  # 超过 1.0
            "violation_types": []
        }
        
        assert service._validate_result(invalid_result) is False
        
        # 置信度为负数
        invalid_result["confidence"] = -0.1
        assert service._validate_result(invalid_result) is False

    def test_validate_result_invalid_violation_types(self, service):
        """测试验证无效的违规类型"""
        invalid_result = {
            "decision": "false",
            "confidence": 0.9,
            "violation_types": ["invalid_type"]  # 无效的违规类型
        }
        
        assert service._validate_result(invalid_result) is False

    def test_validate_result_not_dict(self, service):
        """测试验证非字典类型"""
        assert service._validate_result("not a dict") is False
        assert service._validate_result([]) is False
        assert service._validate_result(None) is False

    def test_validate_result_missing_fields(self, service):
        """测试验证缺少字段"""
        incomplete_result = {
            "decision": "true",
            "confidence": 0.5
            # 缺少 violation_types
        }
        
        assert service._validate_result(incomplete_result) is False


class TestGetModerationService:
    """测试全局服务实例获取"""

    def test_get_moderation_service_singleton(self, monkeypatch):
        """测试单例模式"""
        monkeypatch.setenv("SILICONFLOW_API_KEY", "test-key")
        
        # 重置全局实例
        import app.services.moderation_service as mod_service
        mod_service._moderation_service = None
        
        service1 = get_moderation_service()
        service2 = get_moderation_service()
        
        # 应该返回同一个实例
        assert service1 is service2

    def test_get_moderation_service_creates_instance(self, monkeypatch):
        """测试首次调用创建实例"""
        monkeypatch.setenv("SILICONFLOW_API_KEY", "test-key")
        
        # 重置全局实例
        import app.services.moderation_service as mod_service
        mod_service._moderation_service = None
        
        service = get_moderation_service()
        
        assert service is not None
        assert isinstance(service, ModerationService)


class TestEdgeCases:
    """测试边界情况"""

    @pytest.fixture
    def service(self):
        """创建测试用的服务实例"""
        return ModerationService(api_key="test-api-key")

    def test_moderate_very_long_text(self, service):
        """测试审核超长文本"""
        long_text = "测试" * 10000  # 20000 字符
        
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps({
            "decision": "true",
            "confidence": 0.2,
            "violation_types": []
        })
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        with patch.object(service.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = mock_response
            
            result = service.moderate(long_text)
            
            assert result["decision"] == "true"

    def test_moderate_special_characters(self, service):
        """测试审核包含特殊字符的文本"""
        special_text = "测试 @#$%^&*() 特殊字符 \n\t\r"
        
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps({
            "decision": "true",
            "confidence": 0.1,
            "violation_types": []
        })
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        with patch.object(service.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = mock_response
            
            result = service.moderate(special_text)
            
            assert result["decision"] == "true"

    def test_moderate_unicode_text(self, service):
        """测试审核 Unicode 文本"""
        unicode_text = "测试 emoji 😀😁😂 和其他 Unicode 字符 ñ ü ö"
        
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps({
            "decision": "true",
            "confidence": 0.1,
            "violation_types": []
        })
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        with patch.object(service.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = mock_response
            
            result = service.moderate(unicode_text)
            
            assert result["decision"] == "true"
