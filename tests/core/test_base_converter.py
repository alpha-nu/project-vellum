"""Tests for BaseConverter abstract base class."""
from pathlib import Path
from typing import List, Any
import pytest
from domain.core.base_converter import BaseConverter


class ConcreteConverter(BaseConverter):
    """Concrete implementation of BaseConverter for testing."""
    
    def _load_items(self) -> List[Any]:
        """Return test items."""
        return ["item1", "item2"]
    
    def _extract_from_item(self, item: Any) -> str:
        """Extract text from test item."""
        return f"content from {item}"


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
    
    # Should join items with "\n\n"
    assert result == "content from item1\n\ncontent from item2"


def test_base_converter_extract_content_per_item():
    """Test BaseConverter.extract_content_per_item method"""
    path = Path("document.pdf")
    converter = ConcreteConverter(path)
    
    result = converter.extract_content_per_item()
    
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0] == "content from item1"
    assert result[1] == "content from item2"


def test_base_converter_with_progress_callback():
    """Test BaseConverter accepts progress callback"""
    path = Path("document.pdf")
    converter = ConcreteConverter(path)
    
    calls = []
    def progress_cb(current, total):
        calls.append((current, total))
    
    result = converter.extract_content(progress_callback=progress_cb)
    
    # Should have called progress callback for each item
    assert calls == [(1, 2), (2, 2)]
    assert result == "content from item1\n\ncontent from item2"


def test_base_converter_extract_content_without_callback():
    """Test extract_content can be called without progress callback"""
    path = Path("test.pdf")
    converter = ConcreteConverter(path)
    
    # Call with None explicitly
    result = converter.extract_content(progress_callback=None)
    assert result == "content from item1\n\ncontent from item2"


def test_base_converter_extract_content_per_item_without_callback():
    """Test extract_content_per_item can be called without progress callback"""
    path = Path("test.pdf")
    converter = ConcreteConverter(path)
    
    # Call with None explicitly
    result = converter.extract_content_per_item(progress_callback=None)
    assert result == ["content from item1", "content from item2"]


def test_base_converter_abstract_methods_raise_not_implemented():
    """Test abstract methods are required for instantiation"""
    # Create a class that doesn't fully implement abstract methods
    class PartialConverter(BaseConverter):
        def _load_items(self):
            # Only implement one of the two abstract methods
            return []
    
    # Cannot instantiate because _extract_from_item is missing
    with pytest.raises(TypeError):
        PartialConverter(Path("test.pdf"))


def test_base_converter_progress_callback_with_exception():
    """Test progress callback exceptions are handled gracefully"""
    path = Path("test.pdf")
    converter = ConcreteConverter(path)
    
    def bad_callback(current, total):
        raise ValueError("Test error")
    
    # Should not raise, exception should be logged
    result = converter.extract_content(progress_callback=bad_callback)
    assert result == "content from item1\n\ncontent from item2"
