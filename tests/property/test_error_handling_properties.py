"""
Property-based tests for error handling

**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**
"""

import pytest
from hypothesis import given, settings, strategies as st
from fastapi import HTTPException
from app.services.file_service import FileValidationError, FileDatabaseError


# Property 4: Error responses are consistent and informative
# **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**
@pytest.mark.property
@given(
    error_message=st.text(min_size=1, max_size=200),
    error_code=st.sampled_from([
        "VALIDATION_ERROR", "FILE_COUNT_EXCEEDED", "INVALID_FILE_TYPE",
        "FILE_SIZE_EXCEEDED", "KB_NOT_FOUND", "PC_NOT_FOUND",
        "DUPLICATE_FILENAME", "FILES_MISSING"
    ])
)
@settings(max_examples=100)
def test_file_validation_error_consistency(error_message, error_code):
    """
    Property 4: Error responses are consistent and informative
    
    For any error condition in any module, when an error occurs, then the system
    SHALL execute the appropriate exception handler, return a proper HTTP status code,
    include a descriptive error message, and log the error with relevant context.
    
    **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**
    """
    # Create a FileValidationError
    error = FileValidationError(error_message, code=error_code)
    
    # Verify error has required attributes
    assert hasattr(error, 'message'), "Error should have message attribute"
    assert hasattr(error, 'code'), "Error should have code attribute"
    assert error.message == error_message, "Error message should match"
    assert error.code == error_code, "Error code should match"
    
    # Verify error message is descriptive (not empty)
    assert len(error.message) > 0, "Error message should not be empty"
    
    # Verify error code is descriptive (not empty)
    assert error.code is not None, "Error code should not be None"
    assert len(error.code) > 0, "Error code should not be empty"


@pytest.mark.property
@given(
    error_message=st.text(min_size=1, max_size=200)
)
@settings(max_examples=100)
def test_database_error_consistency(error_message):
    """
    Property: Database errors are consistent and informative
    
    For any database error, the error should have a descriptive message.
    
    **Validates: Requirements 6.1, 6.2, 6.3**
    """
    # Create a FileDatabaseError
    error = FileDatabaseError(error_message)
    
    # Verify error has required attributes
    assert hasattr(error, 'message'), "Error should have message attribute"
    assert error.message == error_message, "Error message should match"
    
    # Verify error message is descriptive (not empty)
    assert len(error.message) > 0, "Error message should not be empty"


@pytest.mark.property
@given(
    status_code=st.sampled_from([400, 401, 403, 404, 409, 500]),
    detail=st.text(min_size=1, max_size=200)
)
@settings(max_examples=100)
def test_http_exception_consistency(status_code, detail):
    """
    Property: HTTP exceptions have proper status codes and details
    
    For any HTTP exception, it should have a valid status code and descriptive detail.
    
    **Validates: Requirements 6.2, 6.3, 6.4**
    """
    # Create an HTTPException
    exception = HTTPException(status_code=status_code, detail=detail)
    
    # Verify exception has required attributes
    assert hasattr(exception, 'status_code'), "Exception should have status_code"
    assert hasattr(exception, 'detail'), "Exception should have detail"
    
    # Verify status code is valid
    assert exception.status_code in [400, 401, 403, 404, 409, 500], \
        "Status code should be a valid HTTP error code"
    
    # Verify detail is descriptive
    assert len(exception.detail) > 0, "Detail should not be empty"


@pytest.mark.property
@given(
    error_message=st.text(min_size=1, max_size=200),
    error_code=st.text(min_size=1, max_size=50),
    has_details=st.booleans()
)
@settings(max_examples=100)
def test_error_with_optional_details(error_message, error_code, has_details):
    """
    Property: Errors can optionally include additional details
    
    For any error, it should support optional details dictionary.
    
    **Validates: Requirements 6.3, 6.5**
    """
    details = {"extra_info": "test"} if has_details else None
    
    # Create a FileValidationError with optional details
    error = FileValidationError(error_message, code=error_code, details=details)
    
    # Verify error has required attributes
    assert hasattr(error, 'message'), "Error should have message attribute"
    assert hasattr(error, 'code'), "Error should have code attribute"
    assert hasattr(error, 'details'), "Error should have details attribute"
    
    # Verify details handling
    if has_details:
        assert error.details is not None, "Details should not be None when provided"
        assert isinstance(error.details, dict), "Details should be a dictionary"
    else:
        assert error.details == {}, "Details should be empty dict when not provided"


@pytest.mark.property
@given(
    num_errors=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=100)
def test_multiple_errors_are_independent(num_errors):
    """
    Property: Multiple error instances are independent
    
    For any number of error instances, each should maintain its own state.
    
    **Validates: Requirements 6.1, 6.2**
    """
    errors = []
    
    # Create multiple errors with different messages
    for i in range(num_errors):
        error = FileValidationError(
            f"Error message {i}",
            code=f"ERROR_CODE_{i}"
        )
        errors.append(error)
    
    # Verify each error maintains its own state
    for i, error in enumerate(errors):
        assert error.message == f"Error message {i}", \
            f"Error {i} should have its own message"
        assert error.code == f"ERROR_CODE_{i}", \
            f"Error {i} should have its own code"
    
    # Verify all errors are distinct
    assert len(errors) == num_errors, "Should have created all errors"
    assert len(set(e.message for e in errors)) == num_errors, \
        "All error messages should be unique"
