import importlib
import pytest
import os

def test_autotrade_package_import():
    """Test that the main package can be imported."""
    try:
        import autotrade
    except ImportError:
        pytest.fail("Could not import autotrade package")

def test_submodules_exist():
    """Test that all submodules exist and can be imported."""
    submodules = [
        "autotrade.core",
        "autotrade.market_data",
        "autotrade.strategies",
        "autotrade.execution",
        "autotrade.risk",
    ]

    for module_name in submodules:
        try:
            importlib.import_module(module_name)
        except ImportError as e:
            pytest.fail(f"Could not import {module_name}: {e}")

def test_directory_structure():
    """Test that essential directories exist."""
    required_dirs = [
        "logs",
        "data",
        "tests",
        "autotrade"
    ]

    for directory in required_dirs:
        assert os.path.isdir(directory), f"Directory {directory} is missing"

def test_files_exist():
    """Test that essential files exist."""
    required_files = [
        "requirements.txt",
        ".env.example",
        "main.py",
        ".gitignore"
    ]

    for filename in required_files:
        assert os.path.isfile(filename), f"File {filename} is missing"
