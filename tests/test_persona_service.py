"""
Unit tests for persona service
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, MagicMock
from sqlalchemy.orm import Session

from app.services.persona_service import PersonaService
from app.models.database import PersonaCard, PersonaCardFile, StarRecord, User


class TestPersonaService:
    """Test cases for PersonaService"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return MagicMock(spec=Session)

    @pytest.fixture
    def persona_service(self, mock_db):
        """Create PersonaService instance with mock database"""
        return PersonaService(mock_db)

    @pytest.fixture
    def sample_pc(self):
        """Create a sample persona card object"""
        return PersonaCard(
            id=str(uuid.uuid4()),
            name="Test Persona",
            description="Test Description",
            uploader_id=str(uuid.uuid4()),
            version="1.0",
            is_public=True,
            is_pending=False,
            star_count=0,
            downloads=0,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    def test_get_persona_card_by_id_success(self, persona_service, mock_db, sample_pc):
        """Test successful persona card retrieval by ID"""
        mock_db.query().filter().first.return_value = sample_pc
        
        result = persona_service.get_persona_card_by_id(sample_pc.id)
        
        assert result == sample_pc

    def test_get_persona_card_by_id_not_found(self, persona_service, mock_db):
        """Test persona card retrieval when not found"""
        mock_db.query().filter().first.return_value = None
        
        result = persona_service.get_persona_card_by_id("nonexistent_id")
        
        assert result is None

    def test_get_all_persona_cards(self, persona_service, mock_db, sample_pc):
        """Test getting all persona cards"""
        mock_db.query().all.return_value = [sample_pc]
        
        result = persona_service.get_all_persona_cards()
        
        assert len(result) == 1
        assert result[0] == sample_pc

    def test_get_public_persona_cards(self, persona_service, mock_db, sample_pc):
        """Test getting public persona cards with pagination"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_pc]
        mock_db.query.return_value = mock_query
        
        pcs, total = persona_service.get_public_persona_cards(page=1, page_size=20)
        
        assert len(pcs) == 1
        assert total == 1
        assert pcs[0] == sample_pc

    def test_save_persona_card_create_new(self, persona_service, mock_db):
        """Test creating new persona card"""
        pc_data = {
            "name": "New Persona",
            "description": "New Description",
            "uploader_id": str(uuid.uuid4()),
            "version": "1.0",
            "is_public": False,
            "is_pending": True
        }
        
        result = persona_service.save_persona_card(pc_data)
        
        assert result is not None
        assert result.name == "New Persona"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_save_persona_card_update_existing(self, persona_service, mock_db, sample_pc):
        """Test updating existing persona card"""
        pc_data = {
            "id": sample_pc.id,
            "name": "Updated Persona",
            "description": "Updated Description"
        }
        mock_db.query().filter().first.return_value = sample_pc
        
        result = persona_service.save_persona_card(pc_data)
        
        assert result is not None
        assert result.name == "Updated Persona"
        mock_db.commit.assert_called_once()

    def test_update_persona_card_success(self, persona_service, mock_db, sample_pc):
        """Test successful persona card update"""
        mock_db.query().filter().first.return_value = sample_pc
        update_data = {"content": "Updated content"}
        
        success, message, pc = persona_service.update_persona_card(
            pc_id=sample_pc.id,
            update_data=update_data,
            user_id=sample_pc.uploader_id
        )
        
        assert success is True
        assert pc is not None
        mock_db.commit.assert_called_once()

    def test_update_persona_card_not_owner(self, persona_service, mock_db, sample_pc):
        """Test persona card update by non-owner"""
        mock_db.query().filter().first.return_value = sample_pc
        update_data = {"content": "Updated content"}
        
        success, message, pc = persona_service.update_persona_card(
            pc_id=sample_pc.id,
            update_data=update_data,
            user_id=str(uuid.uuid4()),  # Different user
            is_admin=False
        )
        
        assert success is False
        assert "没有权限" in message

    def test_update_persona_card_public_restricted(self, persona_service, mock_db, sample_pc):
        """Test that public persona card updates are restricted"""
        sample_pc.is_public = True
        mock_db.query().filter().first.return_value = sample_pc
        update_data = {"name": "New Name"}  # Not allowed for public PC
        
        success, message, pc = persona_service.update_persona_card(
            pc_id=sample_pc.id,
            update_data=update_data,
            user_id=sample_pc.uploader_id
        )
        
        assert success is False
        assert "仅允许修改补充说明" in message

    def test_delete_persona_card_success(self, persona_service, mock_db, sample_pc):
        """Test successful persona card deletion"""
        mock_db.query().filter().first.return_value = sample_pc
        
        result = persona_service.delete_persona_card(sample_pc.id)
        
        assert result is True
        mock_db.delete.assert_called_once_with(sample_pc)
        mock_db.commit.assert_called_once()

    def test_delete_persona_card_not_found(self, persona_service, mock_db):
        """Test persona card deletion when not found"""
        mock_db.query().filter().first.return_value = None
        
        result = persona_service.delete_persona_card("nonexistent_id")
        
        assert result is False

    def test_is_starred_true(self, persona_service, mock_db):
        """Test checking if persona card is starred"""
        mock_star = StarRecord(
            id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            target_id=str(uuid.uuid4()),
            target_type="persona"
        )
        mock_db.query().filter().first.return_value = mock_star
        
        result = persona_service.is_starred(mock_star.user_id, mock_star.target_id)
        
        assert result is True

    def test_is_starred_false(self, persona_service, mock_db):
        """Test checking if persona card is not starred"""
        mock_db.query().filter().first.return_value = None
        
        result = persona_service.is_starred(str(uuid.uuid4()), str(uuid.uuid4()))
        
        assert result is False

    def test_add_star_success(self, persona_service, mock_db, sample_pc):
        """Test successfully adding star"""
        mock_db.query().filter().first.side_effect = [None, sample_pc]  # Not starred, PC exists
        
        result = persona_service.add_star(str(uuid.uuid4()), sample_pc.id)
        
        assert result is True
        assert sample_pc.star_count == 1
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_add_star_already_starred(self, persona_service, mock_db):
        """Test adding star when already starred"""
        mock_star = StarRecord(
            id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            target_id=str(uuid.uuid4()),
            target_type="persona"
        )
        mock_db.query().filter().first.return_value = mock_star
        
        result = persona_service.add_star(mock_star.user_id, mock_star.target_id)
        
        assert result is False
        mock_db.add.assert_not_called()

    def test_remove_star_success(self, persona_service, mock_db, sample_pc):
        """Test successfully removing star"""
        mock_star = StarRecord(
            id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            target_id=sample_pc.id,
            target_type="persona"
        )
        sample_pc.star_count = 5
        mock_db.query().filter().first.side_effect = [mock_star, sample_pc]
        
        result = persona_service.remove_star(mock_star.user_id, sample_pc.id)
        
        assert result is True
        assert sample_pc.star_count == 4
        mock_db.delete.assert_called_once_with(mock_star)
        mock_db.commit.assert_called_once()

    def test_remove_star_not_starred(self, persona_service, mock_db):
        """Test removing star when not starred"""
        mock_db.query().filter().first.return_value = None
        
        result = persona_service.remove_star(str(uuid.uuid4()), str(uuid.uuid4()))
        
        assert result is False
        mock_db.delete.assert_not_called()

    def test_increment_downloads_success(self, persona_service, mock_db, sample_pc):
        """Test successfully incrementing downloads"""
        sample_pc.downloads = 10
        mock_db.query().filter().first.return_value = sample_pc
        
        result = persona_service.increment_downloads(sample_pc.id)
        
        assert result is True
        assert sample_pc.downloads == 11
        mock_db.commit.assert_called_once()

    def test_increment_downloads_not_found(self, persona_service, mock_db):
        """Test incrementing downloads when PC not found"""
        mock_db.query().filter().first.return_value = None
        
        result = persona_service.increment_downloads("nonexistent_id")
        
        assert result is False

    def test_get_files_by_persona_card_id(self, persona_service, mock_db):
        """Test getting files for persona card"""
        mock_files = [
            PersonaCardFile(
                id=str(uuid.uuid4()),
                persona_card_id=str(uuid.uuid4()),
                file_name="bot_config.toml",
                file_path="/path/to/bot_config.toml"
            )
        ]
        mock_db.query().filter().all.return_value = mock_files
        
        result = persona_service.get_files_by_persona_card_id(str(uuid.uuid4()))
        
        assert len(result) == 1
        assert result[0].file_name == "bot_config.toml"

    def test_delete_files_by_persona_card_id_success(self, persona_service, mock_db):
        """Test successfully deleting files for persona card"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_db.query.return_value = mock_query
        
        result = persona_service.delete_files_by_persona_card_id(str(uuid.uuid4()))
        
        assert result is True
        mock_query.delete.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_resolve_uploader_id_by_id(self, persona_service, mock_db):
        """Test resolving uploader by user ID"""
        user_id = str(uuid.uuid4())
        mock_user = User(id=user_id, username="testuser")
        mock_db.query().filter().first.return_value = mock_user
        
        result = persona_service.resolve_uploader_id(user_id)
        
        assert result == user_id

    def test_resolve_uploader_id_by_username(self, persona_service, mock_db):
        """Test resolving uploader by username"""
        user_id = str(uuid.uuid4())
        mock_user = User(id=user_id, username="testuser")
        mock_db.query().filter().first.side_effect = [None, mock_user]  # Not found by ID, found by username
        
        result = persona_service.resolve_uploader_id("testuser")
        
        assert result == user_id

    def test_resolve_uploader_id_not_found(self, persona_service, mock_db):
        """Test resolving uploader when not found"""
        mock_db.query().filter().first.return_value = None
        
        result = persona_service.resolve_uploader_id("nonexistent")
        
        assert result is None

    def test_get_public_persona_cards_pagination(self, persona_service, mock_db, sample_pc):
        """Test pagination with different page sizes"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 50
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_pc]
        mock_db.query.return_value = mock_query
        
        pcs, total = persona_service.get_public_persona_cards(page=2, page_size=10)
        
        assert total == 50
        mock_query.offset.assert_called_with(10)
        mock_query.limit.assert_called_with(10)

    def test_get_user_persona_cards(self, persona_service, mock_db, sample_pc):
        """Test getting persona cards for specific user"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_pc]
        mock_db.query.return_value = mock_query
        
        pcs, total = persona_service.get_user_persona_cards(
            user_id=sample_pc.uploader_id,
            page=1,
            page_size=20
        )
        
        assert len(pcs) == 1
        assert total == 1
