"""Tests for JSONHandler class."""
import json
from domain.outputs.json_handler import JSONHandler


class TestJSONHandler:
    """Test JSONHandler output"""
    
    def test_json_save(self, tmp_path):
        """Test saving JSON output"""
        handler = JSONHandler()
        dest = tmp_path / "output"
        content = "Test content"
        
        size = handler.save(content, dest)
        
        output_file = tmp_path / "output.json"
        assert output_file.exists()
        
        with open(output_file) as f:
            data = json.load(f)
        
        assert "source" in data
        assert "content" in data
        assert data["source"] == "output"
        assert data["content"] == content
        assert size == len(json.dumps(data, indent=4).encode('utf-8'))
    
    def test_json_structure(self, tmp_path):
        """Test JSON output structure"""
        handler = JSONHandler()
        dest = tmp_path / "test.epub"
        content = "Multi-line\ncontent\nhere"
        
        size = handler.save(content, dest)
        
        output_file = tmp_path / "test.json"
        with open(output_file) as f:
            data = json.load(f)
        
        # Verify structure
        assert set(data.keys()) == {"source", "content"}
        assert data["source"] == "test.epub"
        assert data["content"] == content
        assert size == len(json.dumps(data, indent=4).encode('utf-8'))
    
    def test_json_indentation(self, tmp_path):
        """Test JSON is properly indented"""
        handler = JSONHandler()
        dest = tmp_path / "output"
        content = "Test"
        
        size = handler.save(content, dest)
        
        output_file = tmp_path / "output.json"
        json_text = output_file.read_text()
        
        # Check for indentation (4 spaces as per json.dump)
        assert "    " in json_text
        assert size == len(json_text.encode('utf-8'))
        assert size == len(json_text.encode('utf-8'))
    
    def test_json_unicode_content(self, tmp_path):
        """Test JSON with Unicode content"""
        handler = JSONHandler()
        dest = tmp_path / "unicode"
        content = "Unicode: émojis 🎉, spëcial çhars"
        
        size = handler.save(content, dest)
        
        output_file = tmp_path / "unicode.json"
        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)
        
        assert data["content"] == content
        assert size == len(json.dumps(data, indent=4).encode('utf-8'))
    
    def test_json_large_content(self, tmp_path):
        """Test JSON with large content"""
        handler = JSONHandler()
        dest = tmp_path / "large"
        content = "Line\n" * 1000  # 1000 lines
        
        size = handler.save(content, dest)
        
        output_file = tmp_path / "large.json"
        with open(output_file) as f:
            data = json.load(f)
        
        assert data["content"] == content
        assert data["content"].count("\n") == 1000
        assert size == len(json.dumps(data, indent=4).encode('utf-8'))
    
    def test_json_save_multiple(self, tmp_path):
        """Test JSONHandler.save_multiple creates numbered JSON files"""
        handler = JSONHandler()
        destination = tmp_path / "doc.pdf"
        contents = ["First page", "Second page"]
        
        total_size = handler.save_multiple(contents, destination, "doc.pdf")
        
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
        
        # Check total size
        json1_text = json.dumps(data1, indent=4)
        json2_text = json.dumps(data2, indent=4)
        assert total_size == len(json1_text.encode('utf-8')) + len(json2_text.encode('utf-8'))
