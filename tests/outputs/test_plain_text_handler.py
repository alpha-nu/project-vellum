"""Tests for PlainTextHandler class."""
from domain.outputs.plain_text_handler import PlainTextHandler


class TestPlainTextHandler:
    """Test PlainTextHandler output"""
    
    def test_plain_text_save(self, tmp_path):
        """Test saving plain text output"""
        handler = PlainTextHandler()
        dest = tmp_path / "output"
        content = "Test content\nMultiple lines"
        
        size = handler.save(content, dest)
        
        output_file = tmp_path / "output.txt"
        assert output_file.exists()
        assert output_file.read_text(encoding="utf-8") == content
        assert size == len(content.encode('utf-8'))
    
    def test_plain_text_with_existing_extension(self, tmp_path):
        """Test that .txt extension replaces existing extension"""
        handler = PlainTextHandler()
        dest = tmp_path / "output.pdf"
        content = "Test content"
        
        size = handler.save(content, dest)
        
        output_file = tmp_path / "output.txt"
        assert output_file.exists()
        assert not (tmp_path / "output.pdf").exists()
        assert size == len(content.encode('utf-8'))
    
    def test_plain_text_unicode_content(self, tmp_path):
        """Test handling Unicode content"""
        handler = PlainTextHandler()
        dest = tmp_path / "unicode_output"
        content = "Test with émojis 🚀 and spëcial çhars"
        
        size = handler.save(content, dest)
        
        output_file = tmp_path / "unicode_output.txt"
        assert output_file.exists()
        assert output_file.read_text(encoding="utf-8") == content
        assert size == len(content.encode('utf-8'))
    
    def test_plaintext_save_multiple(self, tmp_path):
        """Test PlainTextHandler.save_multiple creates numbered files"""
        handler = PlainTextHandler()
        destination = tmp_path / "document.pdf"
        contents = ["Page 1 text", "Page 2 text", "Page 3 text"]
        
        total_size = handler.save_multiple(contents, destination, "document.pdf")
        
        # Check that 3 files were created
        assert (tmp_path / "document_page_1.txt").exists()
        assert (tmp_path / "document_page_2.txt").exists()
        assert (tmp_path / "document_page_3.txt").exists()
        
        # Check content
        assert (tmp_path / "document_page_1.txt").read_text() == "Page 1 text"
        assert (tmp_path / "document_page_2.txt").read_text() == "Page 2 text"
        assert (tmp_path / "document_page_3.txt").read_text() == "Page 3 text"
        
        # Check total size
        expected_size = sum(len(content.encode('utf-8')) for content in contents)
        assert total_size == expected_size
    
    def test_save_multiple_empty_list(self, tmp_path):
        """Test save_multiple with empty content list"""
        handler = PlainTextHandler()
        destination = tmp_path / "empty.pdf"
        
        handler.save_multiple([], destination, "empty.pdf")
        
        # Should not create any files
        assert not (tmp_path / "empty_page_1.txt").exists()
    
    def test_save_multiple_single_page(self, tmp_path):
        """Test save_multiple with single page"""
        handler = PlainTextHandler()
        destination = tmp_path / "single.pdf"
        
        handler.save_multiple(["Only page"], destination, "single.pdf")
        
        assert (tmp_path / "single_page_1.txt").exists()
        assert (tmp_path / "single_page_1.txt").read_text() == "Only page"
        assert not (tmp_path / "single_page_2.txt").exists()
