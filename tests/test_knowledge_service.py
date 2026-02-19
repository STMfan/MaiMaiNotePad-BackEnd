"""
Unit tests for knowledge service
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.orm import Session

from app.services.knowledge_service import KnowledgeService
from app.models.database import KnowledgeBase, KnowledgeBaseFile, StarRecord, User


class TestKnowledgeService:
    """Test cases for KnowledgeService"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return MagicMock(spec=Session)

    @pytest.fixture
    def knowledge_service(self, mock_db):
        """Create KnowledgeService instance with mock database"""
        return KnowledgeService(mock_db)

    @pytest.fixture
    def sample_kb(self):
        """Create a sample knowledge base object"""
        return KnowledgeBase(
            id=str(uuid.uuid4()),
            name="Test KB",
            description="Test Description",
            uploader_id=str(uuid.uuid4()),
            is_public=True,
            is_pending=False,
            star_count=0,
            downloads=0,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    def test_get_knowledge_base_by_id_success(self, knowledge_service, mock_db, sample_kb):
        """Test successful knowledge base retrieval by ID"""
        mock_db.query().filter().first.return_value = sample_kb
        
        result = knowledge_service.get_knowledge_base_by_id(sample_kb.id)
        
        assert result == sample_kb

    def test_get_knowledge_base_by_id_not_found(self, knowledge_service, mock_db):
        """Test knowledge base retrieval when not found"""
        mock_db.query().filter().first.return_value = None
        
        result = knowledge_service.get_knowledge_base_by_id("nonexistent_id")
        
        assert result is None

    def test_get_public_knowledge_bases(self, knowledge_service, mock_db, sample_kb):
        """Test getting public knowledge bases with pagination"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_kb]
        mock_db.query.return_value = mock_query
        
        kbs, total = knowledge_service.get_public_knowledge_bases(page=1, page_size=20)
        
        assert len(kbs) == 1
        assert total == 1
        assert kbs[0] == sample_kb

    def test_get_public_knowledge_bases_with_name_filter(self, knowledge_service, mock_db, sample_kb):
        """Test getting public knowledge bases with name filter"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_kb]
        mock_db.query.return_value = mock_query
        
        kbs, total = knowledge_service.get_public_knowledge_bases(
            page=1,
            page_size=20,
            name="Test"
        )
        
        assert len(kbs) == 1

    def test_save_knowledge_base_create_new(self, knowledge_service, mock_db):
        """Test creating new knowledge base"""
        kb_data = {
            "name": "New KB",
            "description": "New Description",
            "uploader_id": str(uuid.uuid4()),
            "is_public": False,
            "is_pending": True
        }
        
        result = knowledge_service.save_knowledge_base(kb_data)
        
        assert result is not None
        assert result.name == "New KB"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_save_knowledge_base_update_existing(self, knowledge_service, mock_db, sample_kb):
        """Test updating existing knowledge base"""
        kb_data = {
            "id": sample_kb.id,
            "name": "Updated KB",
            "description": "Updated Description"
        }
        mock_db.query().filter().first.return_value = sample_kb
        
        result = knowledge_service.save_knowledge_base(kb_data)
        
        assert result is not None
        assert result.name == "Updated KB"
        mock_db.commit.assert_called_once()

    def test_check_duplicate_name_exists(self, knowledge_service, mock_db, sample_kb):
        """Test checking for duplicate name when it exists"""
        mock_db.query().filter().first.return_value = sample_kb
        
        result = knowledge_service.check_duplicate_name(
            user_id=sample_kb.uploader_id,
            name="Test KB"
        )
        
        assert result is True

    def test_check_duplicate_name_not_exists(self, knowledge_service, mock_db):
        """Test checking for duplicate name when it doesn't exist"""
        mock_db.query().filter().first.return_value = None
        
        result = knowledge_service.check_duplicate_name(
            user_id=str(uuid.uuid4()),
            name="Unique KB"
        )
        
        assert result is False

    def test_update_knowledge_base_success(self, knowledge_service, mock_db, sample_kb):
        """Test successful knowledge base update"""
        mock_db.query().filter().first.return_value = sample_kb
        update_data = {"content": "Updated content"}
        
        success, message, kb = knowledge_service.update_knowledge_base(
            kb_id=sample_kb.id,
            update_data=update_data,
            user_id=sample_kb.uploader_id
        )
        
        assert success is True
        assert kb is not None
        mock_db.commit.assert_called_once()

    def test_update_knowledge_base_not_owner(self, knowledge_service, mock_db, sample_kb):
        """Test knowledge base update by non-owner"""
        mock_db.query().filter().first.return_value = sample_kb
        update_data = {"content": "Updated content"}
        
        success, message, kb = knowledge_service.update_knowledge_base(
            kb_id=sample_kb.id,
            update_data=update_data,
            user_id=str(uuid.uuid4()),  # Different user
            is_admin=False
        )
        
        assert success is False
        assert "是你的知识库吗你就改" in message

    def test_update_knowledge_base_public_restricted(self, knowledge_service, mock_db, sample_kb):
        """Test that public knowledge base updates are restricted"""
        sample_kb.is_public = True
        mock_db.query().filter().first.return_value = sample_kb
        update_data = {"name": "New Name"}  # Not allowed for public KB
        
        success, message, kb = knowledge_service.update_knowledge_base(
            kb_id=sample_kb.id,
            update_data=update_data,
            user_id=sample_kb.uploader_id
        )
        
        assert success is False
        assert "仅允许修改补充说明" in message

    def test_delete_knowledge_base_success(self, knowledge_service, mock_db, sample_kb):
        """Test successful knowledge base deletion"""
        mock_db.query().filter().first.return_value = sample_kb
        
        result = knowledge_service.delete_knowledge_base(sample_kb.id)
        
        assert result is True
        mock_db.delete.assert_called_once_with(sample_kb)
        mock_db.commit.assert_called_once()

    def test_delete_knowledge_base_not_found(self, knowledge_service, mock_db):
        """Test knowledge base deletion when not found"""
        mock_db.query().filter().first.return_value = None
        
        result = knowledge_service.delete_knowledge_base("nonexistent_id")
        
        assert result is False

    def test_is_starred_true(self, knowledge_service, mock_db):
        """Test checking if knowledge base is starred"""
        mock_star = StarRecord(
            id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            target_id=str(uuid.uuid4()),
            target_type="knowledge"
        )
        mock_db.query().filter().first.return_value = mock_star
        
        result = knowledge_service.is_starred(mock_star.user_id, mock_star.target_id)
        
        assert result is True

    def test_is_starred_false(self, knowledge_service, mock_db):
        """Test checking if knowledge base is not starred"""
        mock_db.query().filter().first.return_value = None
        
        result = knowledge_service.is_starred(str(uuid.uuid4()), str(uuid.uuid4()))
        
        assert result is False

    def test_add_star_success(self, knowledge_service, mock_db, sample_kb):
        """Test successfully adding star"""
        mock_db.query().filter().first.side_effect = [None, sample_kb]  # Not starred, KB exists
        
        result = knowledge_service.add_star(str(uuid.uuid4()), sample_kb.id)
        
        assert result is True
        assert sample_kb.star_count == 1
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_add_star_already_starred(self, knowledge_service, mock_db):
        """Test adding star when already starred"""
        mock_star = StarRecord(
            id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            target_id=str(uuid.uuid4()),
            target_type="knowledge"
        )
        mock_db.query().filter().first.return_value = mock_star
        
        result = knowledge_service.add_star(mock_star.user_id, mock_star.target_id)
        
        assert result is False
        mock_db.add.assert_not_called()

    def test_remove_star_success(self, knowledge_service, mock_db, sample_kb):
        """Test successfully removing star"""
        mock_star = StarRecord(
            id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            target_id=sample_kb.id,
            target_type="knowledge"
        )
        sample_kb.star_count = 5
        mock_db.query().filter().first.side_effect = [mock_star, sample_kb]
        
        result = knowledge_service.remove_star(mock_star.user_id, sample_kb.id)
        
        assert result is True
        assert sample_kb.star_count == 4
        mock_db.delete.assert_called_once_with(mock_star)
        mock_db.commit.assert_called_once()

    def test_remove_star_not_starred(self, knowledge_service, mock_db):
        """Test removing star when not starred"""
        mock_db.query().filter().first.return_value = None
        
        result = knowledge_service.remove_star(str(uuid.uuid4()), str(uuid.uuid4()))
        
        assert result is False
        mock_db.delete.assert_not_called()

    def test_increment_downloads_success(self, knowledge_service, mock_db, sample_kb):
        """Test successfully incrementing downloads"""
        sample_kb.downloads = 10
        mock_db.query().filter().first.return_value = sample_kb
        
        result = knowledge_service.increment_downloads(sample_kb.id)
        
        assert result is True
        assert sample_kb.downloads == 11
        mock_db.commit.assert_called_once()

    def test_increment_downloads_not_found(self, knowledge_service, mock_db):
        """Test incrementing downloads when KB not found"""
        mock_db.query().filter().first.return_value = None
        
        result = knowledge_service.increment_downloads("nonexistent_id")
        
        assert result is False

    def test_get_files_by_knowledge_base_id(self, knowledge_service, mock_db):
        """Test getting files for knowledge base"""
        mock_files = [
            KnowledgeBaseFile(
                id=str(uuid.uuid4()),
                knowledge_base_id=str(uuid.uuid4()),
                file_name="file1.txt",
                file_path="/path/to/file1.txt"
            )
        ]
        mock_db.query().filter().all.return_value = mock_files
        
        result = knowledge_service.get_files_by_knowledge_base_id(str(uuid.uuid4()))
        
        assert len(result) == 1
        assert result[0].file_name == "file1.txt"

    def test_resolve_uploader_id_by_id(self, knowledge_service, mock_db):
        """Test resolving uploader by user ID"""
        user_id = str(uuid.uuid4())
        mock_user = User(id=user_id, username="testuser")
        mock_db.query().filter().first.return_value = mock_user
        
        result = knowledge_service.resolve_uploader_id(user_id)
        
        assert result == user_id

    def test_resolve_uploader_id_by_username(self, knowledge_service, mock_db):
        """Test resolving uploader by username"""
        user_id = str(uuid.uuid4())
        mock_user = User(id=user_id, username="testuser")
        mock_db.query().filter().first.side_effect = [None, mock_user]  # Not found by ID, found by username
        
        result = knowledge_service.resolve_uploader_id("testuser")
        
        assert result == user_id

    def test_resolve_uploader_id_not_found(self, knowledge_service, mock_db):
        """Test resolving uploader when not found"""
        mock_db.query().filter().first.return_value = None
        
        result = knowledge_service.resolve_uploader_id("nonexistent")
        
        assert result is None

    def test_get_public_knowledge_bases_pagination(self, knowledge_service, mock_db, sample_kb):
        """Test pagination with different page sizes"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 50
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_kb]
        mock_db.query.return_value = mock_query
        
        kbs, total = knowledge_service.get_public_knowledge_bases(page=2, page_size=10)
        
        assert total == 50
        mock_query.offset.assert_called_with(10)
        mock_query.limit.assert_called_with(10)

    def test_get_user_knowledge_bases(self, knowledge_service, mock_db, sample_kb):
        """Test getting knowledge bases for specific user"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_kb]
        mock_db.query.return_value = mock_query
        
        kbs, total = knowledge_service.get_user_knowledge_bases(
            user_id=sample_kb.uploader_id,
            page=1,
            page_size=20
        )
        
        assert len(kbs) == 1
        assert total == 1
