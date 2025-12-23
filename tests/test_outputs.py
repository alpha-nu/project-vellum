"""
Enhanced tests for model layer to increase coverage.
Tests converters and output handlers with various scenarios.
"""
import json
from model.outputs import PlainTextHandler, MarkdownHandler, JSONHandler


class TestPlainTextHandler:
    """Test PlainTextHandler output"""
    
    def test_plain_text_save(self, tmp_path):
        """Test saving plain text output"""
        handler = PlainTextHandler()
        dest = tmp_path / "output"
        content = "Test content\nMultiple lines"
        
        handler.save(content, dest)
        
        output_file = tmp_path / "output.txt"
        assert output_file.exists()
        assert output_file.read_text(encoding="utf-8") == content
    
    def test_plain_text_with_existing_extension(self, tmp_path):
        """Test that .txt extension replaces existing extension"""
        handler = PlainTextHandler()
        dest = tmp_path / "output.pdf"
        content = "Test content"
        
        handler.save(content, dest)
        
        output_file = tmp_path / "output.txt"
        assert output_file.exists()
        assert not (tmp_path / "output.pdf").exists()
    
    def test_plain_text_unicode_content(self, tmp_path):
        """Test handling Unicode content"""
        handler = PlainTextHandler()
        dest = tmp_path / "unicode_output"
        content = "Test with émojis 🚀 and spëcial çhars"
        
        handler.save(content, dest)
        
        output_file = tmp_path / "unicode_output.txt"
        assert output_file.exists()
        assert output_file.read_text(encoding="utf-8") == content


class TestMarkdownHandler:
    """Test MarkdownHandler output"""
    
    def test_markdown_save(self, tmp_path):
        """Test saving markdown output with header"""
        handler = MarkdownHandler()
        dest = tmp_path / "output"
        content = "Test content"
        
        handler.save(content, dest)
        
        output_file = tmp_path / "output.md"
        assert output_file.exists()
        
        result = output_file.read_text(encoding="utf-8")
        assert result.startswith("# source: output")
        assert "Test content" in result
    
    def test_markdown_preserves_content(self, tmp_path):
        """Test that markdown preserves original content"""
        handler = MarkdownHandler()
        dest = tmp_path / "test_file"
        content = "Line 1\nLine 2\nLine 3"
        
        handler.save(content, dest)
        
        output_file = tmp_path / "test_file.md"
        result = output_file.read_text(encoding="utf-8")
        
        # Check header
        assert "# source: test_file" in result
        # Check content preserved
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result
    
    def test_markdown_with_special_chars(self, tmp_path):
        """Test markdown with special characters"""
        handler = MarkdownHandler()
        dest = tmp_path / "special.pdf"
        content = "Content with *asterisks* and _underscores_"
        
        handler.save(content, dest)
        
        output_file = tmp_path / "special.md"
        assert output_file.exists()
        result = output_file.read_text(encoding="utf-8")
        assert content in result


class TestJSONHandler:
    """Test JSONHandler output"""
    
    def test_json_save(self, tmp_path):
        """Test saving JSON output"""
        handler = JSONHandler()
        dest = tmp_path / "output"
        content = "Test content"
        
        handler.save(content, dest)
        
        output_file = tmp_path / "output.json"
        assert output_file.exists()
        
        with open(output_file) as f:
            data = json.load(f)
        
        assert "source" in data
        assert "content" in data
        assert data["source"] == "output"
        assert data["content"] == content
    
    def test_json_structure(self, tmp_path):
        """Test JSON output structure"""
        handler = JSONHandler()
        dest = tmp_path / "test.epub"
        content = "Multi-line\ncontent\nhere"
        
        handler.save(content, dest)
        
        output_file = tmp_path / "test.json"
        with open(output_file) as f:
            data = json.load(f)
        
        # Verify structure
        assert set(data.keys()) == {"source", "content"}
        assert data["source"] == "test.epub"
        assert data["content"] == content
    
    def test_json_indentation(self, tmp_path):
        """Test JSON is properly indented"""
        handler = JSONHandler()
        dest = tmp_path / "output"
        content = "Test"
        
        handler.save(content, dest)
        
        output_file = tmp_path / "output.json"
        json_text = output_file.read_text()
        
        # Check for indentation (4 spaces as per json.dump)
        assert "    " in json_text
    
    def test_json_unicode_content(self, tmp_path):
        """Test JSON with Unicode content"""
        handler = JSONHandler()
        dest = tmp_path / "unicode"
        content = "Unicode: émojis 🎉, spëcial çhars"
        
        handler.save(content, dest)
        
        output_file = tmp_path / "unicode.json"
        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)
        
        assert data["content"] == content
    
    def test_json_large_content(self, tmp_path):
        """Test JSON with large content"""
        handler = JSONHandler()
        dest = tmp_path / "large"
        content = "Line\n" * 1000  # 1000 lines
        
        handler.save(content, dest)
        
        output_file = tmp_path / "large.json"
        with open(output_file) as f:
            data = json.load(f)
        
        assert data["content"] == content
        assert data["content"].count("\n") == 1000


class TestOutputHandlersEdgeCases:
    """Test edge cases for all handlers"""
    
    def test_empty_content(self, tmp_path):
        """Test all handlers with empty content"""
        handlers = [
            (PlainTextHandler(), ".txt"),
            (MarkdownHandler(), ".md"),
            (JSONHandler(), ".json"),
        ]
        
        for handler, ext in handlers:
            dest = tmp_path / f"empty{ext}"
            handler.save("", dest.with_suffix(""))
            
            output_file = tmp_path / f"empty{ext}"
            assert output_file.exists()
    
    def test_very_long_filename(self, tmp_path):
        """Test handlers with long filenames"""
        long_name = "a" * 200  # Very long filename
        handlers = [
            (PlainTextHandler(), ".txt"),
            (MarkdownHandler(), ".md"),
            (JSONHandler(), ".json"),
        ]
        
        for handler, ext in handlers:
            dest = tmp_path / long_name
            handler.save("content", dest)
            
            output_file = tmp_path / f"{long_name}{ext}"
            assert output_file.exists()
    
    def test_nested_path(self, tmp_path):
        """Test handlers with nested directory paths"""
        nested_dir = tmp_path / "level1" / "level2" / "level3"
        nested_dir.mkdir(parents=True, exist_ok=True)
        
        handlers = [
            (PlainTextHandler(), ".txt"),
            (MarkdownHandler(), ".md"),
            (JSONHandler(), ".json"),
        ]
        
        for handler, ext in handlers:
            dest = nested_dir / "nested_file"
            handler.save("test content", dest)
            
            output_file = nested_dir / f"nested_file{ext}"
            assert output_file.exists()


class TestPerPageOutputHandlers:
    """Test save_multiple methods in output handlers"""
    
    def test_plaintext_save_multiple(self, tmp_path):
        """Test PlainTextHandler.save_multiple creates numbered files"""
        handler = PlainTextHandler()
        destination = tmp_path / "document.pdf"
        contents = ["Page 1 text", "Page 2 text", "Page 3 text"]
        
        handler.save_multiple(contents, destination, "document.pdf")
        
        # Check that 3 files were created
        assert (tmp_path / "document_page_1.txt").exists()
        assert (tmp_path / "document_page_2.txt").exists()
        assert (tmp_path / "document_page_3.txt").exists()
        
        # Check content
        assert (tmp_path / "document_page_1.txt").read_text() == "Page 1 text"
        assert (tmp_path / "document_page_2.txt").read_text() == "Page 2 text"
        assert (tmp_path / "document_page_3.txt").read_text() == "Page 3 text"
    
    def test_markdown_save_multiple(self, tmp_path):
        """Test MarkdownHandler.save_multiple creates numbered markdown files"""
        handler = MarkdownHandler()
        destination = tmp_path / "book.epub"
        contents = ["Chapter 1", "Chapter 2"]
        
        handler.save_multiple(contents, destination, "book.epub")
        
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
    
    def test_json_save_multiple(self, tmp_path):
        """Test JSONHandler.save_multiple creates numbered JSON files"""
        handler = JSONHandler()
        destination = tmp_path / "doc.pdf"
        contents = ["First page", "Second page"]
        
        handler.save_multiple(contents, destination, "doc.pdf")
        
        # Check files exist
        assert (tmp_path / "doc_page_1.json").exists()
        assert (tmp_path / "doc_page_2.json").exists()
        
        # Check JSON structure
        with open(tmp_path / "doc_page_1.json") as f:
            data1 = json.load(f)
        assert data1["source"] == "doc.pdf"
        assert data1["page"] == 1
        assert data1["content"] == "First page"
        
        with open(tmp_path / "doc_page_2.json") as f:
            data2 = json.load(f)
        assert data2["source"] == "doc.pdf"
        assert data2["page"] == 2
        assert data2["content"] == "Second page"
    
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
