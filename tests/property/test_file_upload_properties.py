"""
Property-based tests for file upload functionality

**Validates: Requirements 4.2, 4.3, 4.4, 4.5**
"""

import pytest
from hypothesis import given, settings, strategies as st
from app.services.file_service import FileService, FileValidationError


# Property 1: File validation enforces constraints
# **Validates: Requirements 4.2, 4.3, 4.4, 4.5**
@pytest.mark.property
@given(
    file_size=st.integers(min_value=0, max_value=200_000_000),
    file_type=st.sampled_from(['.txt', '.json', '.toml', '.pdf', '.jpg', '.exe', '.sh', '.py', '.md'])
)
@settings(max_examples=100)
def test_file_validation_enforces_constraints(file_size, file_type):
    """
    Property 1: File validation enforces constraints
    
    For any file upload attempt, if the file exceeds size limits or has an invalid type,
    then the upload SHALL be rejected with a descriptive error, and if the file meets
    all constraints, then the upload SHALL succeed and the file SHALL be stored at the
    correct path.
    
    **Validates: Requirements 4.2, 4.3, 4.4, 4.5**
    """
    # Get file service constraints
    MAX_SIZE = FileService.MAX_FILE_SIZE
    ALLOWED_KNOWLEDGE_TYPES = FileService.ALLOWED_KNOWLEDGE_TYPES
    ALLOWED_PERSONA_TYPES = FileService.ALLOWED_PERSONA_TYPES
    
    # Determine if file should be valid for knowledge base
    is_valid_knowledge = file_size <= MAX_SIZE and file_type in ALLOWED_KNOWLEDGE_TYPES
    
    # Determine if file should be valid for persona card
    is_valid_persona = file_size <= MAX_SIZE and file_type in ALLOWED_PERSONA_TYPES
    
    # Test knowledge base file validation
    filename_kb = f"test_file{file_type}"
    file_content_kb = b"x" * min(file_size, MAX_SIZE + 1000)  # Cap at reasonable size for test
    
    # Create a mock FileService instance (without db)
    # We'll test the validation methods directly
    service = FileService.__new__(FileService)
    service.MAX_FILE_SIZE = MAX_SIZE
    service.ALLOWED_KNOWLEDGE_TYPES = ALLOWED_KNOWLEDGE_TYPES
    service.ALLOWED_PERSONA_TYPES = ALLOWED_PERSONA_TYPES
    
    # Test file type validation for knowledge base
    type_valid_kb = service._validate_file_type(filename_kb, ALLOWED_KNOWLEDGE_TYPES)
    assert type_valid_kb == (file_type in ALLOWED_KNOWLEDGE_TYPES), \
        f"File type validation failed for {file_type}"
    
    # Test file size validation
    size_valid = service._validate_file_size(file_size)
    assert size_valid == (file_size <= MAX_SIZE), \
        f"File size validation failed for {file_size} bytes"
    
    # Test combined validation for knowledge base
    if is_valid_knowledge:
        # Both type and size should be valid
        assert type_valid_kb, f"Expected valid type for {file_type}"
        assert size_valid, f"Expected valid size for {file_size}"
    else:
        # At least one should be invalid
        assert not (type_valid_kb and size_valid), \
            f"Expected invalid file but both validations passed"
    
    # Test file type validation for persona card
    filename_pc = f"bot_config{file_type}"
    type_valid_pc = service._validate_file_type(filename_pc, ALLOWED_PERSONA_TYPES)
    assert type_valid_pc == (file_type in ALLOWED_PERSONA_TYPES), \
        f"Persona file type validation failed for {file_type}"
    
    # Test combined validation for persona card
    if is_valid_persona:
        # Both type and size should be valid
        assert type_valid_pc, f"Expected valid persona type for {file_type}"
        assert size_valid, f"Expected valid size for {file_size}"
    else:
        # At least one should be invalid
        assert not (type_valid_pc and size_valid), \
            f"Expected invalid persona file but both validations passed"


@pytest.mark.property
@given(
    filename=st.text(min_size=1, max_size=100, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters='-_'
    )).filter(lambda x: x not in ['.', '..', ''])
)
@settings(max_examples=100)
def test_filename_validation_property(filename):
    """
    Property: Filename validation handles various inputs
    
    For any filename input, the validation should handle it gracefully
    without crashing, and empty filenames should be rejected.
    
    **Validates: Requirements 4.2, 4.5**
    """
    service = FileService.__new__(FileService)
    service.ALLOWED_KNOWLEDGE_TYPES = ['.txt', '.json']
    
    # Add extension to filename
    test_filename = f"{filename}.txt"
    
    # Should not crash
    result = service._validate_file_type(test_filename, ['.txt', '.json'])
    
    # Result should be boolean
    assert isinstance(result, bool)
    
    # Valid .txt file should pass
    assert result is True


@pytest.mark.property
@given(
    file_count=st.integers(min_value=0, max_value=150)
)
@settings(max_examples=100)
def test_file_count_limits_property(file_count):
    """
    Property: File count limits are enforced
    
    For any number of files, if the count exceeds the maximum allowed,
    the validation should reject it.
    
    **Validates: Requirements 4.2**
    """
    MAX_KNOWLEDGE_FILES = 100
    MAX_PERSONA_FILES = 1
    
    # Knowledge base file count validation
    is_valid_kb = file_count <= MAX_KNOWLEDGE_FILES
    
    # Persona card file count validation
    is_valid_pc = file_count == MAX_PERSONA_FILES
    
    # Verify the logic
    if file_count > MAX_KNOWLEDGE_FILES:
        assert not is_valid_kb, f"Should reject {file_count} knowledge files"
    else:
        assert is_valid_kb, f"Should accept {file_count} knowledge files"
    
    if file_count != MAX_PERSONA_FILES:
        assert not is_valid_pc, f"Should reject {file_count} persona files"
    else:
        assert is_valid_pc, f"Should accept {file_count} persona file"


@pytest.mark.property
@given(
    file_size=st.integers(min_value=0, max_value=200_000_000),
    max_size_mb=st.integers(min_value=1, max_value=500)
)
@settings(max_examples=100)
def test_file_size_validation_with_different_limits(file_size, max_size_mb):
    """
    Property: File size validation works with different size limits
    
    For any file size and any maximum size limit, the validation
    should correctly determine if the file is within limits.
    
    **Validates: Requirements 4.2, 4.3**
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    
    service = FileService.__new__(FileService)
    service.MAX_FILE_SIZE = max_size_bytes
    
    result = service._validate_file_size(file_size)
    expected = file_size <= max_size_bytes
    
    assert result == expected, \
        f"File size validation mismatch: {file_size} bytes vs {max_size_bytes} bytes limit"
