"""
Property-Based Test: Parallel Test Suite Isolation

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8**

This test verifies that the test suite maintains proper isolation when running
tests in parallel using pytest-xdist. It checks for:
- Cache isolation between workers
- Transaction management during cleanup
- Dependency override conflicts
- File cleanup race conditions
- Foreign key constraint handling

CRITICAL: This test is EXPECTED TO FAIL on unfixed code - failure confirms the bug exists.
"""

import pytest
import subprocess
import sys
import os
from pathlib import Path
from hypothesis import given, strategies as st, settings, HealthCheck

# Mark all tests in this file as serial
pytestmark = pytest.mark.serial


# ============================================================================
# Property 1: Fault Condition - 并行测试隔离失败
# ============================================================================


@pytest.mark.property
class TestParallelIsolation:
    """
    Test parallel test execution isolation.

    This test runs a subset of the test suite in parallel and verifies that
    all tests pass without state pollution, authentication failures, cleanup
    errors, or foreign key violations.

    NOTE: This test is skipped in the main test suite to avoid conflicts.
    Run it separately using: scripts/run_parallel_isolation_tests.sh
    """

    @pytest.mark.skipif(
        "not config.getoption('--run-parallel-isolation', default=False)",
        reason="Skipped in parallel test suite to avoid nested parallelism. Run with: bash scripts/run_parallel_isolation_tests.sh",
    )
    def test_parallel_execution_isolation(self):
        """
        **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8**

        Test that parallel test execution maintains proper isolation.

        This test runs in a completely separate Python process to avoid
        conflicts with the main test suite's parallel execution.
        """
        # Run in a separate Python process to completely isolate from main test suite
        import subprocess

        # Run a subset of integration tests in parallel in a new process
        test_path = "tests/integration/routes"

        # Use subprocess to run pytest in a completely new Python process
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_path, "-n", "4", "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            # Use a new environment to ensure complete isolation
            env={**os.environ, "PYTEST_CURRENT_TEST": ""},
        )

        output = result.stdout + result.stderr

        # Check for common failure patterns
        failure_indicators = {
            "authentication_failures": "401" in output or "Unauthorized" in output,
            "cleanup_errors": "Error during test_db cleanup" in output,
            "foreign_key_violations": "FOREIGN KEY constraint failed" in output,
            "file_cleanup_failures": "Failed to clean up" in output,
            "transaction_errors": "in_transaction" in output,
        }

        # Extract test counts
        import re

        failed_match = re.search(r"(\d+) failed", output)
        passed_match = re.search(r"(\d+) passed", output)
        error_match = re.search(r"(\d+) error", output)

        failed_count = int(failed_match.group(1)) if failed_match else 0
        passed_count = int(passed_match.group(1)) if passed_match else 0
        error_count = int(error_match.group(1)) if error_match else 0

        # Document the counterexamples found
        counterexamples = []
        if failure_indicators["authentication_failures"]:
            counterexamples.append("Authentication failures (401 errors) - cache pollution")
        if failure_indicators["cleanup_errors"]:
            counterexamples.append("Cleanup errors - transaction management issues")
        if failure_indicators["foreign_key_violations"]:
            counterexamples.append("Foreign key constraint violations - deletion order issues")
        if failure_indicators["file_cleanup_failures"]:
            counterexamples.append("File cleanup failures - race conditions")
        if failure_indicators["transaction_errors"]:
            counterexamples.append("Transaction errors - improper transaction handling")

        # Print diagnostic information
        print(f"\n{'='*70}")
        print("PARALLEL ISOLATION TEST RESULTS (Separate Process)")
        print(f"{'='*70}")
        print(f"Tests run: {passed_count + failed_count + error_count}")
        print(f"Passed: {passed_count}")
        print(f"Failed: {failed_count}")
        print(f"Errors: {error_count}")
        print(f"\nFailure indicators detected:")
        for key, detected in failure_indicators.items():
            status = "✗ DETECTED" if detected else "✓ Not detected"
            print(f"  {key}: {status}")

        if counterexamples:
            print(f"\nCounterexamples found:")
            for i, example in enumerate(counterexamples, 1):
                print(f"  {i}. {example}")

        print(f"{'='*70}\n")

        # ASSERTION: All tests should pass with no failures or errors
        assert failed_count == 0, (
            f"Parallel execution had {failed_count} failures. "
            f"Counterexamples: {', '.join(counterexamples) if counterexamples else 'See output above'}"
        )
        assert error_count == 0, (
            f"Parallel execution had {error_count} errors. "
            f"Counterexamples: {', '.join(counterexamples) if counterexamples else 'See output above'}"
        )

        # Verify no failure indicators were detected
        detected_issues = [k for k, v in failure_indicators.items() if v]
        assert not detected_issues, (
            f"Detected isolation issues: {', '.join(detected_issues)}. "
            f"This indicates state pollution between parallel tests."
        )


@pytest.mark.property
class TestCacheIsolation:
    """
    Test cache isolation between parallel workers.

    This test verifies that password hash cache and database engine cache
    are properly isolated between workers.
    """

    @given(
        num_workers=st.integers(min_value=2, max_value=8),
    )
    @settings(
        max_examples=5, deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture]
    )
    def test_cache_isolation_property(self, num_workers):
        """
        **Validates: Requirements 1.2, 2.2**

        Property: For any number of parallel workers, each worker should have
        isolated cache state.

        This test runs a simple test that uses password hashing (which uses
        the _PASSWORD_HASH_CACHE) in parallel and verifies no cache pollution.

        EXPECTED ON UNFIXED CODE: May fail with authentication errors due to
        cache pollution between workers.
        """
        # Create a minimal test file that uses password hashing
        test_content = '''
import pytest

def test_password_cache_isolation(test_user):
    """Test that uses password hashing via test_user fixture"""
    assert test_user is not None
    assert test_user.email is not None
    assert test_user.hashed_password is not None
'''

        # Write temporary test file
        temp_test_file = Path("tests/temp_cache_test.py")
        temp_test_file.write_text(test_content)

        try:
            # Run the test in parallel
            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(temp_test_file), "-n", str(num_workers), "-v"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            output = result.stdout + result.stderr

            # Check for failures
            import re

            failed_match = re.search(r"(\d+) failed", output)
            failed_count = int(failed_match.group(1)) if failed_match else 0

            # On unfixed code, this may fail due to cache pollution
            assert failed_count == 0, (
                f"Cache isolation test failed with {num_workers} workers. "
                f"This indicates cache pollution between workers."
            )
        finally:
            # Clean up temporary test file
            if temp_test_file.exists():
                temp_test_file.unlink()


@pytest.mark.property
class TestTransactionManagement:
    """
    Test transaction management during test cleanup.

    This test verifies that test_db fixture properly handles active
    transactions during cleanup.
    """

    def test_cleanup_with_active_transaction(self):
        """
        **Validates: Requirements 1.3, 2.3**

        Test that cleanup succeeds even when transactions are active.

        This test creates a scenario where a transaction might be left active
        and verifies that cleanup handles it properly.

        EXPECTED ON UNFIXED CODE: May fail with cleanup errors if transactions
        are not properly rolled back before deletion.
        """
        # Create a test that leaves a transaction in an uncertain state
        test_content = '''
import pytest
from app.models.database import User
import uuid

def test_transaction_cleanup(test_db):
    """Test that creates data but doesn't explicitly commit"""
    # Create a user without explicit commit
    user = User(
        id=str(uuid.uuid4()),
        username=f"txtest_{uuid.uuid4().hex[:8]}",
        email=f"txtest_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="dummy_hash",
        is_active=True,
        is_admin=False,
        is_moderator=False,
        is_super_admin=False,
        password_version=0
    )
    test_db.add(user)
    # Intentionally not committing to test cleanup behavior
    # The test_db fixture should handle this during cleanup
'''

        temp_test_file = Path("tests/temp_transaction_test.py")
        temp_test_file.write_text(test_content)

        try:
            # Run the test in parallel to increase chance of transaction issues
            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(temp_test_file), "-n", "4", "-v", "-s"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            output = result.stdout + result.stderr

            # Check for cleanup errors
            has_cleanup_error = "Error during test_db cleanup" in output
            has_transaction_error = "in_transaction" in output

            assert not has_cleanup_error, (
                "Cleanup failed with active transaction. "
                "test_db fixture should rollback transactions before cleanup."
            )
            assert not has_transaction_error, (
                "Transaction management error detected. " "Transactions should be properly handled during cleanup."
            )
        finally:
            if temp_test_file.exists():
                temp_test_file.unlink()


@pytest.mark.property
class TestForeignKeyHandling:
    """
    Test foreign key constraint handling during cleanup.

    This test verifies that data deletion follows proper foreign key
    dependency order.
    """

    def test_foreign_key_deletion_order(self):
        """
        **Validates: Requirements 1.5, 2.3**

        Test that cleanup deletes data in correct foreign key order.

        This test creates data with foreign key relationships and verifies
        that cleanup succeeds without foreign key violations.

        EXPECTED ON UNFIXED CODE: May fail with foreign key constraint
        violations if deletion order is incorrect.
        """
        # Create a test that creates related data
        test_content = '''
import pytest
import uuid
from datetime import datetime

def test_foreign_key_cleanup(test_db, test_user, factory):
    """Test that creates data with foreign key relationships"""
    # Create a knowledge base (has foreign key to user)
    kb = factory.create_knowledge_base(
        owner_id=test_user.id,
        name=f"Test KB {uuid.uuid4().hex[:8]}",
        description="Test description"
    )
    
    # Create a file (has foreign key to knowledge base)
    kb_file = factory.create_knowledge_base_file(
        knowledge_base_id=kb.id,
        filename=f"test_{uuid.uuid4().hex[:8]}.txt",
        file_path=f"/tmp/test_{uuid.uuid4().hex[:8]}.txt"
    )
    
    # The test_db fixture should clean up in correct order:
    # KnowledgeBaseFile -> KnowledgeBase -> User
    assert kb is not None
    assert kb_file is not None
'''

        temp_test_file = Path("tests/temp_fk_test.py")
        temp_test_file.write_text(test_content)

        try:
            # Run in parallel to increase chance of foreign key issues
            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(temp_test_file), "-n", "4", "-v"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            output = result.stdout + result.stderr

            # Check for foreign key violations
            has_fk_violation = "FOREIGN KEY constraint failed" in output

            assert not has_fk_violation, (
                "Foreign key constraint violation during cleanup. "
                "Deletion order should respect foreign key dependencies."
            )
        finally:
            if temp_test_file.exists():
                temp_test_file.unlink()


@pytest.mark.property
class TestDependencyOverrideIsolation:
    """
    Test dependency injection override isolation.

    This test verifies that parallel tests using authenticated clients
    don't interfere with each other's dependency overrides.

    NOTE: This test is skipped in the main test suite to avoid conflicts.
    Run it separately using: scripts/run_parallel_isolation_tests.sh
    """

    @pytest.mark.skipif(
        "not config.getoption('--run-parallel-isolation', default=False)",
        reason="Skipped in parallel test suite to avoid nested parallelism. Run with: bash scripts/run_parallel_isolation_tests.sh",
    )
    def test_authenticated_client_isolation(self):
        """
        **Validates: Requirements 1.4, 1.6, 2.4, 2.6**

        Test that parallel authenticated_client fixtures don't interfere.

        This test runs in a completely separate Python process to avoid
        conflicts with the main test suite's parallel execution.
        """
        # Create tests that use authenticated_client
        test_content = '''
import pytest

def test_auth_client_1(authenticated_client):
    """Test using authenticated client"""
    response = authenticated_client.get("/api/users/me")
    assert response.status_code == 200

def test_auth_client_2(authenticated_client):
    """Test using authenticated client"""
    response = authenticated_client.get("/api/users/me")
    assert response.status_code == 200

def test_auth_client_3(authenticated_client):
    """Test using authenticated client"""
    response = authenticated_client.get("/api/users/me")
    assert response.status_code == 200

def test_auth_client_4(authenticated_client):
    """Test using authenticated client"""
    response = authenticated_client.get("/api/users/me")
    assert response.status_code == 200
'''

        temp_test_file = Path("tests/temp_auth_client_test.py")
        temp_test_file.write_text(test_content)

        try:
            # Run in a separate Python process to completely isolate from main test suite
            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(temp_test_file), "-n", "4", "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=60,
                # Use a new environment to ensure complete isolation
                env={**os.environ, "PYTEST_CURRENT_TEST": ""},
            )

            output = result.stdout + result.stderr

            # Check for authentication failures
            has_auth_failure = "401" in output or "Unauthorized" in output

            import re

            failed_match = re.search(r"(\d+) failed", output)
            passed_match = re.search(r"(\d+) passed", output)

            failed_count = int(failed_match.group(1)) if failed_match else 0
            passed_count = int(passed_match.group(1)) if passed_match else 0

            # Print diagnostic information
            print(f"\n{'='*70}")
            print("AUTHENTICATED CLIENT ISOLATION TEST RESULTS (Separate Process)")
            print(f"{'='*70}")
            print(f"Tests run: {passed_count + failed_count}")
            print(f"Passed: {passed_count}")
            print(f"Failed: {failed_count}")
            print(f"Authentication failures detected: {'Yes' if has_auth_failure else 'No'}")
            print(f"{'='*70}\n")

            assert failed_count == 0, (
                f"Authenticated client tests failed ({failed_count} failures). "
                f"This indicates dependency override conflicts."
            )
            assert not has_auth_failure, (
                "Authentication failures detected. "
                "This indicates dependency injection conflicts between parallel tests."
            )
        finally:
            if temp_test_file.exists():
                temp_test_file.unlink()


if __name__ == "__main__":
    # Run this test file directly to see the bug in action
    pytest.main([__file__, "-v", "-s"])
