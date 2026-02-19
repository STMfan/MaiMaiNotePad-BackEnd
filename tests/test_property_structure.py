"""
Property-based tests for backend structure refactor.

Feature: backend-structure-refactor
"""

import os
from pathlib import Path
from hypothesis import given, strategies as st, settings, HealthCheck
import pytest


# Feature: backend-structure-refactor, Property 1: 目录结构完整性
# **Validates: Requirements 1.1, 1.2, 1.5, 2.1, 4.1, 5.1, 6.1**


# Get project root once at module level
PROJECT_ROOT = Path(__file__).parent.parent


class TestDirectoryStructureIntegrity:
    """Test Property 1: Directory structure integrity.
    
    For any required directory (app/, app/api/, app/core/, app/models/, 
    app/services/, app/utils/, tests/, alembic/), that directory should 
    exist in the refactored project.
    """
    
    @pytest.fixture
    def project_root(self):
        """Get the project root directory."""
        return PROJECT_ROOT
    
    @pytest.fixture
    def required_directories(self):
        """List of required directories in the refactored structure."""
        return [
            "app",
            "app/api",
            "app/api/routes",
            "app/core",
            "app/models",
            "app/services",
            "app/utils",
            "tests",
            "alembic",
        ]
    
    def test_all_required_directories_exist(self, project_root, required_directories):
        """Test that all required directories exist."""
        for directory in required_directories:
            dir_path = project_root / directory
            assert dir_path.exists(), f"Required directory {directory} does not exist"
            assert dir_path.is_dir(), f"Required path {directory} is not a directory"
    
    @given(st.sampled_from([
        "app",
        "app/api",
        "app/api/routes",
        "app/core",
        "app/models",
        "app/services",
        "app/utils",
        "tests",
        "alembic",
    ]))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_required_directory_exists(self, directory):
        """Property test: For any required directory, it should exist.
        
        This property verifies that the refactored project structure contains
        all necessary directories as specified in the design.
        """
        dir_path = PROJECT_ROOT / directory
        
        # Property: The directory must exist
        assert dir_path.exists(), (
            f"Property violation: Required directory '{directory}' does not exist. "
            f"Expected path: {dir_path}"
        )
        
        # Property: The path must be a directory, not a file
        assert dir_path.is_dir(), (
            f"Property violation: Required path '{directory}' exists but is not a directory. "
            f"Path: {dir_path}"
        )



# Feature: backend-structure-refactor, Property 2: 模块初始化文件存在性
# **Validates: Requirements 2.4**


class TestModuleInitializationFiles:
    """Test Property 2: Module initialization file existence.
    
    For any Python package directory (app/ and its subdirectories), 
    it should contain an __init__.py file to control the module's public interface.
    """
    
    @pytest.fixture
    def project_root(self):
        """Get the project root directory."""
        return PROJECT_ROOT
    
    @pytest.fixture
    def python_package_directories(self):
        """List of Python package directories that should have __init__.py."""
        return [
            "app",
            "app/api",
            "app/api/routes",
            "app/core",
            "app/models",
            "app/services",
            "app/utils",
            "tests",
        ]
    
    def test_all_package_directories_have_init_files(self, project_root, python_package_directories):
        """Test that all package directories have __init__.py files."""
        for directory in python_package_directories:
            init_file = project_root / directory / "__init__.py"
            assert init_file.exists(), f"Package directory {directory} is missing __init__.py"
            assert init_file.is_file(), f"Path {directory}/__init__.py exists but is not a file"
    
    @given(st.sampled_from([
        "app",
        "app/api",
        "app/api/routes",
        "app/core",
        "app/models",
        "app/services",
        "app/utils",
        "tests",
    ]))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_package_has_init_file(self, directory):
        """Property test: For any Python package directory, __init__.py should exist.
        
        This property verifies that all Python package directories contain
        __init__.py files to properly control module interfaces.
        """
        init_file = PROJECT_ROOT / directory / "__init__.py"
        
        # Property: The __init__.py file must exist
        assert init_file.exists(), (
            f"Property violation: Package directory '{directory}' is missing __init__.py. "
            f"Expected file: {init_file}"
        )
        
        # Property: The path must be a file, not a directory
        assert init_file.is_file(), (
            f"Property violation: Path '{directory}/__init__.py' exists but is not a file. "
            f"Path: {init_file}"
        )
