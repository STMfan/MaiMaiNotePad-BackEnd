"""
Property-based tests for import paths and circular dependencies.

Feature: backend-structure-refactor
"""

import ast
import os
from pathlib import Path
from typing import Set, Dict, List
from hypothesis import given, strategies as st, settings, HealthCheck
import pytest


# Get project root once at module level
PROJECT_ROOT = Path(__file__).parent.parent


# Feature: backend-structure-refactor, Property 5: 循环依赖不存在性
# **Validates: Requirements 2.5, 8.3**


def get_python_files(directory: Path) -> List[Path]:
    """Get all Python files in a directory recursively."""
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Skip __pycache__ and .pytest_cache directories
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.pytest_cache', '.hypothesis']]
        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)
    return python_files


def extract_imports(file_path: Path) -> Set[str]:
    """Extract all import statements from a Python file."""
    imports = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(file_path))
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Get the full module path
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)
    except (SyntaxError, UnicodeDecodeError):
        # Skip files with syntax errors or encoding issues
        pass
    
    return imports


def get_module_name(file_path: Path, base_path: Path) -> str:
    """Convert a file path to a module name."""
    relative_path = file_path.relative_to(base_path)
    parts = list(relative_path.parts)
    
    # Remove .py extension
    if parts[-1].endswith('.py'):
        parts[-1] = parts[-1][:-3]
    
    # Remove __init__ from the end
    if parts[-1] == '__init__':
        parts = parts[:-1]
    
    return '.'.join(parts) if parts else ''


def build_dependency_graph(directory: Path) -> Dict[str, Set[str]]:
    """Build a dependency graph for all Python modules in a directory."""
    graph = {}
    python_files = get_python_files(directory)
    
    # First, collect all module names
    all_modules = set()
    for file_path in python_files:
        module_name = get_module_name(file_path, PROJECT_ROOT)
        if module_name:
            all_modules.add(module_name)
    
    # Then build the graph with only internal dependencies
    for file_path in python_files:
        module_name = get_module_name(file_path, PROJECT_ROOT)
        if not module_name:
            continue
        
        imports = extract_imports(file_path)
        # Filter to only include imports that are in our module set
        internal_imports = set()
        for imp in imports:
            # Check if this import is one of our modules
            if imp in all_modules:
                internal_imports.add(imp)
            # Also check if it's a parent module of one of our modules
            for mod in all_modules:
                if mod.startswith(imp + '.') and imp != module_name:
                    internal_imports.add(imp)
                    break
        
        graph[module_name] = internal_imports
    
    return graph


def find_circular_dependencies(graph: Dict[str, Set[str]]) -> List[List[str]]:
    """Find all circular dependencies in the graph."""
    cycles = []
    
    def dfs(node: str, path: List[str], visited: Set[str]) -> None:
        if node in path:
            # Found a cycle
            cycle_start = path.index(node)
            cycle = path[cycle_start:] + [node]
            # Only add if this exact cycle hasn't been found yet
            if cycle not in cycles and cycle[::-1] not in cycles:
                cycles.append(cycle)
            return
        
        if node in visited:
            return
        
        visited.add(node)
        path.append(node)
        
        for dependency in graph.get(node, set()):
            dfs(dependency, path.copy(), visited)
    
    visited_global = set()
    for module in graph:
        if module not in visited_global:
            dfs(module, [], visited_global)
    
    return cycles


class TestCircularDependencies:
    """Test Property 5: Circular dependency non-existence.
    
    For any two modules A and B, there should not exist a circular dependency
    where A imports B and B imports A.
    """
    
    def test_no_circular_dependencies_in_app(self):
        """Test that there are no circular dependencies in the app package."""
        app_dir = PROJECT_ROOT / "app"
        graph = build_dependency_graph(app_dir)
        
        cycles = find_circular_dependencies(graph)
        
        assert len(cycles) == 0, (
            f"Found {len(cycles)} circular dependencies: {cycles}. "
            f"Circular dependencies violate the design principle of clean module separation."
        )
    
    @given(st.sampled_from([
        "app.core",
        "app.models",
        "app.services",
        "app.api",
        "app.utils",
    ]))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_module_has_no_circular_deps(self, module_prefix):
        """Property test: For any module, it should not have circular dependencies.
        
        This property verifies that the refactored codebase maintains clean
        dependency relationships without circular imports.
        """
        app_dir = PROJECT_ROOT / "app"
        graph = build_dependency_graph(app_dir)
        
        cycles = find_circular_dependencies(graph)
        
        # Check if any cycle involves modules with this prefix
        cycles_with_prefix = [c for c in cycles if any(m.startswith(module_prefix) for m in c)]
        
        assert len(cycles_with_prefix) == 0, (
            f"Property violation: Found {len(cycles_with_prefix)} circular dependencies "
            f"involving modules with prefix '{module_prefix}': {cycles_with_prefix}. "
            f"This violates requirement 2.5 (avoid circular dependencies)."
        )



# Feature: backend-structure-refactor, Property 10: 绝对导入路径一致性
# **Validates: Requirements 8.2**


class TestAbsoluteImportPaths:
    """Test Property 10: Absolute import path consistency.
    
    For any import statement in the app/ directory, it should use absolute
    import paths (starting with 'app.') rather than relative imports.
    """
    
    def test_all_imports_are_absolute(self):
        """Test that all imports in app/ use absolute paths."""
        app_dir = PROJECT_ROOT / "app"
        python_files = get_python_files(app_dir)
        
        relative_imports = []
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read(), filename=str(file_path))
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        # Check if it's a relative import (starts with .)
                        if node.level > 0:
                            module_name = get_module_name(file_path, PROJECT_ROOT)
                            relative_imports.append((module_name, node.level, node.module))
            except (SyntaxError, UnicodeDecodeError):
                pass
        
        assert len(relative_imports) == 0, (
            f"Found {len(relative_imports)} relative imports. All imports should use "
            f"absolute paths starting with 'app.': {relative_imports[:10]}"
        )
    
    @given(st.sampled_from([
        "app/core",
        "app/models",
        "app/services",
        "app/api",
        "app/utils",
    ]))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_module_uses_absolute_imports(self, module_dir):
        """Property test: For any module, imports should be absolute.
        
        This property verifies that all import statements use absolute paths
        (from app.) rather than relative imports.
        """
        module_path = PROJECT_ROOT / module_dir
        python_files = get_python_files(module_path)
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read(), filename=str(file_path))
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        assert node.level == 0, (
                            f"Property violation: File '{file_path}' uses relative import "
                            f"(level={node.level}, module={node.module}). "
                            f"All imports should use absolute paths starting with 'app.'"
                        )
            except (SyntaxError, UnicodeDecodeError):
                pass


# Feature: backend-structure-refactor, Property 11: 导入路径有效性
# **Validates: Requirements 8.1, 8.4**


class TestImportPathValidity:
    """Test Property 11: Import path validity.
    
    For any import statement, Python interpreter should be able to successfully
    resolve that import path without ImportError.
    """
    
    def test_all_app_imports_are_valid(self):
        """Test that all imports from app modules can be resolved."""
        # This test verifies that the application can be imported without errors
        try:
            import app
            import app.main
            import app.core.config
            import app.core.database
            import app.core.security
            import app.models.database
            import app.models.schemas
            import app.services.user_service
            import app.services.auth_service
            import app.api.deps
            import app.api.routes.auth
            import app.api.routes.users
            import app.utils.websocket
        except ImportError as e:
            pytest.fail(f"Import failed: {e}. All import paths should be valid.")
    
    @given(st.sampled_from([
        "app.core.config",
        "app.core.database",
        "app.core.security",
        "app.models.database",
        "app.models.schemas",
        "app.services.user_service",
        "app.services.auth_service",
        "app.api.deps",
    ]))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_module_can_be_imported(self, module_name):
        """Property test: For any module, it should be importable.
        
        This property verifies that all modules have valid import paths
        and can be successfully imported by Python.
        """
        try:
            __import__(module_name)
        except ImportError as e:
            pytest.fail(
                f"Property violation: Module '{module_name}' cannot be imported. "
                f"Error: {e}. This violates requirement 8.1 (update import paths) "
                f"and 8.4 (verify import validity)."
            )
