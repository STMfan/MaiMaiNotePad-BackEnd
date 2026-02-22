"""
测试数据生成器
提供生成各种测试数据的辅助方法
"""

import uuid
import io
from typing import Optional


class TestDataGenerator:
    """测试数据生成器"""

    @staticmethod
    def generate_valid_user_data():
        """生成有效的用户数据"""
        unique_id = uuid.uuid4().hex[:8]
        return {"username": f"user_{unique_id}", "email": f"test_{unique_id}@example.com", "password": "Test123!@#"}

    @staticmethod
    def generate_invalid_user_data(invalid_field: str):
        """
        生成包含无效字段的用户数据

        Args:
            invalid_field: 要设置为无效的字段名（username, email, password）
        """
        data = TestDataGenerator.generate_valid_user_data()

        if invalid_field == "username":
            data["username"] = ""
        elif invalid_field == "email":
            data["email"] = "invalid-email"
        elif invalid_field == "password":
            data["password"] = "123"  # 太短

        return data

    @staticmethod
    def generate_test_file(
        filename: str = "test.txt", content: bytes = b"test content", content_type: str = "text/plain"
    ):
        """
        生成测试文件

        Args:
            filename: 文件名
            content: 文件内容
            content_type: 文件 MIME 类型

        Returns:
            tuple: (filename, file_object, content_type)
        """
        return (filename, io.BytesIO(content), content_type)

    @staticmethod
    def generate_toml_file(version: str = "1.0.0", additional_content: Optional[str] = None):
        """
        生成有效的 TOML 配置文件

        Args:
            version: 版本号
            additional_content: 额外的 TOML 内容

        Returns:
            tuple: (filename, file_object, content_type)
        """
        content = f'version = "{version}"\n'
        if additional_content:
            content += additional_content

        return ("bot_config.toml", io.BytesIO(content.encode()), "application/toml")

    @staticmethod
    def generate_knowledge_base_data():
        """生成知识库数据"""
        unique_id = uuid.uuid4().hex[:8]
        return {
            "name": f"KB_{unique_id}",
            "description": "Test knowledge base description",
            "copyright_owner": "Test Owner",
            "tags": "test,knowledge",
        }

    @staticmethod
    def generate_persona_card_data():
        """生成人设卡数据"""
        unique_id = uuid.uuid4().hex[:8]
        return {
            "name": f"PC_{unique_id}",
            "description": "Test persona card description",
            "copyright_owner": "Test Owner",
            "tags": "test,persona",
        }

    @staticmethod
    def generate_message_data(recipient_id: str):
        """生成消息数据"""
        return {
            "recipient_id": recipient_id,
            "subject": f"Test Message {uuid.uuid4().hex[:8]}",
            "content": "Test message content",
        }

    @staticmethod
    def generate_comment_data():
        """生成评论数据"""
        return {"content": f"Test comment {uuid.uuid4().hex[:8]}"}
