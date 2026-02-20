"""
人设卡验证逻辑单元测试

测试人设卡验证和文件类型验证
需求：1.3
"""

import pytest
from io import BytesIO
from fastapi import UploadFile
from app.file_upload import FileUploadService
from app.error_handlers import ValidationError


class TestPersonaCardValidation:
    """测试人设卡验证逻辑"""

    @pytest.fixture
    def file_service(self):
        """创建文件上传服务实例"""
        return FileUploadService()

    def create_upload_file(self, filename: str, content: bytes = b"test content"):
        """创建用于测试的UploadFile的辅助方法"""
        return UploadFile(
            filename=filename,
            file=BytesIO(content)
        )

    def test_validate_file_type_valid_toml(self, file_service):
        """测试.toml文件被接受用于人设卡"""
        file = self.create_upload_file("bot_config.toml")
        
        result = file_service._validate_file_type(file, file_service.ALLOWED_PERSONA_TYPES)
        
        assert result is True

    def test_validate_file_type_invalid_txt(self, file_service):
        """测试.txt文件被拒绝用于人设卡"""
        file = self.create_upload_file("config.txt")
        
        result = file_service._validate_file_type(file, file_service.ALLOWED_PERSONA_TYPES)
        
        assert result is False

    def test_validate_file_type_invalid_json(self, file_service):
        """测试.json文件被拒绝用于人设卡"""
        file = self.create_upload_file("config.json")
        
        result = file_service._validate_file_type(file, file_service.ALLOWED_PERSONA_TYPES)
        
        assert result is False

    def test_validate_file_type_case_insensitive(self, file_service):
        """测试文件类型验证不区分大小写"""
        file = self.create_upload_file("bot_config.TOML")
        
        result = file_service._validate_file_type(file, file_service.ALLOWED_PERSONA_TYPES)
        
        assert result is True

    def test_validate_file_type_no_extension(self, file_service):
        """测试没有扩展名的文件被拒绝"""
        file = self.create_upload_file("bot_config")
        
        result = file_service._validate_file_type(file, file_service.ALLOWED_PERSONA_TYPES)
        
        assert result is False

    def test_validate_file_type_empty_filename(self, file_service):
        """测试空文件名被拒绝"""
        file = self.create_upload_file("")
        
        result = file_service._validate_file_type(file, file_service.ALLOWED_PERSONA_TYPES)
        
        assert result is False

    def test_validate_file_size_within_limit(self, file_service):
        """测试大小在限制内的文件被接受"""
        # 创建一个小文件
        content = b"x" * 1024  # 1KB
        file = self.create_upload_file("bot_config.toml", content)
        file.size = len(content)
        
        result = file_service._validate_file_size(file)
        
        assert result is True

    def test_validate_file_size_exceeds_limit(self, file_service):
        """测试超过大小限制的文件被拒绝"""
        # 设置大小大于MAX_FILE_SIZE
        file = self.create_upload_file("bot_config.toml")
        file.size = file_service.MAX_FILE_SIZE + 1
        
        result = file_service._validate_file_size(file)
        
        assert result is False

    def test_validate_file_size_no_size_attribute(self, file_service):
        """测试没有size属性的文件被允许（临时）"""
        file = self.create_upload_file("bot_config.toml")
        file.size = None
        
        result = file_service._validate_file_size(file)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_file_content_within_limit(self, file_service):
        """测试大小在限制内的文件内容被接受"""
        content = b"x" * 1024  # 1KB
        file = self.create_upload_file("bot_config.toml", content)
        
        result = await file_service._validate_file_content(file)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_file_content_exceeds_limit(self, file_service):
        """测试超过大小限制的文件内容被拒绝"""
        # 创建大于MAX_FILE_SIZE的内容
        content = b"x" * (file_service.MAX_FILE_SIZE + 1)
        file = self.create_upload_file("bot_config.toml", content)
        
        result = await file_service._validate_file_content(file)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_upload_persona_card_wrong_file_count_zero(self, file_service):
        """测试上传零个文件抛出ValidationError"""
        files = []
        
        with pytest.raises(ValidationError) as exc_info:
            await file_service.upload_persona_card(
                files=files,
                name="Test Persona",
                description="Test Description",
                uploader_id="user123",
                copyright_owner="Test Owner"
            )
        
        assert "必须且仅包含一个" in str(exc_info.value.message)
        assert exc_info.value.details["code"] == "PERSONA_FILE_COUNT_INVALID"

    @pytest.mark.asyncio
    async def test_upload_persona_card_wrong_file_count_multiple(self, file_service):
        """测试上传多个文件抛出ValidationError"""
        files = [
            self.create_upload_file("bot_config.toml"),
            self.create_upload_file("extra.toml")
        ]
        
        with pytest.raises(ValidationError) as exc_info:
            await file_service.upload_persona_card(
                files=files,
                name="Test Persona",
                description="Test Description",
                uploader_id="user123",
                copyright_owner="Test Owner"
            )
        
        assert "必须且仅包含一个" in str(exc_info.value.message)
        assert exc_info.value.details["code"] == "PERSONA_FILE_COUNT_INVALID"

    @pytest.mark.asyncio
    async def test_upload_persona_card_wrong_filename(self, file_service):
        """测试错误的文件名抛出ValidationError"""
        files = [self.create_upload_file("wrong_name.toml")]
        
        with pytest.raises(ValidationError) as exc_info:
            await file_service.upload_persona_card(
                files=files,
                name="Test Persona",
                description="Test Description",
                uploader_id="user123",
                copyright_owner="Test Owner"
            )
        
        assert "配置文件名必须为 bot_config.toml" in str(exc_info.value.message)
        assert exc_info.value.details["code"] == "PERSONA_FILE_NAME_INVALID"

    @pytest.mark.asyncio
    async def test_upload_persona_card_wrong_file_type(self, file_service):
        """测试错误的文件类型抛出ValidationError"""
        # 使用正确的文件名但错误的扩展名
        files = [self.create_upload_file("bot_config.json")]
        
        with pytest.raises(ValidationError) as exc_info:
            await file_service.upload_persona_card(
                files=files,
                name="Test Persona",
                description="Test Description",
                uploader_id="user123",
                copyright_owner="Test Owner"
            )
        
        # 文件名检查首先进行，所以我们得到文件名错误
        assert "配置文件名必须为 bot_config.toml" in str(exc_info.value.message)
        assert exc_info.value.details["code"] == "PERSONA_FILE_NAME_INVALID"


class TestFileTypeValidation:
    """测试不同文件类型的文件类型验证"""

    @pytest.fixture
    def file_service(self):
        """创建文件上传服务实例"""
        return FileUploadService()

    def create_upload_file(self, filename: str):
        """创建用于测试的UploadFile的辅助方法"""
        return UploadFile(
            filename=filename,
            file=BytesIO(b"test content")
        )

    def test_knowledge_base_accepts_txt(self, file_service):
        """测试知识库接受.txt文件"""
        file = self.create_upload_file("document.txt")
        
        result = file_service._validate_file_type(file, file_service.ALLOWED_KNOWLEDGE_TYPES)
        
        assert result is True

    def test_knowledge_base_accepts_json(self, file_service):
        """测试知识库接受.json文件"""
        file = self.create_upload_file("data.json")
        
        result = file_service._validate_file_type(file, file_service.ALLOWED_KNOWLEDGE_TYPES)
        
        assert result is True

    def test_knowledge_base_rejects_toml(self, file_service):
        """测试知识库拒绝.toml文件"""
        file = self.create_upload_file("config.toml")
        
        result = file_service._validate_file_type(file, file_service.ALLOWED_KNOWLEDGE_TYPES)
        
        assert result is False

    def test_persona_card_accepts_toml(self, file_service):
        """测试人设卡接受.toml文件"""
        file = self.create_upload_file("bot_config.toml")
        
        result = file_service._validate_file_type(file, file_service.ALLOWED_PERSONA_TYPES)
        
        assert result is True

    def test_persona_card_rejects_txt(self, file_service):
        """测试人设卡拒绝.txt文件"""
        file = self.create_upload_file("config.txt")
        
        result = file_service._validate_file_type(file, file_service.ALLOWED_PERSONA_TYPES)
        
        assert result is False

    def test_persona_card_rejects_json(self, file_service):
        """测试人设卡拒绝.json文件"""
        file = self.create_upload_file("config.json")
        
        result = file_service._validate_file_type(file, file_service.ALLOWED_PERSONA_TYPES)
        
        assert result is False

    def test_file_type_validation_with_multiple_dots(self, file_service):
        """测试包含多个点的文件名的文件类型验证"""
        file = self.create_upload_file("my.config.file.toml")
        
        result = file_service._validate_file_type(file, file_service.ALLOWED_PERSONA_TYPES)
        
        assert result is True

    def test_file_type_validation_with_path_separator(self, file_service):
        """测试文件类型验证正确处理路径分隔符"""
        file = self.create_upload_file("path/to/bot_config.toml")
        
        result = file_service._validate_file_type(file, file_service.ALLOWED_PERSONA_TYPES)
        
        assert result is True
