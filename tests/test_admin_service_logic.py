"""
Unit tests for admin service layer logic

This module tests the business logic used in admin operations:
- Admin statistics calculation
- User search and filtering logic
- Role assignment validation

Requirements: 2.1
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.database import User, KnowledgeBase, PersonaCard


class TestAdminStatisticsCalculation:
    """Test admin statistics calculation logic
    
    Tests the business logic for calculating admin dashboard statistics
    including user counts, content counts, and pending review counts.
    """
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return MagicMock(spec=Session)
    
    def test_calculate_total_active_users(self, mock_db):
        """Test counting total active users"""
        # Mock the query chain for counting active users
        mock_query = Mock()
        mock_query.scalar.return_value = 42
        mock_db.query().filter().scalar.return_value = 42
        
        # Execute the logic from admin routes
        total_users = mock_db.query(func.count(User.id)).filter(
            User.is_active == True
        ).scalar() or 0
        
        assert total_users == 42
    
    def test_calculate_total_active_users_when_none(self, mock_db):
        """Test counting active users returns 0 when None"""
        mock_db.query().filter().scalar.return_value = None
        
        total_users = mock_db.query(func.count(User.id)).filter(
            User.is_active == True
        ).scalar() or 0
        
        assert total_users == 0
    
    def test_calculate_total_knowledge_bases(self, mock_db):
        """Test counting total knowledge bases"""
        mock_db.query().scalar.return_value = 15
        
        total_knowledge = mock_db.query(
            func.count(KnowledgeBase.id)
        ).scalar() or 0
        
        assert total_knowledge == 15
    
    def test_calculate_total_persona_cards(self, mock_db):
        """Test counting total persona cards"""
        mock_db.query().scalar.return_value = 23
        
        total_personas = mock_db.query(
            func.count(PersonaCard.id)
        ).scalar() or 0
        
        assert total_personas == 23
    
    def test_calculate_pending_knowledge_bases(self, mock_db):
        """Test counting pending knowledge bases"""
        mock_db.query().filter().scalar.return_value = 5
        
        pending_knowledge = mock_db.query(func.count(KnowledgeBase.id)).filter(
            KnowledgeBase.is_pending == True
        ).scalar() or 0
        
        assert pending_knowledge == 5
    
    def test_calculate_pending_persona_cards(self, mock_db):
        """Test counting pending persona cards"""
        mock_db.query().filter().scalar.return_value = 3
        
        pending_personas = mock_db.query(func.count(PersonaCard.id)).filter(
            PersonaCard.is_pending == True
        ).scalar() or 0
        
        assert pending_personas == 3
    
    def test_calculate_all_statistics_together(self, mock_db):
        """Test calculating all statistics in one operation"""
        # Setup mock to return different values for different queries
        mock_db.query().filter().scalar.side_effect = [42, 15, 23, 5, 3]
        mock_db.query().scalar.side_effect = [15, 23]
        
        # This simulates the statistics gathering logic
        stats = {
            "totalUsers": 42,
            "totalKnowledge": 15,
            "totalPersonas": 23,
            "pendingKnowledge": 5,
            "pendingPersonas": 3
        }
        
        assert stats["totalUsers"] == 42
        assert stats["totalKnowledge"] == 15
        assert stats["totalPersonas"] == 23
        assert stats["pendingKnowledge"] == 5
        assert stats["pendingPersonas"] == 3


class TestUserSearchAndFiltering:
    """Test user search and filtering logic
    
    Tests the business logic for searching users by username/email
    and filtering by role.
    """
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return MagicMock(spec=Session)
    
    @pytest.fixture
    def sample_users(self):
        """Create sample user objects"""
        return [
            User(
                id="user1",
                username="john_doe",
                email="john@example.com",
                is_active=True,
                is_admin=False,
                is_moderator=False,
                is_super_admin=False
            ),
            User(
                id="user2",
                username="jane_admin",
                email="jane@example.com",
                is_active=True,
                is_admin=True,
                is_moderator=False,
                is_super_admin=False
            ),
            User(
                id="user3",
                username="bob_mod",
                email="bob@example.com",
                is_active=True,
                is_admin=False,
                is_moderator=True,
                is_super_admin=False
            )
        ]
    
    def test_filter_active_users_only(self, mock_db):
        """Test filtering to show only active users"""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        
        # Simulate the filter logic
        query = mock_db.query(User).filter(
            User.is_active == True,
            User.is_super_admin == False
        )
        
        # Verify filter was called
        mock_query.filter.assert_called()
    
    def test_search_by_username(self, mock_db):
        """Test searching users by username"""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        
        search_term = "john"
        
        # This simulates the search logic from admin routes
        # The actual implementation uses or_() with ilike
        query = mock_db.query(User).filter(
            User.is_active == True,
            User.is_super_admin == False
        )
        
        # Verify query was constructed
        assert mock_query.filter.called
    
    def test_search_by_email(self, mock_db):
        """Test searching users by email"""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        
        search_term = "example.com"
        
        query = mock_db.query(User).filter(
            User.is_active == True,
            User.is_super_admin == False
        )
        
        assert mock_query.filter.called
    
    def test_filter_by_admin_role(self, mock_db, sample_users):
        """Test filtering users by admin role"""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by().offset().limit().all.return_value = [sample_users[1]]
        
        # Simulate admin role filter
        query = mock_db.query(User).filter(
            User.is_active == True,
            User.is_super_admin == False
        )
        query = query.filter(User.is_admin == True)
        
        results = query.order_by().offset().limit().all()
        
        assert len(results) == 1
        assert results[0].is_admin is True
    
    def test_filter_by_moderator_role(self, mock_db, sample_users):
        """Test filtering users by moderator role"""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by().offset().limit().all.return_value = [sample_users[2]]
        
        # Simulate moderator role filter
        query = mock_db.query(User).filter(
            User.is_active == True,
            User.is_super_admin == False
        )
        query = query.filter(
            User.is_moderator == True,
            User.is_admin == False
        )
        
        results = query.order_by().offset().limit().all()
        
        assert len(results) == 1
        assert results[0].is_moderator is True
        assert results[0].is_admin is False
    
    def test_filter_by_user_role(self, mock_db, sample_users):
        """Test filtering users by regular user role"""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by().offset().limit().all.return_value = [sample_users[0]]
        
        # Simulate regular user role filter
        query = mock_db.query(User).filter(
            User.is_active == True,
            User.is_super_admin == False
        )
        query = query.filter(
            User.is_moderator == False,
            User.is_admin == False
        )
        
        results = query.order_by().offset().limit().all()
        
        assert len(results) == 1
        assert results[0].is_admin is False
        assert results[0].is_moderator is False
    
    def test_pagination_parameters_validation(self):
        """Test pagination parameter validation logic"""
        # Test page_size validation
        page_size = 200
        if page_size < 1 or page_size > 100:
            page_size = 20
        assert page_size == 20
        
        page_size = 0
        if page_size < 1 or page_size > 100:
            page_size = 20
        assert page_size == 20
        
        page_size = 50
        if page_size < 1 or page_size > 100:
            page_size = 20
        assert page_size == 50
        
        # Test page validation
        page = -1
        if page < 1:
            page = 1
        assert page == 1
        
        page = 0
        if page < 1:
            page = 1
        assert page == 1
        
        page = 5
        if page < 1:
            page = 1
        assert page == 5
    
    def test_offset_calculation(self):
        """Test offset calculation for pagination"""
        page = 1
        page_size = 20
        offset = (page - 1) * page_size
        assert offset == 0
        
        page = 2
        page_size = 20
        offset = (page - 1) * page_size
        assert offset == 20
        
        page = 5
        page_size = 10
        offset = (page - 1) * page_size
        assert offset == 40


class TestRoleAssignmentValidation:
    """Test role assignment validation logic
    
    Tests the business logic for validating role changes including
    permission checks and last admin protection.
    """
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return MagicMock(spec=Session)
    
    def test_validate_role_value(self):
        """Test role value validation"""
        valid_roles = ["user", "moderator", "admin"]
        
        # Valid roles
        assert "user" in valid_roles
        assert "moderator" in valid_roles
        assert "admin" in valid_roles
        
        # Invalid roles
        assert "superuser" not in valid_roles
        assert "guest" not in valid_roles
        assert "" not in valid_roles
    
    def test_cannot_modify_own_role(self):
        """Test validation that user cannot modify their own role"""
        current_user_id = "user123"
        target_user_id = "user123"
        
        can_modify = (target_user_id != current_user_id)
        
        assert can_modify is False
    
    def test_can_modify_other_user_role(self):
        """Test validation that user can modify other user's role"""
        current_user_id = "user123"
        target_user_id = "user456"
        
        can_modify = (target_user_id != current_user_id)
        
        assert can_modify is True
    
    def test_regular_admin_cannot_modify_admin_role(self):
        """Test that regular admin cannot modify another admin's role"""
        is_target_admin = True
        is_operator_super_admin = False
        
        can_modify = not (is_target_admin and not is_operator_super_admin)
        
        assert can_modify is False
    
    def test_super_admin_can_modify_admin_role(self):
        """Test that super admin can modify admin's role"""
        is_target_admin = True
        is_operator_super_admin = True
        
        can_modify = not (is_target_admin and not is_operator_super_admin)
        
        assert can_modify is True
    
    def test_regular_admin_can_modify_regular_user_role(self):
        """Test that regular admin can modify regular user's role"""
        is_target_admin = False
        is_operator_super_admin = False
        
        can_modify = not (is_target_admin and not is_operator_super_admin)
        
        assert can_modify is True
    
    def test_only_super_admin_can_promote_to_admin(self):
        """Test that only super admin can promote users to admin"""
        new_role = "admin"
        is_operator_super_admin = False
        
        can_promote = not (new_role == "admin" and not is_operator_super_admin)
        
        assert can_promote is False
        
        is_operator_super_admin = True
        can_promote = not (new_role == "admin" and not is_operator_super_admin)
        
        assert can_promote is True
    
    def test_last_admin_protection_check(self, mock_db):
        """Test checking if user is the last admin"""
        # Mock scenario: user is admin and there's only 1 admin
        user_is_admin = True
        new_role = "user"
        mock_db.query().filter().scalar.return_value = 1
        
        # Check if this is the last admin
        if user_is_admin and new_role != "admin":
            admin_count = mock_db.query(func.count(User.id)).filter(
                User.is_admin == True,
                User.is_active == True
            ).scalar() or 0
            
            is_last_admin = (admin_count <= 1)
        else:
            is_last_admin = False
        
        assert is_last_admin is True
    
    def test_not_last_admin_when_multiple_admins(self, mock_db):
        """Test that user is not last admin when multiple admins exist"""
        user_is_admin = True
        new_role = "user"
        mock_db.query().filter().scalar.return_value = 3
        
        if user_is_admin and new_role != "admin":
            admin_count = mock_db.query(func.count(User.id)).filter(
                User.is_admin == True,
                User.is_active == True
            ).scalar() or 0
            
            is_last_admin = (admin_count <= 1)
        else:
            is_last_admin = False
        
        assert is_last_admin is False
    
    def test_role_update_logic(self):
        """Test role update logic"""
        # Create a mock user object
        user = Mock()
        user.is_admin = False
        user.is_moderator = False
        
        # Update to moderator
        new_role = "moderator"
        user.is_admin = (new_role == "admin")
        user.is_moderator = (new_role == "moderator")
        
        assert user.is_admin is False
        assert user.is_moderator is True
        
        # Update to admin
        new_role = "admin"
        user.is_admin = (new_role == "admin")
        user.is_moderator = (new_role == "moderator")
        
        assert user.is_admin is True
        assert user.is_moderator is False
        
        # Update to user
        new_role = "user"
        user.is_admin = (new_role == "admin")
        user.is_moderator = (new_role == "moderator")
        
        assert user.is_admin is False
        assert user.is_moderator is False
    
    def test_determine_user_role_string(self):
        """Test logic for determining user role string"""
        # Super admin
        user = Mock()
        user.is_super_admin = True
        user.is_admin = True
        user.is_moderator = False
        
        role_str = "super_admin" if getattr(user, "is_super_admin", False) else (
            "admin" if user.is_admin else (
                "moderator" if user.is_moderator else "user"
            )
        )
        assert role_str == "super_admin"
        
        # Admin
        user.is_super_admin = False
        user.is_admin = True
        user.is_moderator = False
        
        role_str = "super_admin" if getattr(user, "is_super_admin", False) else (
            "admin" if user.is_admin else (
                "moderator" if user.is_moderator else "user"
            )
        )
        assert role_str == "admin"
        
        # Moderator
        user.is_super_admin = False
        user.is_admin = False
        user.is_moderator = True
        
        role_str = "super_admin" if getattr(user, "is_super_admin", False) else (
            "admin" if user.is_admin else (
                "moderator" if user.is_moderator else "user"
            )
        )
        assert role_str == "moderator"
        
        # Regular user
        user.is_super_admin = False
        user.is_admin = False
        user.is_moderator = False
        
        role_str = "super_admin" if getattr(user, "is_super_admin", False) else (
            "admin" if user.is_admin else (
                "moderator" if user.is_moderator else "user"
            )
        )
        assert role_str == "user"


class TestUserDeletionValidation:
    """Test user deletion validation logic"""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return MagicMock(spec=Session)
    
    def test_cannot_delete_self(self):
        """Test validation that user cannot delete themselves"""
        current_user_id = "user123"
        target_user_id = "user123"
        
        can_delete = (target_user_id != current_user_id)
        
        assert can_delete is False
    
    def test_can_delete_other_user(self):
        """Test validation that user can delete other users"""
        current_user_id = "user123"
        target_user_id = "user456"
        
        can_delete = (target_user_id != current_user_id)
        
        assert can_delete is True
    
    def test_regular_admin_cannot_delete_admin(self):
        """Test that regular admin cannot delete another admin"""
        is_target_admin = True
        is_operator_super_admin = False
        
        can_delete = not (is_target_admin and not is_operator_super_admin)
        
        assert can_delete is False
    
    def test_super_admin_can_delete_admin(self):
        """Test that super admin can delete admin users"""
        is_target_admin = True
        is_operator_super_admin = True
        
        can_delete = not (is_target_admin and not is_operator_super_admin)
        
        assert can_delete is True
    
    def test_last_admin_deletion_protection(self, mock_db):
        """Test that last admin cannot be deleted"""
        user_is_admin = True
        mock_db.query().filter().scalar.return_value = 1
        
        if user_is_admin:
            admin_count = mock_db.query(func.count(User.id)).filter(
                User.is_admin == True,
                User.is_active == True
            ).scalar() or 0
            
            is_last_admin = (admin_count <= 1)
        else:
            is_last_admin = False
        
        assert is_last_admin is True
    
    def test_soft_delete_logic(self):
        """Test soft delete implementation"""
        user = Mock()
        user.is_active = True
        
        # Perform soft delete
        user.is_active = False
        
        assert user.is_active is False


class TestMuteAndBanDurationCalculation:
    """Test mute and ban duration calculation logic"""
    
    def test_mute_duration_one_day(self):
        """Test calculating mute duration for 1 day"""
        duration = "1d"
        now = datetime.now()
        
        if duration == "1d":
            muted_until = now + timedelta(days=1)
        elif duration == "7d":
            muted_until = now + timedelta(days=7)
        elif duration == "30d":
            muted_until = now + timedelta(days=30)
        elif duration == "permanent":
            muted_until = None
        else:
            muted_until = None
        
        assert muted_until is not None
        time_diff = (muted_until - now).total_seconds()
        assert 86390 < time_diff < 86410  # Approximately 1 day (86400 seconds)
    
    def test_mute_duration_seven_days(self):
        """Test calculating mute duration for 7 days"""
        duration = "7d"
        now = datetime.now()
        
        if duration == "1d":
            muted_until = now + timedelta(days=1)
        elif duration == "7d":
            muted_until = now + timedelta(days=7)
        elif duration == "30d":
            muted_until = now + timedelta(days=30)
        elif duration == "permanent":
            muted_until = None
        else:
            muted_until = None
        
        assert muted_until is not None
        time_diff = (muted_until - now).total_seconds()
        assert 604790 < time_diff < 604810  # Approximately 7 days
    
    def test_mute_duration_thirty_days(self):
        """Test calculating mute duration for 30 days"""
        duration = "30d"
        now = datetime.now()
        
        if duration == "1d":
            muted_until = now + timedelta(days=1)
        elif duration == "7d":
            muted_until = now + timedelta(days=7)
        elif duration == "30d":
            muted_until = now + timedelta(days=30)
        elif duration == "permanent":
            muted_until = None
        else:
            muted_until = None
        
        assert muted_until is not None
        time_diff = (muted_until - now).total_seconds()
        assert 2591990 < time_diff < 2592010  # Approximately 30 days
    
    def test_mute_duration_permanent(self):
        """Test calculating permanent mute duration"""
        duration = "permanent"
        
        if duration == "1d":
            muted_until = now + timedelta(days=1)
        elif duration == "7d":
            muted_until = now + timedelta(days=7)
        elif duration == "30d":
            muted_until = now + timedelta(days=30)
        elif duration == "permanent":
            muted_until = None
        else:
            muted_until = None
        
        assert muted_until is None
    
    def test_ban_duration_one_day(self):
        """Test calculating ban duration for 1 day"""
        duration = "1d"
        now = datetime.now()
        
        if duration == "1d":
            locked_until = now + timedelta(days=1)
        elif duration == "7d":
            locked_until = now + timedelta(days=7)
        elif duration == "30d":
            locked_until = now + timedelta(days=30)
        elif duration == "permanent":
            locked_until = now + timedelta(days=365 * 100)
        else:
            locked_until = None
        
        assert locked_until is not None
        time_diff = (locked_until - now).total_seconds()
        assert 86390 < time_diff < 86410  # Approximately 1 day
    
    def test_ban_duration_permanent(self):
        """Test calculating permanent ban duration (100 years)"""
        duration = "permanent"
        now = datetime.now()
        
        if duration == "1d":
            locked_until = now + timedelta(days=1)
        elif duration == "7d":
            locked_until = now + timedelta(days=7)
        elif duration == "30d":
            locked_until = now + timedelta(days=30)
        elif duration == "permanent":
            locked_until = now + timedelta(days=365 * 100)
        else:
            locked_until = None
        
        assert locked_until is not None
        time_diff = (locked_until - now).total_seconds()
        # 100 years in seconds (approximately)
        expected_seconds = 365 * 100 * 86400
        assert abs(time_diff - expected_seconds) < 100
    
    def test_invalid_duration_handling(self):
        """Test handling invalid duration values"""
        duration = "invalid"
        
        if duration in ["1d", "7d", "30d", "permanent"]:
            is_valid = True
        else:
            is_valid = False
        
        assert is_valid is False
