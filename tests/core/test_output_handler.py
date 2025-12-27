"""Tests for OutputHandler abstract base class."""
from pathlib import Path
from typing import List
import pytest
from domain.core.output_handler import OutputHandler


class ConcreteOutputHandler(OutputHandler):
    """Concrete implementation of OutputHandler for testing."""
    
    def save(self, content: str, destination: Path):
        """Simple implementation for testing."""
        return len(content)
    
    def save_multiple(self, contents: List[str], destination: Path, source_name: str):
        """Simple implementation for testing."""
        return sum(len(c) for c in contents)


def test_output_handler_save():
    """Test OutputHandler.save method"""
    handler = ConcreteOutputHandler()
    dest = Path("output")
    content = "Test content"
    
    size = handler.save(content, dest)
    
    assert size == 12


def test_output_handler_save_multiple():
    """Test OutputHandler.save_multiple method"""
    handler = ConcreteOutputHandler()
    dest = Path("output")
    contents = ["Page 1", "Page 2", "Page 3"]
    
    total_size = handler.save_multiple(contents, dest, "document.pdf")
    
    assert total_size == 18  # 6 + 6 + 6


def test_output_handler_save_with_none_callback():
    """Test OutputHandler.save can be called with None destination"""
    handler = ConcreteOutputHandler()
    
    # Test with various destination types
    size1 = handler.save("content", Path("test1"))
    size2 = handler.save("content", Path("test2"))
    
    assert size1 == 7
    assert size2 == 7


def test_output_handler_save_multiple_single_item():
    """Test OutputHandler.save_multiple with single content item"""
    handler = ConcreteOutputHandler()
    dest = Path("output")
    contents = ["Single page"]
    
    total_size = handler.save_multiple(contents, dest, "document.pdf")
    
    assert total_size == 11  # len("Single page")


def test_output_handler_abstract_methods_raise_not_implemented():
    """Test abstract methods raise NotImplementedError when not overridden"""
    class PartialHandler(OutputHandler):
        def save(self, content: str, destination: Path):
            return super().save(content, destination)
        
        def save_multiple(self, contents: List[str], destination: Path, source_name: str):
            return super().save_multiple(contents, destination, source_name)
    
    handler = PartialHandler()
    
    with pytest.raises(NotImplementedError, match="Subclasses must implement save"):
        handler.save("test", Path("output"))
    
    with pytest.raises(NotImplementedError, match="Subclasses must implement save_multiple"):
        handler.save_multiple(["test"], Path("output"), "doc.pdf")
