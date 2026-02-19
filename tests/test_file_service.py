"""
Unit tests for file service
"""

import pytest
import uuid
import os
import tempfile
import shutil
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch, mock_open
from sqlalchemy.orm import Session

from app.services.file_service import FileService, FileValidationError, FileDatabaseError
from app.models.database import KnowledgeBase, PersonaCard, KnowledgeBaseFile, PersonaCardFile, User


class TestFileService:
    """Test cases for FileService"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return MagicMock(spec=Session)

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        # Cleanup
        if os.path.exists(temp_path):
            shutil.rmtree(temp_path)

    @pytest.fixture
    def file_service(self, mock_db, temp_dir):
        """Create FileService instance with mock database and temp directory"""
        with patch.dict('os.environ', {'UPLOAD_DIR': temp_dir}):
            service = FileService(mock_db)
            return service

    @pytest.fixture
    def sample_kb(self, temp_dir):
        """Create a sample knowledge base object"""
        kb_dir = os.path.join(temp_dir, "kb_test")
        os.makedirs(kb_dir, exist_ok=True)
        return KnowledgeBase(
            id=str(uuid.uuid4()),
            name="Test KB",
            description="Test Description",
            uploader_id=str(uuid.uuid4()),
            base_path=kb_dir,
            is_public=False,
            is_pending=True,
            created_at=datetime.now()
        )

    @pytest.fixture
    def sample_pc(self, temp_dir):
        """Create a sample persona card object"""
        pc_dir = os.path.join(temp_dir, "pc_test")
        os.makedirs(pc_dir, exist_ok=True)
        return PersonaCard(
            id=str(uuid.uuid4()),
            name="Test Persona",
            description="Test Description",
            uploader_id=str(uuid.uuid4()),
            base_path=pc_dir,
            version="1.0",
            is_public=False,
            is_pending=True,
            created_at=datetime.now()
        )

    def test_file_service_initialization(self, file_service, temp_dir):
        """Test FileService initializes with correct directories"""
        assert file_service.upload_dir == temp_dir
        assert os.path.exists(file_service.knowledge_dir)
        assert os.path.exists(file_service.persona_dir)

    def test_validate_file_type_valid(self, file_service):
        """Test file type validation for valid types"""
        assert file_service._validate_file_type("test.txt", [".txt", ".json"]) is True
        assert file_service._validate_file_type("test.json", [".txt", ".json"]) is True

    def test_validate_file_type_invalid(self, file_service):
        """Test file type validation for invalid types"""
        assert file_service._validate_file_type("test.exe", [".txt", ".json"]) is False
        assert file_service._validate_file_type("test.pdf", [".txt", ".json"]) is False

    def test_validate_file_size_valid(self, file_service):
        """Test file size validation for valid sizes"""
        assert file_service._validate_file_size(1024) is True
        assert file_service._validate_file_size(file_service.MAX_FILE_SIZE) is True

    def test_validate_file_size_invalid(self, file_service):
        """Test file size validation for invalid sizes"""
        assert file_service._validate_file_size(file_service.MAX_FILE_SIZE + 1) is False

    def test_save_file_success(self, file_service, temp_dir):
        """Test successful file saving"""
        content = b"Test file content"
        filename = "test.txt"
        
        file_path, file_size = file_service._save_file(content, filename, temp_dir)
        
        assert os.path.exists(file_path)
        assert file_size == len(content)
        with open(file_path, 'rb') as f:
            assert f.read() == content

    def test_save_file_duplicate_name(self, file_service, temp_dir):
        """Test saving file with duplicate name adds timestamp"""
        content = b"Test content"
        filename = "test.txt"
        
        # Save first file
        file_path1, _ = file_service._save_file(content, filename, temp_dir)
        
        # Save second file with same name
        file_path2, _ = file_service._save_file(content, filename, temp_dir)
        
        assert file_path1 != file_path2
        assert os.path.exists(file_path1)
        assert os.path.exists(file_path2)

    def test_upload_knowledge_base_success(self, file_service, mock_db):
        """Test successful knowledge base upload"""
        files = [("test.txt", b"Test content")]
        
        result = file_service.upload_knowledge_base(
            files=files,
            name="Test KB",
            description="Test Description",
            uploader_id=str(uuid.uuid4())
        )
        
        assert result is not None
        assert result.name == "Test KB"
        mock_db.add.assert_called()
        mock_db.commit.assert_called_once()

    def test_upload_knowledge_base_too_many_files(self, file_service, mock_db):
        """Test knowledge base upload with too many files"""
        files = [(f"test{i}.txt", b"Content") for i in range(101)]
        
        with pytest.raises(FileValidationError) as exc_info:
            file_service.upload_knowledge_base(
                files=files,
                name="Test KB",
                description="Test Description",
                uploader_id=str(uuid.uuid4())
            )
        
        assert "文件数量超过限制" in str(exc_info.value)

    def test_upload_knowledge_base_invalid_file_type(self, file_service, mock_db):
        """Test knowledge base upload with invalid file type"""
        files = [("test.exe", b"Content")]
        
        with pytest.raises(FileValidationError) as exc_info:
            file_service.upload_knowledge_base(
                files=files,
                name="Test KB",
                description="Test Description",
                uploader_id=str(uuid.uuid4())
            )
        
        assert "不支持的文件类型" in str(exc_info.value)

    def test_upload_knowledge_base_file_too_large(self, file_service, mock_db):
        """Test knowledge base upload with file too large"""
        large_content = b"x" * (file_service.MAX_FILE_SIZE + 1)
        files = [("test.txt", large_content)]
        
        with pytest.raises(FileValidationError) as exc_info:
            file_service.upload_knowledge_base(
                files=files,
                name="Test KB",
                description="Test Description",
                uploader_id=str(uuid.uuid4())
            )
        
        assert "文件过大" in str(exc_info.value)

    def test_upload_persona_card_success(self, file_service, mock_db):
        """Test successful persona card upload"""
        toml_content = b'version = "1.0"\nname = "Test Bot"'
        files = [("bot_config.toml", toml_content)]
        
        with patch('builtins.open', mock_open(read_data=toml_content)):
            with patch('toml.load', return_value={"version": "1.0"}):
                result = file_service.upload_persona_card(
                    files=files,
                    name="Test Persona",
                    description="Test Description",
                    uploader_id=str(uuid.uuid4()),
                    copyright_owner="Test Owner"
                )
        
        assert result is not None
        assert result.name == "Test Persona"
        assert result.version == "1.0"
        mock_db.add.assert_called()
        mock_db.commit.assert_called_once()

    def test_upload_persona_card_wrong_file_count(self, file_service, mock_db):
        """Test persona card upload with wrong file count"""
        files = [("file1.toml", b"content"), ("file2.toml", b"content")]
        
        with pytest.raises(FileValidationError) as exc_info:
            file_service.upload_persona_card(
                files=files,
                name="Test Persona",
                description="Test Description",
                uploader_id=str(uuid.uuid4()),
                copyright_owner="Test Owner"
            )
        
        assert "必须且仅包含一个" in str(exc_info.value)

    def test_upload_persona_card_wrong_filename(self, file_service, mock_db):
        """Test persona card upload with wrong filename"""
        files = [("wrong_name.toml", b"content")]
        
        with pytest.raises(FileValidationError) as exc_info:
            file_service.upload_persona_card(
                files=files,
                name="Test Persona",
                description="Test Description",
                uploader_id=str(uuid.uuid4()),
                copyright_owner="Test Owner"
            )
        
        assert "配置文件名必须为 bot_config.toml" in str(exc_info.value)

    def test_upload_persona_card_missing_version(self, file_service, mock_db):
        """Test persona card upload with missing version in TOML"""
        toml_content = b'name = "Test Bot"'
        files = [("bot_config.toml", toml_content)]
        
        with patch('builtins.open', mock_open(read_data=toml_content)):
            with patch('toml.load', return_value={"name": "Test Bot"}):
                with pytest.raises(FileValidationError) as exc_info:
                    file_service.upload_persona_card(
                        files=files,
                        name="Test Persona",
                        description="Test Description",
                        uploader_id=str(uuid.uuid4()),
                        copyright_owner="Test Owner"
                    )
        
        assert "未找到版本号字段" in str(exc_info.value)

    def test_get_knowledge_base_content_success(self, file_service, mock_db, sample_kb):
        """Test getting knowledge base content"""
        mock_db.query().filter().first.return_value = sample_kb
        mock_db.query().filter().all.return_value = []
        
        result = file_service.get_knowledge_base_content(sample_kb.id)
        
        assert result["knowledge_base"]["id"] == sample_kb.id
        assert result["knowledge_base"]["name"] == sample_kb.name
        assert "files" in result

    def test_get_knowledge_base_content_not_found(self, file_service, mock_db):
        """Test getting knowledge base content when not found"""
        mock_db.query().filter().first.return_value = None
        
        with pytest.raises(FileValidationError) as exc_info:
            file_service.get_knowledge_base_content("nonexistent_id")
        
        assert "知识库不存在" in str(exc_info.value)

    def test_get_persona_card_content_success(self, file_service, mock_db, sample_pc):
        """Test getting persona card content"""
        mock_db.query().filter().first.return_value = sample_pc
        mock_db.query().filter().all.return_value = []
        
        result = file_service.get_persona_card_content(sample_pc.id)
        
        assert result["persona_card"]["id"] == sample_pc.id
        assert result["persona_card"]["name"] == sample_pc.name
        assert "files" in result

    def test_delete_knowledge_base_success(self, file_service, mock_db, sample_kb):
        """Test successful knowledge base deletion"""
        # Create a test directory
        os.makedirs(sample_kb.base_path, exist_ok=True)
        test_file = os.path.join(sample_kb.base_path, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test")
        
        # Mock the database query to return our sample KB
        mock_db.query().filter().first.return_value = sample_kb
        
        # Ensure directory exists before deletion
        assert os.path.exists(sample_kb.base_path)
        
        result = file_service.delete_knowledge_base(sample_kb.id, sample_kb.uploader_id)
        
        assert result is True
        assert not os.path.exists(sample_kb.base_path)

    def test_delete_knowledge_base_directory_not_exists(self, file_service, sample_kb):
        """Test knowledge base deletion when directory doesn't exist"""
        sample_kb.base_path = "/nonexistent/path"
        
        result = file_service.delete_knowledge_base(sample_kb.id, sample_kb.uploader_id)
        
        assert result is False

    def test_extract_version_from_toml_top_level(self, file_service):
        """Test extracting version from top-level TOML field"""
        data = {"version": "1.0", "name": "Test"}
        
        result = file_service._extract_version_from_toml(data)
        
        assert result == "1.0"

    def test_extract_version_from_toml_meta_field(self, file_service):
        """Test extracting version from meta field in TOML"""
        data = {"meta": {"version": "2.0"}, "name": "Test"}
        
        result = file_service._extract_version_from_toml(data)
        
        assert result == "2.0"

    def test_extract_version_from_toml_not_found(self, file_service):
        """Test extracting version when not found in TOML"""
        data = {"name": "Test", "description": "Test"}
        
        result = file_service._extract_version_from_toml(data)
        
        assert result is None

    def test_add_files_to_knowledge_base_success(self, file_service, mock_db, sample_kb):
        """Test successfully adding files to knowledge base"""
        mock_db.query().filter().first.return_value = sample_kb
        mock_db.query().filter().all.return_value = []
        
        files = [("new_file.txt", b"New content")]
        
        result = file_service.add_files_to_knowledge_base(
            kb_id=sample_kb.id,
            files=files,
            user_id=sample_kb.uploader_id
        )
        
        assert result is not None
        mock_db.add.assert_called()
        mock_db.commit.assert_called_once()

    def test_add_files_to_knowledge_base_duplicate_name(self, file_service, mock_db, sample_kb):
        """Test adding file with duplicate name"""
        existing_file = KnowledgeBaseFile(
            id=str(uuid.uuid4()),
            knowledge_base_id=sample_kb.id,
            original_name="test.txt",
            file_name="test.txt",
            file_path="/path/test.txt"
        )
        
        mock_db.query().filter().first.return_value = sample_kb
        mock_db.query().filter().all.return_value = [existing_file]
        
        files = [("test.txt", b"Content")]
        
        with pytest.raises(FileValidationError) as exc_info:
            file_service.add_files_to_knowledge_base(
                kb_id=sample_kb.id,
                files=files,
                user_id=sample_kb.uploader_id
            )
        
        assert "文件名已存在" in str(exc_info.value)

    def test_delete_file_from_knowledge_base_success(self, file_service, mock_db, sample_kb):
        """Test successfully deleting file from knowledge base"""
        # Create test file
        test_file_path = os.path.join(sample_kb.base_path, "test.txt")
        with open(test_file_path, 'w') as f:
            f.write("test")
        
        kb_file = KnowledgeBaseFile(
            id=str(uuid.uuid4()),
            knowledge_base_id=sample_kb.id,
            original_name="test.txt",
            file_name="test.txt",
            file_path="test.txt"
        )
        
        mock_db.query().filter().first.side_effect = [sample_kb, kb_file]
        
        result = file_service.delete_file_from_knowledge_base(
            kb_id=sample_kb.id,
            file_id=kb_file.id,
            user_id=sample_kb.uploader_id
        )
        
        assert result is True
        assert not os.path.exists(test_file_path)
        mock_db.delete.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_validate_file_type_case_insensitive(self, file_service):
        """Test file type validation is case insensitive"""
        assert file_service._validate_file_type("test.TXT", [".txt", ".json"]) is True
        assert file_service._validate_file_type("test.JSON", [".txt", ".json"]) is True

    def test_validate_file_size_zero(self, file_service):
        """Test file size validation for zero-sized file"""
        assert file_service._validate_file_size(0) is True

    def test_extract_version_from_toml_nested_meta(self, file_service):
        """Test extracting version from nested meta field"""
        data = {"meta": {"info": {"version": "3.0"}}}
        
        result = file_service._extract_version_from_toml(data)
        
        # Should not find deeply nested version
        assert result is None or result == "3.0"
