"""Tests for BaseConverter abstract base class."""
from pathlib import Path
from typing import List
import pytest
from domain.core.base_converter import BaseConverter


class ConcreteConverter(BaseConverter):
    """Concrete implementation of BaseConverter for testing."""
    
    def extract_content(self, progress_callback=None) -> str:
        """Simple implementation for testing."""
        return f"Content from {self.source_path}"
    
    def extract_content_per_item(self, progress_callback=None) -> List[str]:
        """Simple implementation for testing."""
        return [f"Item from {self.source_path}"]


def test_base_converter_initialization():
    """Test BaseConverter initialization stores source path"""
    path = Path("test.pdf")
    converter = ConcreteConverter(path)
    
    assert converter.source_path == path


def test_base_converter_extract_content():
    """Test BaseConverter.extract_content method"""
    path = Path("document.pdf")
    converter = ConcreteConverter(path)
    
    result = converter.extract_content()
    
    assert result == "Content from document.pdf"


def test_base_converter_extract_content_per_item():
    """Test BaseConverter.extract_content_per_item method"""
    path = Path("document.pdf")
    converter = ConcreteConverter(path)
    
    result = converter.extract_content_per_item()
    
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0] == "Item from document.pdf"


def test_base_converter_with_progress_callback():
    """Test BaseConverter accepts progress callback"""
    path = Path("document.pdf")
    converter = ConcreteConverter(path)
    
    calls = []
    def progress_cb(current, total):
        calls.append((current, total))
    
    result = converter.extract_content(progress_callback=progress_cb)
    
    assert result == "Content from document.pdf"


def test_base_converter_extract_content_without_callback():
    """Test extract_content can be called without progress callback"""
    path = Path("test.pdf")
    converter = ConcreteConverter(path)
    
    # Call with None explicitly
    result = converter.extract_content(progress_callback=None)
    assert result == "Content from test.pdf"


def test_base_converter_extract_content_per_item_without_callback():
    """Test extract_content_per_item can be called without progress callback"""
    path = Path("test.pdf")
    converter = ConcreteConverter(path)
    
    # Call with None explicitly
    result = converter.extract_content_per_item(progress_callback=None)
    assert result == ["Item from test.pdf"]


def test_base_converter_abstract_methods_raise_not_implemented():
    """Test abstract methods raise NotImplementedError when not overridden"""
    # Create a class that doesn't fully implement abstract methods
    class PartialConverter(BaseConverter):
        def extract_content(self, progress_callback=None):
            return super().extract_content(progress_callback)
        
        def extract_content_per_item(self, progress_callback=None):
            return super().extract_content_per_item(progress_callback)
    
    converter = PartialConverter(Path("test.pdf"))
    
    with pytest.raises(NotImplementedError, match="Subclasses must implement extract_content"):
        converter.extract_content()
    
    with pytest.raises(NotImplementedError, match="Subclasses must implement extract_content_per_item"):
        converter.extract_content_per_item()
