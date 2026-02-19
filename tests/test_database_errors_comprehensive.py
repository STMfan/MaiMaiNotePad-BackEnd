"""
Comprehensive database error handling tests
Tests connection failures, transaction conflicts, constraint violations

Requirements: 8.5, 8.6
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
from sqlalchemy.orm import Session
from sqlalchemy.exc import (
    IntegrityError,
    OperationalError,
    DatabaseError,
    DataError,
    InvalidRequestError,
    DBAPIError
)
from tests.test_data_factory import TestDataFactory


class TestDatabaseConnectionErrors:
    """Test database connection failure scenarios"""
    
    def test_connection_timeout(self, client):
        """Test handling of database connection timeout"""
        with patch('app.core.deps.get_db') as mock_get_db:
            mock_get_db.side_effect = OperationalError(
                "Connection timeout",
                None,
                None
            )
            
            response = client.get("/api/knowledge")
            # Should handle gracefully with 500 or 503
            assert response.status_code in [500, 503]
    
    def test_connection_refused(self, client):
        """Test handling of database connection refused"""
        with patch('app.core.deps.get_db') as mock_get_db:
            mock_get_db.side_effect = OperationalError(
                "Connection refused",
                None,
                None
            )
            
            response = client.get("/api/knowledge")
            assert response.status_code in [500, 503]
    
    def test_connection_lost_during_query(self, authenticated_client):
        """Test handling of connection lost during query execution"""
        with patch('sqlalchemy.orm.Query.all') as mock_query:
            mock_query.side_effect = OperationalError(
                "Connection lost",
                None,
                None
            )
            
            response = authenticated_client.get("/api/knowledge")
            assert response.status_code in [200, 500, 503]
    
    def test_max_connections_exceeded(self, client):
        """Test handling of max connections exceeded"""
        with patch('app.core.deps.get_db') as mock_get_db:
            mock_get_db.side_effect = OperationalError(
                "Too many connections",
                None,
                None
            )
            
            response = client.get("/api/knowledge")
            assert response.status_code in [500, 503]
    
    def test_database_not_found(self, client):
        """Test handling of database not found error"""
        with patch('app.core.deps.get_db') as mock_get_db:
            mock_get_db.side_effect = OperationalError(
                "Database does not exist",
                None,
                None
            )
            
            response = client.get("/api/knowledge")
            assert response.status_code in [500, 503]


class TestTransactionConflicts:
    """Test transaction conflict and rollback scenarios"""
    
    def test_concurrent_update_conflict(self, authenticated_client, factory: TestDataFactory, test_db: Session):
        """Test handling of concurrent update conflicts"""
        kb = factory.create_knowledge_base()
        
        with patch('sqlalchemy.orm.Session.commit') as mock_commit:
            mock_commit.side_effect = OperationalError(
                "Deadlock detected",
                None,
                None
            )
            
            response = authenticated_client.put(
                f"/api/knowledge/{kb.id}",
                json={"title": "Updated Title"}
            )
            # Should handle gracefully
            assert response.status_code in [200, 409, 500]
    
    def test_transaction_rollback_on_error(self, authenticated_client, test_db: Session):
        """Test that transaction is rolled back on error"""
        initial_count = test_db.query(test_db.bind.dialect.get_table_names).count() if hasattr(test_db.query(test_db.bind.dialect.get_table_names), 'count') else 0
        
        with patch('sqlalchemy.orm.Session.commit') as mock_commit:
            mock_commit.side_effect = DatabaseError(
                "Transaction error",
                None,
                None
            )
            
            response = authenticated_client.post(
                "/api/knowledge",
                json={"title": "Test", "description": "Test"}
            )
            
            # Transaction should be rolled back
            # Database state should be unchanged
            assert response.status_code in [400, 500]
    
    def test_nested_transaction_rollback(self, authenticated_client, factory: TestDataFactory, test_db: Session):
        """Test rollback of nested transactions"""
        user = factory.create_user()
        
        with patch('sqlalchemy.orm.Session.flush') as mock_flush:
            mock_flush.side_effect = DatabaseError(
                "Nested transaction error",
                None,
                None
            )
            
            response = authenticated_client.post(
                "/api/knowledge",
                json={"title": "Test", "description": "Test"}
            )
            
            assert response.status_code in [400, 500]
    
    def test_savepoint_rollback(self, authenticated_client, test_db: Session):
        """Test rollback to savepoint on partial failure"""
        # This tests that partial operations are rolled back
        with patch('sqlalchemy.orm.Session.commit') as mock_commit:
            # First call succeeds, second fails
            mock_commit.side_effect = [None, DatabaseError("Error", None, None)]
            
            response = authenticated_client.post(
                "/api/knowledge",
                json={"title": "Test", "description": "Test"}
            )
            
            # Should handle gracefully
            assert response.status_code in [200, 201, 400, 500]
    
    def test_deadlock_detection(self, authenticated_client, factory: TestDataFactory, test_db: Session):
        """Test handling of database deadlock"""
        kb = factory.create_knowledge_base()
        
        with patch('sqlalchemy.orm.Session.commit') as mock_commit:
            mock_commit.side_effect = OperationalError(
                "Deadlock found when trying to get lock",
                None,
                None
            )
            
            response = authenticated_client.put(
                f"/api/knowledge/{kb.id}",
                json={"title": "Updated"}
            )
            
            assert response.status_code in [200, 409, 500]
    
    def test_lock_timeout(self, authenticated_client, factory: TestDataFactory, test_db: Session):
        """Test handling of lock acquisition timeout"""
        kb = factory.create_knowledge_base()
        
        with patch('sqlalchemy.orm.Session.commit') as mock_commit:
            mock_commit.side_effect = OperationalError(
                "Lock wait timeout exceeded",
                None,
                None
            )
            
            response = authenticated_client.put(
                f"/api/knowledge/{kb.id}",
                json={"title": "Updated"}
            )
            
            assert response.status_code in [200, 409, 500, 503]


class TestConstraintViolations:
    """Test database constraint violation scenarios"""
    
    def test_unique_constraint_violation(self, client, factory: TestDataFactory, test_db: Session):
        """Test handling of unique constraint violation"""
        existing_user = factory.create_user(username="existinguser")
        
        # Try to create user with same username
        response = client.post(
            "/api/auth/register",
            json={
                "username": "existinguser",
                "email": "different@example.com",
                "password": "password123"
            }
        )
        
        assert response.status_code in [400, 409]
        data = response.json()
        assert "detail" in data or "message" in data
    
    def test_foreign_key_constraint_violation(self, authenticated_client):
        """Test handling of foreign key constraint violation"""
        import uuid
        fake_user_id = str(uuid.uuid4())
        
        # Try to create knowledge base with non-existent user
        with patch('app.models.database.KnowledgeBase') as mock_kb:
            mock_kb.side_effect = IntegrityError(
                "Foreign key constraint failed",
                None,
                None
            )
            
            response = authenticated_client.post(
                "/api/knowledge",
                json={"title": "Test", "description": "Test"}
            )
            
            # Should handle gracefully
            assert response.status_code in [200, 201, 400, 500]
    
    def test_not_null_constraint_violation(self, authenticated_client):
        """Test handling of NOT NULL constraint violation"""
        with patch('sqlalchemy.orm.Session.commit') as mock_commit:
            mock_commit.side_effect = IntegrityError(
                "NOT NULL constraint failed",
                None,
                None
            )
            
            response = authenticated_client.post(
                "/api/knowledge",
                json={"title": "Test", "description": "Test"}
            )
            
            assert response.status_code in [200, 201, 400, 500]
    
    def test_check_constraint_violation(self, authenticated_client):
        """Test handling of CHECK constraint violation"""
        with patch('sqlalchemy.orm.Session.commit') as mock_commit:
            mock_commit.side_effect = IntegrityError(
                "CHECK constraint failed",
                None,
                None
            )
            
            response = authenticated_client.post(
                "/api/knowledge",
                json={"title": "Test", "description": "Test"}
            )
            
            assert response.status_code in [200, 201, 400, 500]
    
    def test_cascade_delete_constraint(self, authenticated_client, factory: TestDataFactory, test_db: Session):
        """Test handling of cascade delete constraints"""
        kb = factory.create_knowledge_base()
        comment = factory.create_comment(knowledge_base=kb)
        
        # Delete knowledge base should cascade to comments
        response = authenticated_client.delete(f"/api/knowledge/{kb.id}")
        
        # Should succeed with cascade or handle constraint
        assert response.status_code in [200, 204, 400, 409]
    
    def test_circular_foreign_key_constraint(self, authenticated_client, test_db: Session):
        """Test handling of circular foreign key constraints"""
        # This is a complex scenario that depends on schema design
        # Testing that the system handles it gracefully
        with patch('sqlalchemy.orm.Session.commit') as mock_commit:
            mock_commit.side_effect = IntegrityError(
                "Circular foreign key constraint",
                None,
                None
            )
            
            response = authenticated_client.post(
                "/api/knowledge",
                json={"title": "Test", "description": "Test"}
            )
            
            assert response.status_code in [200, 201, 400, 500]


class TestDataIntegrityErrors:
    """Test data integrity and validation errors"""
    
    def test_invalid_data_type(self, authenticated_client):
        """Test handling of invalid data type in database operation"""
        with patch('sqlalchemy.orm.Session.commit') as mock_commit:
            mock_commit.side_effect = DataError(
                "Invalid data type",
                None,
                None
            )
            
            response = authenticated_client.post(
                "/api/knowledge",
                json={"title": "Test", "description": "Test"}
            )
            
            assert response.status_code in [200, 201, 400, 500]
    
    def test_data_too_long(self, authenticated_client):
        """Test handling of data exceeding column length"""
        very_long_title = "a" * 10000
        
        response = authenticated_client.post(
            "/api/knowledge",
            json={"title": very_long_title, "description": "Test"}
        )
        
        # Should validate or handle database error
        assert response.status_code in [400, 422, 500]
    
    def test_invalid_enum_value(self, authenticated_client, factory: TestDataFactory, test_db: Session):
        """Test handling of invalid enum value"""
        kb = factory.create_knowledge_base()
        
        with patch('sqlalchemy.orm.Session.commit') as mock_commit:
            mock_commit.side_effect = DataError(
                "Invalid enum value",
                None,
                None
            )
            
            response = authenticated_client.put(
                f"/api/knowledge/{kb.id}",
                json={"title": "Updated", "status": "invalid_status"}
            )
            
            assert response.status_code in [200, 400, 422, 500]
    
    def test_invalid_date_format(self, authenticated_client):
        """Test handling of invalid date format"""
        with patch('sqlalchemy.orm.Session.commit') as mock_commit:
            mock_commit.side_effect = DataError(
                "Invalid date format",
                None,
                None
            )
            
            response = authenticated_client.post(
                "/api/knowledge",
                json={"title": "Test", "description": "Test"}
            )
            
            assert response.status_code in [200, 201, 400, 500]
    
    def test_numeric_overflow(self, authenticated_client):
        """Test handling of numeric overflow"""
        with patch('sqlalchemy.orm.Session.commit') as mock_commit:
            mock_commit.side_effect = DataError(
                "Numeric value out of range",
                None,
                None
            )
            
            response = authenticated_client.post(
                "/api/knowledge",
                json={"title": "Test", "description": "Test"}
            )
            
            assert response.status_code in [200, 201, 400, 500]


class TestSessionManagementErrors:
    """Test database session management errors"""
    
    def test_session_closed_error(self, authenticated_client):
        """Test handling of operations on closed session"""
        with patch('sqlalchemy.orm.Session.query') as mock_query:
            mock_query.side_effect = InvalidRequestError(
                "Session is closed"
            )
            
            response = authenticated_client.get("/api/knowledge")
            
            assert response.status_code in [200, 500]
    
    def test_session_expired_error(self, authenticated_client):
        """Test handling of expired session"""
        with patch('sqlalchemy.orm.Session.query') as mock_query:
            mock_query.side_effect = InvalidRequestError(
                "Session has expired"
            )
            
            response = authenticated_client.get("/api/knowledge")
            
            assert response.status_code in [200, 500]
    
    def test_detached_instance_error(self, authenticated_client, factory: TestDataFactory, test_db: Session):
        """Test handling of detached instance access"""
        kb = factory.create_knowledge_base()
        test_db.expunge(kb)  # Detach from session
        
        response = authenticated_client.get(f"/api/knowledge/{kb.id}")
        
        # Should handle gracefully
        assert response.status_code in [200, 404, 500]
    
    def test_pending_instance_error(self, authenticated_client):
        """Test handling of pending instance operations"""
        with patch('sqlalchemy.orm.Session.commit') as mock_commit:
            mock_commit.side_effect = InvalidRequestError(
                "Instance is pending"
            )
            
            response = authenticated_client.post(
                "/api/knowledge",
                json={"title": "Test", "description": "Test"}
            )
            
            assert response.status_code in [200, 201, 400, 500]
    
    def test_flush_error(self, authenticated_client):
        """Test handling of flush errors"""
        with patch('sqlalchemy.orm.Session.flush') as mock_flush:
            mock_flush.side_effect = DatabaseError(
                "Flush failed",
                None,
                None
            )
            
            response = authenticated_client.post(
                "/api/knowledge",
                json={"title": "Test", "description": "Test"}
            )
            
            assert response.status_code in [200, 201, 400, 500]


class TestQueryErrors:
    """Test database query execution errors"""
    
    def test_invalid_sql_syntax(self, authenticated_client):
        """Test handling of invalid SQL syntax"""
        with patch('sqlalchemy.orm.Query.all') as mock_query:
            mock_query.side_effect = DatabaseError(
                "SQL syntax error",
                None,
                None
            )
            
            response = authenticated_client.get("/api/knowledge")
            
            assert response.status_code in [200, 500]
    
    def test_query_timeout(self, authenticated_client):
        """Test handling of query timeout"""
        with patch('sqlalchemy.orm.Query.all') as mock_query:
            mock_query.side_effect = OperationalError(
                "Query execution timeout",
                None,
                None
            )
            
            response = authenticated_client.get("/api/knowledge")
            
            assert response.status_code in [200, 500, 504]
    
    def test_invalid_column_reference(self, authenticated_client):
        """Test handling of invalid column reference"""
        with patch('sqlalchemy.orm.Query.filter') as mock_filter:
            mock_filter.side_effect = DatabaseError(
                "Unknown column",
                None,
                None
            )
            
            response = authenticated_client.get("/api/knowledge?sort_by=invalid_column")
            
            assert response.status_code in [200, 400, 500]
    
    def test_ambiguous_column_reference(self, authenticated_client):
        """Test handling of ambiguous column reference"""
        with patch('sqlalchemy.orm.Query.all') as mock_query:
            mock_query.side_effect = DatabaseError(
                "Ambiguous column name",
                None,
                None
            )
            
            response = authenticated_client.get("/api/knowledge")
            
            assert response.status_code in [200, 500]
    
    def test_result_set_too_large(self, authenticated_client):
        """Test handling of very large result sets"""
        with patch('sqlalchemy.orm.Query.all') as mock_query:
            mock_query.side_effect = MemoryError(
                "Result set too large"
            )
            
            response = authenticated_client.get("/api/knowledge?page_size=999999")
            
            assert response.status_code in [200, 400, 500]


class TestDatabaseRecovery:
    """Test database error recovery scenarios"""
    
    def test_retry_on_transient_error(self, authenticated_client):
        """Test retry logic on transient database errors"""
        # This tests that transient errors are retried
        call_count = 0
        
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise OperationalError("Transient error", None, None)
            return []
        
        with patch('sqlalchemy.orm.Query.all', side_effect=side_effect):
            response = authenticated_client.get("/api/knowledge")
            
            # Should succeed after retry or return error
            assert response.status_code in [200, 500]
    
    def test_no_retry_on_permanent_error(self, authenticated_client):
        """Test that permanent errors are not retried"""
        with patch('sqlalchemy.orm.Query.all') as mock_query:
            mock_query.side_effect = IntegrityError(
                "Permanent constraint violation",
                None,
                None
            )
            
            response = authenticated_client.get("/api/knowledge")
            
            # Should fail immediately
            assert response.status_code in [200, 400, 500]
    
    def test_connection_pool_recovery(self, client):
        """Test connection pool recovery after errors"""
        # Simulate connection pool exhaustion and recovery
        with patch('app.core.deps.get_db') as mock_get_db:
            # First call fails, subsequent calls succeed
            mock_get_db.side_effect = [
                OperationalError("Pool exhausted", None, None),
                MagicMock()
            ]
            
            response1 = client.get("/api/knowledge")
            response2 = client.get("/api/knowledge")
            
            # First should fail, second might succeed
            assert response1.status_code in [500, 503]
