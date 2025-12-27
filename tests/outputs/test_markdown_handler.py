"""Tests for MarkdownHandler class."""
from domain.outputs.markdown_handler import MarkdownHandler


class TestMarkdownHandler:
    """Test MarkdownHandler output"""
    
    def test_markdown_save(self, tmp_path):
        """Test saving markdown output with header"""
        handler = MarkdownHandler()
        dest = tmp_path / "output"
        content = "Test content"
        
        size = handler.save(content, dest)
        
        output_file = tmp_path / "output.md"
        assert output_file.exists()
        
        result = output_file.read_text(encoding="utf-8")
        assert result.startswith("# source: output")
        assert "Test content" in result
        assert size == len(result.encode('utf-8'))
    
    def test_markdown_preserves_content(self, tmp_path):
        """Test that markdown preserves original content"""
        handler = MarkdownHandler()
        dest = tmp_path / "test_file"
        content = "Line 1\nLine 2\nLine 3"
        
        size = handler.save(content, dest)
        
        output_file = tmp_path / "test_file.md"
        result = output_file.read_text(encoding="utf-8")
        
        # Check header
        assert "# source: test_file" in result
        # Check content preserved
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result
        assert size == len(result.encode('utf-8'))
    
    def test_markdown_with_special_chars(self, tmp_path):
        """Test markdown with special characters"""
        handler = MarkdownHandler()
        dest = tmp_path / "special.pdf"
        content = "Content with *asterisks* and _underscores_"
        
        size = handler.save(content, dest)
        
        output_file = tmp_path / "special.md"
        assert output_file.exists()
        result = output_file.read_text(encoding="utf-8")
        assert content in result
        assert size == len(result.encode('utf-8'))
    
    def test_markdown_save_multiple(self, tmp_path):
        """Test MarkdownHandler.save_multiple creates numbered markdown files"""
        handler = MarkdownHandler()
        destination = tmp_path / "book.epub"
        contents = ["Chapter 1", "Chapter 2"]
        
        total_size = handler.save_multiple(contents, destination, "book.epub")
        
        # Check files exist
        assert (tmp_path / "book_page_1.md").exists()
        assert (tmp_path / "book_page_2.md").exists()
        
        # Check markdown formatting
        page1 = (tmp_path / "book_page_1.md").read_text()
        assert page1.startswith("# source: book.epub (page 1)")
        assert "Chapter 1" in page1
        
        page2 = (tmp_path / "book_page_2.md").read_text()
        assert page2.startswith("# source: book.epub (page 2)")
        assert "Chapter 2" in page2
        
        # Check total size
        assert total_size == len(page1.encode('utf-8')) + len(page2.encode('utf-8'))
